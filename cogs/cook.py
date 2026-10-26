import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection, RECIPE_DATABASE, COOKING_STATION_UPGRADE_COST

class RecipeSelect(discord.ui.Select):
    def __init__(self, user_id, station_level, unlocked_recipes):
        self.user_id = user_id
        options = []

        # 將 21 道食譜加入下拉選單
        for name, data in RECIPE_DATABASE.items():
            # 檢查是否可製作
            is_unlocked = (name in unlocked_recipes) or (data["station_level"] <= 1)
            is_level_enough = station_level >= data["station_level"]
            
            emoji = "🍳" if (is_unlocked and is_level_enough) else "🔒"
            desc = f"需求台階: Lv.{data['station_level']} | 產出: {data['output']}"
            
            options.append(
                discord.SelectOption(
                    label=name,
                    value=name,
                    description=desc[:100], # Discord 限制描述 100 字元內
                    emoji=emoji
                )
            )

        super().__init__(placeholder="👉 點擊此處選擇想要烹調的料理...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的料理台！", ephemeral=True)
            return

        recipe_name = self.values[0]
        recipe = RECIPE_DATABASE[recipe_name]

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. 檢查料理台等級
        cursor.execute("SELECT cooking_level FROM players WHERE user_id = ?", (self.user_id,))
        player_row = cursor.fetchone()
        station_level = player_row["cooking_level"] if player_row else 1

        if station_level < recipe["station_level"]:
            cursor.close()
            conn.close()
            await interaction.response.send_message(f"❌ 你的料理台等級不足！製作 **{recipe_name}** 需要 **Lv.{recipe['station_level']}** 料理台。", ephemeral=True)
            return

        # 2. 檢查背包材料是否充足
        missing_items = []
        for item_name, req_qty in recipe["ingredients"].items():
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, item_name))
            inv_row = cursor.fetchone()
            has_qty = inv_row["quantity"] if inv_row else 0
            if has_qty < req_qty:
                missing_items.append(f"**{item_name}** (需求: {req_qty}, 擁有: {has_qty})")

        if missing_items:
            cursor.close()
            conn.close()
            missing_str = ", ".join(missing_items)
            await interaction.response.send_message(f"❌ 材料不足，無法製作 **{recipe_name}**！\n缺少：{missing_str}", ephemeral=True)
            return

        # 3. 扣除材料
        for item_name, req_qty in recipe["ingredients"].items():
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, item_name))
            has_qty = cursor.fetchone()["quantity"]
            new_qty = has_qty - req_qty
            if new_qty <= 0:
                cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, item_name))
            else:
                cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, self.user_id, item_name))

        # 4. 發放成品到背包
        output_item = recipe["output"]
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, output_item))
        out_row = cursor.fetchone()
        if out_row:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (self.user_id, output_item))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (self.user_id, output_item))

        conn.commit()
        cursor.close()
        conn.close()

        await interaction.response.send_message(f"🎉 **烹飪成功！** 你成功製作了 **{output_item}**！\n💡 *{recipe['description']}*", ephemeral=True)


class CookingView(discord.ui.View):
    def __init__(self, user_id, station_level, unlocked_recipes):
        super().__init__(timeout=60)
        self.user_id = user_id
        # 將下拉選單加入 View 中
        self.add_item(RecipeSelect(user_id, station_level, unlocked_recipes))

    @discord.ui.button(label="⬆️ 升級料理台", style=discord.ButtonStyle.primary, row=1)
    async def upgrade_station(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的料理台！", ephemeral=True)
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT cooking_level, gold FROM players WHERE user_id = ?", (self.user_id,))
        player = cursor.fetchone()
        if not player:
            await interaction.response.send_message("⚠️ 找不到角色資料。", ephemeral=True)
            cursor.close()
            conn.close()
            return

        current_level, gold = player
        next_level = current_level + 1

        if next_level not in COOKING_STATION_UPGRADE_COST:
            await interaction.response.send_message("🎉 你的料理台已經達到最高等級 (Lv.3)！", ephemeral=True)
            cursor.close()
            conn.close()
            return

        cost = COOKING_STATION_UPGRADE_COST[next_level]
        
        if gold < cost["gold"]:
            await interaction.response.send_message(f"❌ 升級需要 `{cost['gold']} G`，你的金幣不足！", ephemeral=True)
            cursor.close()
            conn.close()
            return

        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, cost["item"]))
        inv = cursor.fetchone()
        has_qty = inv["quantity"] if inv else 0

        if has_qty < cost["qty"]:
            await interaction.response.send_message(f"❌ 升級需要素材 **{cost['item']}** x `{cost['qty']}`（你當前擁有 `{has_qty}` 個）", ephemeral=True)
            cursor.close()
            conn.close()
            return

        # 執行升級與扣除資源
        cursor.execute("UPDATE players SET cooking_level = cooking_level + 1, gold = gold - ? WHERE user_id = ?", (cost["gold"], self.user_id))
        
        new_qty = has_qty - cost["qty"]
        if new_qty <= 0:
            cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, cost["item"]))
        else:
            cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, self.user_id, cost["item"]))

        conn.commit()
        cursor.close()
        conn.close()

        await interaction.response.send_message(f"🎉 升級成功！你的料理台已提升至 **Lv.{next_level}**！請重新輸入 `/料理台` 來解鎖更多高級食譜。", ephemeral=True)


class Cook(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="料理台", description="開啟你的專屬料理台與 21 道豪華食譜系統")
    async def cooking(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT cooking_level FROM players WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 請先建立角色才能使用料理台！", ephemeral=True)
            return

        station_level = row["cooking_level"]

        cursor.execute("SELECT recipe_name FROM player_recipes WHERE user_id = ?", (user_id,))
        unlocked_recipes = {r["recipe_name"] for r in cursor.fetchall()}
        cursor.close()
        conn.close()

        embed = discord.Embed(
            title="🍳 【冒險者頂級料理台】",
            description=f"歡迎來到廚房！結合農場作物與牧場肉品，製作多達 21 道頂級料理。\n\n🔥 **當前料理台等級**：`Lv.{station_level}`\n\n👇 **請從下方選單中選擇你想製作的料理：**",
            color=discord.Color.gold()
        )
        embed.set_footer(text="💡 Lv.1 可做家常菜，Lv.2~3 可解鎖精緻甜點與主廚級料理！")

        view = CookingView(user_id, station_level, unlocked_recipes)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Cook(bot))
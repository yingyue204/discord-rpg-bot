import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# ⚙️ 強化配方設定 (等級: {所需金幣, 所需材料, 增加數值})
UPGRADE_RECIPES = {
    "武器": {
        1: {"gold": 200, "material": "鐵塊", "mat_qty": 2, "bonus": 5, "desc": "初階鐵劍磨利，攻擊力 +5"},
        2: {"gold": 600, "material": "鐵塊", "mat_qty": 5, "bonus": 12, "desc": "精煉鋼鐵武器，攻擊力 +12"},
        3: {"gold": 1500, "material": "魔導金屬", "mat_qty": 2, "bonus": 25, "desc": "注入魔導能量，攻擊力 +25"}
    },
    "防具": {
        1: {"gold": 150, "material": "海帶", "mat_qty": 3, "bonus": 20, "desc": "加固防護服，生命上限 +20"},
        2: {"gold": 500, "material": "高級肉塊", "mat_qty": 2, "bonus": 50, "desc": "重型防護裝甲，生命上限 +50"},
        3: {"gold": 1200, "material": "魔導金屬", "mat_qty": 1, "bonus": 100, "desc": "神話合金護甲，生命上限 +100"}
    }
}

class Blacksmith(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="鐵匠舖", description="前往鐵匠舖查看與強化你的武器或防具")
    @app_commands.rename(equipment_type="裝備類型")
    @app_commands.describe(equipment_type="選擇要強化的裝備部位")
    @app_commands.choices(equipment_type=[
        app_commands.Choice(name="⚔️ 武器 (提升攻擊力)", value="武器"),
        app_commands.Choice(name="🛡️ 防具 (提升生命上限)", value="防具")
    ])
    async def blacksmith(self, interaction: discord.Interaction, equipment_type: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 1. 檢查玩家資料與目前裝備等級 (假設 players 表中有 weapon_lvl, armor_lvl，若沒有等下幫你補)
            # 為了保險，我們先檢查欄位是否存在或確保資料庫有對應欄位
            cursor.execute("SELECT gold, role_name FROM players WHERE user_id = ?", (user_id,))
            player = cursor.fetchone()

            if not player or not player["role_name"]:
                await interaction.followup.send("⚠️ 你尚未建立角色！請先使用相關指令選擇職業。", ephemeral=True)
                return

            gold = player["gold"]

            # 檢查並確保 players 資料表有裝備等級欄位
            try:
                cursor.execute(f"SELECT weapon_lvl, armor_lvl FROM players WHERE user_id = ?", (user_id,))
                lvl_row = cursor.fetchone()
                weapon_lvl = lvl_row["weapon_lvl"] if lvl_row and lvl_row["weapon_lvl"] is not None else 0
                armor_lvl = lvl_row["armor_lvl"] if lvl_row and lvl_row["armor_lvl"] is not None else 0
            except Exception:
                # 若欄位不存在，自動幫資料庫補上這兩個欄位
                cursor.execute("ALTER TABLE players ADD COLUMN weapon_lvl INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE players ADD COLUMN armor_lvl INTEGER DEFAULT 0")
                conn.commit()
                weapon_lvl, armor_lvl = 0, 0

            current_lvl = weapon_lvl if equipment_type == "武器" else armor_lvl
            next_lvl = current_lvl + 1

            # 檢查是否已達最高等級 (目前設定最高 3 等)
            if next_lvl > 3:
                embed = discord.Embed(
                    title=f"⚒️ 【鐵匠舖 - {equipment_type}】",
                    description=f"太神啦！你的**{equipment_type}**已經達到最高等級（Lv.3），匠人已經無法再幫你突破了！",
                    color=discord.Color.gold()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            recipe = UPGRADE_RECIPES[equipment_type][next_lvl]
            req_gold = recipe["gold"]
            req_mat = recipe["material"]
            req_qty = recipe["mat_qty"]

            # 2. 檢查玩家背包內的材料數量
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, req_mat))
            mat_row = cursor.fetchone()
            user_mat_qty = mat_row["quantity"] if mat_row else 0

            # 3. 組合介面顯示目前的強化狀態與需求
            embed = discord.Embed(
                title=f"⚒️ 【皇家鐵匠舖】— 強化 {equipment_type}",
                description=f"歡迎來到鐵匠舖！資深鐵匠正等著為你的裝備更上一層樓。\n\n"
                            f"📌 **目前等級**：`Lv.{current_lvl}`\n"
                            f"🚀 **目標升級**：`Lv.{next_lvl}`\n"
                            f"✨ **強化效果**：{recipe['desc']}\n\n"
                            f"📋 **升級所需成本**：\n"
                            f"• 💰 金幣：`{req_gold} G` （你有 `{gold} G`）\n"
                            f"• 📦 材料：`{req_mat}` x `{req_qty}` （你有 `{user_mat_qty} 個`）",
                color=discord.Color.blue()
            )

            # 檢查資源是否足夠
            can_upgrade = (gold >= req_gold) and (user_mat_qty >= req_qty)

            if not can_upgrade:
                embed.add_field(name="⚠️ 資源不足", value="你的金幣或指定材料不夠，快去冒險、釣魚或逛逛系統商店收集吧！", inline=False)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # 4. 執行扣款與升級
            if equipment_type == "武器":
                cursor.execute("UPDATE players SET gold = gold - ?, weapon_lvl = weapon_lvl + 1, attack = attack + ? WHERE user_id = ?", 
                               (req_gold, recipe["bonus"], user_id))
            else:
                cursor.execute("UPDATE players SET gold = gold - ?, armor_lvl = armor_lvl + 1, max_hp = max_hp + ? WHERE user_id = ?", 
                               (req_gold, recipe["bonus"], user_id))

            # 扣除背包材料
            cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?", (req_qty, user_id, req_mat))
            # 若材料扣到 0 可以選擇清空，不過保留 0 或後續清理皆可

            conn.commit()

            embed_success = discord.Embed(
                title=f"🎉 【裝備強化成功！】",
                description=f"伴隨著巨大的打鐵聲與火花，你的 **{equipment_type}** 成功升級到 **`Lv.{next_lvl}`**！\n\n"
                            f"✨ **能力提升**：{recipe['desc']}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed_success, ephemeral=True)

        except Exception as e:
            conn.rollback()
            print(f"❌ 鐵匠舖指令發生錯誤: {e}")
            await interaction.followup.send(f"❌ 強化過程發生未預期的錯誤：`{e}`", ephemeral=True)
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

async def setup(bot):
    await bot.add_cog(Blacksmith(bot))
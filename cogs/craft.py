import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# 定義合成配方表 { 合成結果道具: {"cost_gold": 費用, "materials": {材料名稱: 數量}} }
CRAFT_RECIPES = {
    "【普通】高震動短刀": {
        "cost_gold": 30,
        "materials": {"鐵劍碎片": 3, "鐵礦石": 2},
        "type": "weapon",
        "bonus": 6,
        "desc": "消耗 3 個鐵劍碎片、2 個鐵礦石與 30 G 合成的普通武器。"
    },
    "【普通】光束劍": {
        "cost_gold": 50,
        "materials": {"鐵劍碎片": 5, "鐵礦石": 3},
        "type": "weapon",
        "bonus": 8,
        "desc": "消耗 5 個鐵劍碎片、3 個鐵礦石與 50 G 合成的普通武器。"
    },
    "【普通】電擊打擊槍": {
        "cost_gold": 60,
        "materials": {"鐵劍碎片": 4, "鐵礦石": 3},
        "type": "weapon",
        "bouns": 9,
        "desc": "消耗 4 鐵劍碎片、 3 個鐵礦石與 60 G 合成的普通武器。"
    },
    "【普通】重型巨斧": {
        "cost_gold": 70,
        "materials": {"鐵劍碎片": 6, "鐵礦石": 4},
        "type": "weapon",
        "bouns": 11,
        "desc": "消耗 6 鐵劍碎片、 4 個鐵礦石與 70 G 合成的普通武器。"
    },
    "【精良】高震動短刀": {
        "cost_gold": 100,
        "materials": {"【普通】高震動短刀": 1, "鐵劍碎片": 10, "鐵礦石": 6, "碳化纖維": 1},
        "type": "weapon",
        "bouns": 12,
        "desc": "消耗 1 【普通】高震動短刀、 10 鐵劍碎片、 6 鐵礦石、 1 碳化纖維與 100 G 合成的普通武器。"
    },
    "【精良】光束劍": {
        "cost_gold": 120,
        "materials": {"【普通】光束劍": 1, "鐵劍碎片": 13, "鐵礦石": 7, "碳化纖維": 2},
        "type": "weapon",
        "bouns": 15,
        "desc": "消耗 1 【普通】光束劍、 13 鐵劍碎片、 7 鐵礦石、 2 碳化纖維與 120 G 合成的普通武器。"
    },
    "【精良】電擊打擊槍": {
        "cost_gold": 140,
        "materials": {"【普通】電擊打擊槍": 1, "鐵劍碎片": 16, "鐵礦石": 8, "碳化纖維": 2},
        "type": "weapon",
        "bouns": 17,
        "desc": "消耗 1 【普通】電擊打擊槍、 16 鐵劍碎片、 8 鐵礦石、 2 碳化纖維與 140 G 合成的普通武器。"
    },
    "【精良】重型巨斧": {
        "cost_gold": 160,
        "materials": {"【普通】重型巨斧": 1, "鐵劍碎片": 19, "鐵礦石": 9, "碳化纖維": 3},
        "type": "weapon",
        "bouns": 20,
        "desc": "消耗 1 【普通】重型巨斧、 19 鐵劍碎片、 9 鐵礦石、 3 碳化纖維與 160 G 合成的普通武器。"
    },
    "急救包": {
        "cost_gold": 50,
        "materials": {"生命藥水": 2},
        "type": "item",
        "desc": "消耗 2 瓶生命藥水與 50 G 濃縮合成的高效急救包。"
    }
}

class Craft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="craft", description="使用收集到的素材與金幣合成強力道具或裝備")
    @app_commands.describe(item_name="你想合成的目標道具名稱")
    async def craft(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        if item_name not in CRAFT_RECIPES:
            # 列出所有可合成清單
            recipe_list = "\n".join([f"• **{name}" for name in CRAFT_RECIPES.keys()])
            await interaction.followup.send(
                f"❌ 沒有這個合成配方！目前可合成的道具清單：\n{recipe_list}\n請輸入正確的名稱。", 
                ephemeral=True
            )
            return

        recipe = CRAFT_RECIPES[item_name]
        cost_gold = recipe["cost_gold"]
        required_materials = recipe["materials"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 1. 檢查玩家金幣
            cursor.execute("SELECT gold FROM players WHERE user_id = ?", (user_id,))
            player = cursor.fetchone()
            if not player or (player[0] or 0) < cost_gold:
                await interaction.followup.send(f"❌ 金幣不足！合成 **{item_name}** 需要 `{cost_gold} G`。", ephemeral=True)
                return

            # 2. 檢查玩家身上的所有材料是否足夠
            for mat_name, req_qty in required_materials.items():
                cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, mat_name))
                row = cursor.fetchone()
                current_qty = row[0] if row else 0
                if current_qty < req_qty:
                    await interaction.followup.send(
                        f"❌ 材料不足！缺少 **{mat_name}**（需要 `{req_qty}` 個，你目前有 `{current_qty}` 個）。", 
                        ephemeral=True
                    )
                    return

            # 3. 扣除金幣
            cursor.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (cost_gold, user_id))

            # 4. 扣除對應材料數量
            for mat_name, req_qty in required_materials.items():
                cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, mat_name))
                current_qty = cursor.fetchone()[0]
                if current_qty == req_qty:
                    cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, mat_name))
                else:
                    cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?", (req_qty, user_id, mat_name))

            # 5. 發放合成後的道具到背包
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            target_row = cursor.fetchone()
            if target_row:
                cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, item_name))

            conn.commit()

            embed = discord.Embed(
                title="⚒️ 【裝備/道具合成成功】",
                description=f"你成功消耗材料與金幣，打造出了 **{item_name}** x `1`！\n💡 趕快使用 `/bag` 查看背包吧！",
                color=discord.Color.brand_green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        finally:
            cursor.close()
            conn.close()

async def setup(bot):
    await bot.add_cog(Craft(bot))
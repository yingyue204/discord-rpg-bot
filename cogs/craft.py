import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# 定義合成配方表 { 合成結果道具: {"cost_gold": 費用, "materials": {材料名稱: 數量}} }
CRAFT_RECIPES = {
    # ---------------- ⚪ 普通裝備系列 (入門期) ----------------
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
        "materials": {"鐵劍碎片": 6, "鐵礦石": 4},
        "type": "weapon",
        "bonus": 9,
        "desc": "消耗 6 個鐵劍碎片、4 個鐵礦石與 60 G 合成的普通武器。"
    },
    "【普通】重型巨斧": {
        "cost_gold": 70,
        "materials": {"鐵劍碎片": 8, "鐵礦石": 5},
        "type": "weapon",
        "bonus": 11,
        "desc": "消耗 8 個鐵劍碎片、5 個鐵礦石與 70 G 合成的普通武器。"
    },
    "【普通】戰術護甲": {
        "cost_gold": 40,
        "materials": {"鐵礦石": 3},
        "type": "armor",
        "bonus": 5,
        "desc": "消耗 3 個鐵礦石與 40 G 合成的普通防具。"
    },
    "【普通】納米防護服": {
        "cost_gold": 45,
        "materials": {"鐵礦石": 4, "生命藥水": 1},
        "type": "armor",
        "bonus": 6,
        "desc": "消耗 4 個鐵礦石、1 瓶生命藥水與 45 G 合成的防具。"
    },
    "【普通】合金重盾": {
        "cost_gold": 55,
        "materials": {"鐵礦石": 6},
        "type": "armor",
        "bonus": 8,
        "desc": "消耗 6 個鐵礦石與 55 G 合成的普通防具。"
    },
    "【普通】外骨骼裝甲": {
        "cost_gold": 70,
        "materials": {"鐵礦石": 8},
        "type": "armor",
        "bonus": 10,
        "desc": "消耗 8 個鐵礦石與 70 G 合成的普通防具。"
    },

    # ---------------- 🔵 精良裝備系列 (消耗：普通裝備 + 更多鐵料 + 低階能量晶核) ----------------
    "【精良】高震動短刀": {
        "cost_gold": 100,
        "materials": {"【普通】高震動短刀": 1, "鐵劍碎片": 12, "鐵礦石": 8, "低階能量晶核": 1},
        "type": "weapon",
        "bonus": 12,
        "desc": "消耗普通短刀、大量鐵料與低階能量晶核升級的精良武器。"
    },
    "【精良】光束劍": {
        "cost_gold": 120,
        "materials": {"【普通】光束劍": 1, "鐵劍碎片": 15, "鐵礦石": 10, "低階能量晶核": 1},
        "type": "weapon",
        "bonus": 15,
        "desc": "消耗普通光束劍、大量鐵料與低階能量晶核升級的精良武器。"
    },
    "【精良】電擊打擊槍": {
        "cost_gold": 140,
        "materials": {"【普通】電擊打擊槍": 1, "鐵劍碎片": 18, "鐵礦石": 12, "低階能量晶核": 1},
        "type": "weapon",
        "bonus": 17,
        "desc": "結合鐵料與低階能量晶核強化的精良打擊槍。"
    },
    "【精良】重型巨斧": {
        "cost_gold": 160,
        "materials": {"【普通】重型巨斧": 1, "鐵劍碎片": 22, "鐵礦石": 15, "低階能量晶核": 1},
        "type": "weapon",
        "bonus": 20,
        "desc": "注入低階能量晶核與重度鐵料的精良重型巨斧。"
    },
    "【精良】戰術護甲": {
        "cost_gold": 90,
        "materials": {"【普通】戰術護甲": 1, "鐵礦石": 10, "低階能量晶核": 1},
        "type": "armor",
        "bonus": 10,
        "desc": "使用大量鐵礦石與低階能量晶核升級的精良戰術護甲。"
    },
    "【精良】納米防護服": {
        "cost_gold": 100,
        "materials": {"【普通】納米防護服": 1, "鐵礦石": 12, "低階能量晶核": 1},
        "type": "armor",
        "bonus": 12,
        "desc": "防禦力提升的精良納米防護服。"
    },
    "【精良】合金重盾": {
        "cost_gold": 120,
        "materials": {"【普通】合金重盾": 1, "鐵礦石": 15, "低階能量晶核": 1},
        "type": "armor",
        "bonus": 14,
        "desc": "強化結構的精良合金重盾。"
    },
    "【精良】外骨骼裝甲": {
        "cost_gold": 150,
        "materials": {"【普通】外骨骼裝甲": 1, "鐵礦石": 18, "低階能量晶核": 1},
        "type": "armor",
        "bonus": 16,
        "desc": "重型強化的精良外骨骼裝甲。"
    },

    # ---------------- 🟣 史詩裝備系列 (消耗：精良裝備 + 海量鐵料 + 中階能量晶核) ----------------
    "【史詩】高震動短刀": {
        "cost_gold": 350,
        "materials": {"【精良】高震動短刀": 1, "鐵劍碎片": 30, "鐵礦石": 20, "中階能量晶核": 1},
        "type": "weapon",
        "bonus": 22,
        "desc": "消耗精良短刀、海量鐵料與中階能量晶核的史詩短刀。"
    },
    "【史詩】光束劍": {
        "cost_gold": 380,
        "materials": {"【精良】光束劍": 1, "鐵劍碎片": 35, "鐵礦石": 24, "中階能量晶核": 1},
        "type": "weapon",
        "bonus": 26,
        "desc": "高能聚焦且消耗大量鐵料的史詩級光束劍。"
    },
    "【史詩】電磁打擊槍": {
        "cost_gold": 400,
        "materials": {"【精良】電擊打擊槍": 1, "鐵劍碎片": 40, "鐵礦石": 28, "中階能量晶核": 1},
        "type": "weapon",
        "bonus": 29,
        "desc": "注入中階能量核心與重裝鐵料的史詩遠程武器。"
    },
    "【史詩】重型巨斧": {
        "cost_gold": 450,
        "materials": {"【精良】重型巨斧": 1, "鐵劍碎片": 48, "鐵礦石": 32, "中階能量晶核": 1},
        "type": "weapon",
        "bonus": 34,
        "desc": "沉重且附帶中階能量震盪與海量鐵料的史詩巨斧。"
    },
    "【史詩】戰術護甲": {
        "cost_gold": 300,
        "materials": {"【精良】戰術護甲": 1, "鐵礦石": 25, "中階能量晶核": 1},
        "type": "armor",
        "bonus": 18,
        "desc": "具備中階能量防禦場與重裝鐵礦的史詩護甲。"
    },
    "【史詩】納米防護服": {
        "cost_gold": 330,
        "materials": {"【精良】納米防護服": 1, "鐵礦石": 28, "中階能量晶核": 1},
        "type": "armor",
        "bonus": 20,
        "desc": "微型奈米防禦升級的史詩防護服。"
    },
    "【史詩】合金重盾": {
        "cost_gold": 370,
        "materials": {"【精良】合金重盾": 1, "鐵礦石": 32, "中階能量晶核": 1},
        "type": "armor",
        "bonus": 24,
        "desc": "中階能量屏障加固的史詩重盾。"
    },
    "【史詩】外骨骼裝甲": {
        "cost_gold": 420,
        "materials": {"【精良】外骨骼裝甲": 1, "鐵礦石": 36, "中階能量晶核": 1},
        "type": "armor",
        "bonus": 28,
        "desc": "全覆蓋中階動力的史詩外骨骼。"
    },

    # ---------------- 🟡 傳說級裝備系列 (消耗：史詩裝備 + 極量鐵料 + 高階能量晶核) ----------------
    "【傳說級】終焉短刀": {
        "cost_gold": 1000,
        "materials": {"【史詩】高震動短刀": 1, "鐵劍碎片": 70, "鐵礦石": 45, "高階能量晶核": 1},
        "type": "weapon",
        "bonus": 40,
        "desc": "消耗史詩短刀、極量鐵料與高階能量晶核的傳說短刀。"
    },
    "【傳說級】終焉光束劍": {
        "cost_gold": 1100,
        "materials": {"【史詩】光束劍": 1, "鐵劍碎片": 80, "鐵礦石": 50, "高階能量晶核": 1},
        "type": "weapon",
        "bonus": 42,
        "desc": "切割一切的傳說級終焉光束劍。"
    },
    "【傳說級】毀滅電磁槍": {
        "cost_gold": 1200,
        "materials": {"【史詩】電磁打擊槍": 1, "鐵劍碎片": 90, "鐵礦石": 55, "高階能量晶核": 1},
        "type": "weapon",
        "bonus": 45,
        "desc": "貫穿戰場的傳說級電磁神兵。"
    },
    "【傳說級】毀滅重型巨斧": {
        "cost_gold": 1300,
        "materials": {"【史詩】重型巨斧": 1, "鐵劍碎片": 100, "鐵礦石": 60, "高階能量晶核": 1},
        "type": "weapon",
        "bonus": 50,
        "desc": "擁有神話級破壞力的傳說巨斧。"
    },
    "【傳說級】泰坦戰術護甲": {
        "cost_gold": 900,
        "materials": {"【史詩】戰術護甲": 1, "鐵礦石": 50, "高階能量晶核": 1},
        "type": "armor",
        "bonus": 30,
        "desc": "泰坦級防禦力的傳說戰術護甲。"
    },
    "【傳說級】脈衝防衛力場": {
        "cost_gold": 1000,
        "materials": {"【史詩】納米防護服": 1, "鐵礦石": 55, "高階能量晶核": 1},
        "type": "armor",
        "bonus": 33,
        "desc": "展開自動脈衝防禦的傳說力場服。"
    },
    "【傳說級】絕對防禦重盾": {
        "cost_gold": 1100,
        "materials": {"【史詩】合金重盾": 1, "鐵礦石": 60, "高階能量晶核": 1},
        "type": "armor",
        "bonus": 37,
        "desc": "號稱永不破裂的傳說重盾。"
    },
    "【傳說級】泰坦合金重裝": {
        "cost_gold": 1300,
        "materials": {"【史詩】外骨骼裝甲": 1, "鐵礦石": 70, "高階能量晶核": 1},
        "type": "armor",
        "bonus": 42,
        "desc": "終極防禦型態的傳說級泰坦重裝。"
    },

    # ---------------- 📦 消耗品與其他 ----------------
    "急救包": {
        "cost_gold": 50,
        "materials": {"生命藥水": 2},
        "type": "item",
        "desc": "消耗 2 瓶生命藥水與 50 G 濃縮合成的高效急救包。"
    },
    "中階能量晶核": {
        "cost_gold": 100,
        "materials": {"低階能量晶核": 3},
        "type": "item",
        "desc": "消耗 3 顆低階能量晶核與 100 G合成的中階能量晶核"
    },
    "高階能量晶核": {
        "cost_gold": 300,
        "materials": {"中階能量晶核": 3},
        "type": "item",
        "desc": "消耗 3 顆中階能量晶核與 300 G合成的高階能量晶核"
    }
}

class Craft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="合成", description="使用收集到的素材與金幣合成強力道具或裝備")
    @app_commands.rename(name="合成目標")
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
import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection
from cogs.battle import BattleChoiceView

# 地圖資料設定
MAP_DATA = {
    "新手廢墟": {
        "description": "和平但充滿殘骸的廢墟，適合新手搜刮。",
        "monster_chance": 0.25,
        "monsters": ["廢土伏擊者", "迷路防禦機械"],
        "gold_range": (5, 10),
        "drops": [
            ("生命藥水", 35),
            ("鐵劍碎片", 30),
            ("神秘寶箱", 10),
            ("鐵礦石",25),
            ("低階能量晶核", 25),
            ("低階授權晶片", 20)
        ]
    },
    "廢棄實驗室": {
        "description": "科學失控後人去樓空的密閉空間，能有機率獲得醫療用品",
        "monster_chance": 0.45,
        "monsters": ["失控實驗品", "寄生感染體"],
        "gold_range": (10, 20),
        "drops": [
            ("急救包", 40),
            ("魔力藥水", 30),
            ("神秘寶箱", 15),
            ("中階能量晶核", 25),
            ("中階授權晶片", 20),
            ("碳化纖維", 20),
        ]
    },
    "機械禁區": {
        "description": "高度防衛的禁忌科技園區，充滿強敵與極珍貴物資！",
        "monster_chance": 0.65,
        "monsters": ["防衛機器人 MK-II", "暴走核心守衛"],
        "gold_range": (30, 60),
        "drops": [
            ("能量飲料", 50),
            ("急救包", 30),
            ("神秘寶箱", 20),
            ("高階能量晶核", 25),
            ("高階授權晶片", 25),
            ("輻射源石", 25)
        ]
    }
}

class Explore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="explore", description="選擇前往不同的區域進行冒險與搜刮")
    @app_commands.choices(location=[
        app_commands.Choice(name="新手廢墟 (安全，適合初期的探索)", value="新手廢墟"),
        app_commands.Choice(name="廢棄實驗室 (中等風險，報酬較高)", value="廢棄實驗室"),
        app_commands.Choice(name="機械禁區 (高風險高報酬，強敵環伺)", value="機械禁區")
    ])
    @app_commands.describe(location="你想前往的冒險區域")
    async def explore(self, interaction: discord.Interaction, location: str):
        await interaction.response.defer()
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role, hp, max_hp FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()

        if not player or not player[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/setup_roles` 選擇職業。", ephemeral=True)
            return

        role_name, hp, max_hp = player

        # 🏥 檢查倒地狀態
        if hp <= 0:
            new_hp = min(max_hp, 50)
            cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
            conn.commit()
            cursor.close()
            conn.close()

            embed = discord.Embed(title="🏥 【新手村診所】", color=discord.Color.blue())
            embed.description = f"你處於倒地狀態無法冒險！已被送至診所急救。\n❤️ 當前血量：`{new_hp}/{max_hp}`"
            await interaction.followup.send(embed=embed)
            return

        cursor.close()
        conn.close()

        # 取得該地圖的設定
        map_info = MAP_DATA[location]

        # ⚔️ 依據地圖機率判定是否遭遇怪物伏擊
        if random.random() < map_info["monster_chance"]:
            monster_name = random.choice(map_info["monsters"])
            # 根據不同地圖調整怪物強弱
            stat_multiplier = 1.0 if location == "新手廢墟" else (1.5 if location == "廢棄實驗室" else 2.2)
            monster_hp = int(random.randint(30, 50) * stat_multiplier)
            monster_atk = int(random.randint(8, 15) * stat_multiplier)

            embed = discord.Embed(
                title=f"⚡ 【{location}】遭遇敵人伏擊！",
                description=f"你在「{location}」搜刮時驚動了守衛，必須立刻迎戰！",
                color=discord.Color.red()
            )
            embed.add_field(name="🤖 敵方目標", value=f"**{monster_name}**", inline=True)
            embed.add_field(name="❤️ 血量", value=f"`{monster_hp}` HP", inline=True)
            embed.add_field(name="⚔️ 攻擊力", value=f"`{monster_atk}` ATK", inline=True)
            embed.set_footer(text="💡 擊敗強敵可以獲得更豐富的戰利品獎勵！60秒未操作將自動過期。")

            view = BattleChoiceView(user_id, monster_name, monster_hp, monster_atk, is_adventure_ambush=True)
            sent_message = await interaction.followup.send(embed=embed, view=view, wait=True)
            view.message = sent_message
            return

        # 🎒 平安搜刮邏輯（隨機掉落物權重計算）
        found_gold = random.randint(map_info["gold_range"][0], map_info["gold_range"][1])
        
        # 權重抽獎法 (Weighted Random)
        items, weights = zip(*map_info["drops"])
        found_item = random.choices(items, weights=weights, k=1)[0]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, found_item))
        item_row = cursor.fetchone()
        
        if item_row:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, found_item))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, found_item))

        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (found_gold, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        embed = discord.Embed(title=f"🛡️ 【{location} · 搜刮成功】", color=discord.Color.green())
        embed.description = map_info["description"]
        embed.add_field(name="📦 獲得道具", value=f"**{found_item}** x `1`", inline=True)
        embed.add_field(name="💰 獲得金幣", value=f"**+{found_gold} G**", inline=True)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Explore(bot))
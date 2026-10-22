import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random

class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 初始化資料庫表格的輔助函式
    def init_db(self):
        conn = sqlite3.connect("rpg.db")
        cursor = conn.cursor()
        # 建立玩家資料表 (金幣、HP等)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                gold INTEGER DEFAULT 0,
                hp INTEGER DEFAULT 100
            )
        """)
        # 建立背包資料表 (使用 PRIMARY KEY 讓相同道具自動累加數量)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER,
                PRIMARY KEY (user_id, item_name)
            )
        """)
        conn.commit()
        conn.close()

    @app_commands.command(name="adventure", description="前往新手村或野外進行冒險與搜刮！")
    async def adventure(self, interaction: discord.Interaction):
        self.init_db()
        
        # 隨機掉落的道具清單
        possible_items = ["急救包", "稀有金屬", "生命藥水", "鐵劍碎片"]
        found_item = random.choice(possible_items)
        found_gold = random.randint(10, 50)

        conn = sqlite3.connect("rpg.db")
        cursor = conn.cursor()
        
        # 確保玩家存在於 players 表格中
        cursor.execute("INSERT OR IGNORE INTO players (user_id, gold, hp) VALUES (?, 100, 100)", (interaction.user.id,))
        
        # 增加金幣
        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (found_gold, interaction.user.id))

        # 檢查背包是否已有該道具，有則數量 +1，無則新增
        cursor.execute("""
            SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?
        """, (interaction.user.id, found_item))
        result = cursor.fetchone()

        if result:
            cursor.execute("""
                UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?
            """, (interaction.user.id, found_item))
        else:
            cursor.execute("""
                INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)
            """, (interaction.user.id, found_item))

        conn.commit()
        conn.close()

        # 建立漂亮的嵌入式訊息回報搜刮成果
        embed = discord.Embed(
            title="🛡️ 【冒險成功：艾底索德 (Episode-0)】",
            description=f"你在探索的途中有了驚人的收穫！",
            color=discord.Color.green()
        )
        embed.add_field(name="📦 獲得道具", value=f"**{found_item} x1**", inline=True)
        embed.add_field(name="💰 獲得金幣", value=f"**{found_gold} G**", inline=True)
        embed.set_footer(text="提示：使用 /bag 指令可以隨時查看你的隨身背包！")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Adventure(bot))
import discord
from discord.ext import commands
from discord import app_commands
import random
from db import get_db_connection  # 引入雲端資料庫連線模組

class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def init_db(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id BIGINT PRIMARY KEY,
                gold INTEGER DEFAULT 0,
                hp INTEGER DEFAULT 100
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                item_name TEXT,
                quantity INTEGER,
                CONSTRAINT unique_user_item UNIQUE (user_id, item_name)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

    @app_commands.command(name="adventure", description="前往新手村或野外進行冒險與搜刮！")
    async def adventure(self, interaction: discord.Interaction):
        self.init_db()
        
        possible_items = ["急救包", "稀有金屬", "生命藥水", "鐵劍碎片"]
        found_item = random.choice(possible_items)
        
        # 調整：將獲得金幣的範圍縮小，讓經濟平衡
        found_gold = random.randint(5, 15)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # PostgreSQL 的防重複插入寫法 (ON CONFLICT)
        cursor.execute("""
            INSERT INTO players (user_id, gold, hp) 
            VALUES (%s, 100, 100) 
            ON CONFLICT (user_id) DO NOTHING
        """, (interaction.user.id,))
        
        cursor.execute("UPDATE players SET gold = gold + %s WHERE user_id = %s", (found_gold, interaction.user.id))

        cursor.execute("SELECT quantity FROM inventory WHERE user_id = %s AND item_name = %s", (interaction.user.id, found_item))
        result = cursor.fetchone()

        if result:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = %s AND item_name = %s", (interaction.user.id, found_item))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (%s, %s, 1)", (interaction.user.id, found_item))

        conn.commit()
        cursor.close()
        conn.close()

        embed = discord.Embed(
            title="🛡️ 【冒險成功：艾底索德 (Episode-0)】",
            description=f"你在探索的途中有了收穫！",
            color=discord.Color.green()
        )
        embed.add_field(name="📦 獲得道具", value=f"**{found_item} x1**", inline=True)
        embed.add_field(name="💰 獲得金幣", value=f"**{found_gold} G**", inline=True)
        embed.set_footer(text="提示：使用 /bag 指令可以隨時查看你的隨身背包！")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Adventure(bot))
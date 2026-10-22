import sqlite3
import discord
from discord.ext import commands

class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect("rpg_game.db")
        cursor = conn.cursor()
        # 建立玩家資料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                hp INTEGER DEFAULT 100,
                atk INTEGER DEFAULT 25,
                defense INTEGER DEFAULT 10,
                gold INTEGER DEFAULT 50
            )
        """)
        # 建立背包資料表
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

async def setup(bot):
    await bot.add_cog(Database(bot))
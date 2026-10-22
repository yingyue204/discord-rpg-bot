import discord
from discord.ext import commands
import os
import asyncio
from keep_alive import keep_alive
from db import get_db_connection

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

def init_global_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id BIGINT PRIMARY KEY,
                role TEXT,
                hp INTEGER DEFAULT 100,
                max_hp INTEGER DEFAULT 100,
                atk INTEGER DEFAULT 25,
                def INTEGER DEFAULT 10,
                speed INTEGER DEFAULT 20,
                gold INTEGER DEFAULT 100
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
        print("✅ 雲端資料庫表格檢查與初始化完成！")
    except Exception as e:
        print(f"❌ 資料庫初始化失敗: {e}")

async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"📦 已載入 Cog: {filename[:-3]}")

@bot.event
async def on_ready():
    init_global_db()
    try:
        synced = await bot.tree.sync()
        print(f"✅ 已成功同步 {len(synced)} 個斜線指令！")
    except Exception as e:
        print(f"⚠️ 指令同步失敗: {e}")
    print(f"✅ 機器人已成功登入為 {bot.user}")

async def main():
    keep_alive()
    async with bot:
        await load_extensions()
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("❌ 錯誤：找不到 DISCORD_TOKEN 環境變數！")
            return
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
import discord
from discord.ext import commands
import os
import asyncio
from keep_alive import keep_alive
from db import init_db

# 1. 統一在啟動時呼叫 db.py 的完整初始化（會自動包含所有欄位與防護）
init_db()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"📦 已載入 Cog: {filename[:-3]}")

@bot.event
async def on_ready():
    # 同步所有斜線指令到 Discord
    try:
        synced = await bot.tree.sync()
        print(f"✅ 已成功同步 {len(synced)} 個斜線指令！")
    except Exception as e:
        print(f"⚠️ 指令同步失敗: {e}")
    print(f"✅ 機器人已成功線上登入：{bot.user}")

async def main():
    keep_alive()  # 啟動 Web Server
    async with bot:
        await load_extensions()
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("❌ 錯誤：未設定 DISCORD_TOKEN 環境變數！")
            return
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
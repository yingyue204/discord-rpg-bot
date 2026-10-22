import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# 設定機器人權限 (Intents)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 機器人已成功連線：{bot.user}")
    try:
        # 同步 Slash 指令到 Discord
        synced = await bot.tree.sync()
        print(f"🌐 成功同步 {len(synced)} 個應用程式指令 (Slash Commands)")
    except Exception as e:
        print(f"❌ 同步指令失敗: {e}")

async def load_extensions():
    # 自動載入 cogs 資料夾底下的所有模組
    if not os.path.exists("./cogs"):
        os.makedirs("./cogs")
        
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            cog_name = filename[:-3]
            try:
                await bot.load_extension(f"cogs.{cog_name}")
                print(f"✅ 成功載入模組 : {filename}")
            except Exception as e:
                print(f"❌ 載入模組 {filename} 失敗，錯誤原因：{e}")

async def main():
    async with bot:
        await load_extensions()
        if TOKEN:
            await bot.start(TOKEN)
        else:
            print("❌ 錯誤：找不到 DISCORD_TOKEN，請檢查 .env 檔案或 Render 環境變數設定！")

if __name__ == "__main__":
    asyncio.run(main())
    bot.run(os.getenv("DISCORD_TOKEN"))
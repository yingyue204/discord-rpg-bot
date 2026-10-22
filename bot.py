import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive  # 引入保持連線功能

# ... (中間原本載入 cogs 的程式碼保持不變) ...

if __name__ == "__main__":
    keep_alive()  # 啟動網頁伺服器以通過 Render 的 Port 檢查
    asyncio.run(main())

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
            print("❌ 錯誤：找不到 DISCORD_TOKEN")

if __name__ == "__main__":
    keep_alive()          # 啟動保持連線伺服器
    asyncio.run(main())   # 啟動機器人主程式
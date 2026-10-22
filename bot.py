import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive  # 引入保持連線伺服器

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# ... 你的其他 cog 載入與事件 ...

if __name__ == "__main__":
    # 啟動保持活線的 Web 伺服器
    keep_alive()
    
    # 啟動你的 Discord 機器人
    bot.run("你的_DISCORD_TOKEN")
    
# 載入環境變數（如果在 Render 上則會直接讀取雲端設定）
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# 設定 Bot 的權限 (Intents)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ 機器人已成功登入為：{bot.user} (ID: {bot.user.id})")

# 動態載入 cogs 資料夾底下的所有模組
async def load_extensions():
    if not os.path.exists("./cogs"):
        print("⚠️ 找不到 cogs 資料夾！")
        return
        
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            cog_name = filename[:-3]
            try:
                await bot.load_extension(f"cogs.{cog_name}")
                print(f"✅ 成功載入模組：{filename}")
            except Exception as e:
                print(f"❌ 載入模組 {filename} 失敗，錯誤原因：{e}")

async def main():
    # 啟動時先載入模組
    await load_extensions()
    
    if TOKEN:
        # 啟動 Discord 機器人
        await bot.start(TOKEN)
    else:
        print("❌ 錯誤：找不到 DISCORD_TOKEN，請檢查 .env 檔案或 Render 環境變數設定！")

if __name__ == "__main__":
    # 1. 先啟動網頁伺服器，讓 Render 的 Port 檢查通過
    keep_alive()
    # 2. 執行主異步程式
    asyncio.run(main())
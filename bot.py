import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive  # 引入保持連線伺服器
from db import get_db_connection   # 引入我們的雲端資料庫連線模組

# 載入環境變數（如果在 Render 上則會直接讀取雲端設定）
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# 設定 Bot 的權限 (Intents)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 初始化雲端資料庫表格（確保 PostgreSQL 裡面有需要的 Table）
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 範例：建立玩家資料表 (users / players) 與背包表 (inventory)
    # 依照你原本專案的欄位需求，這裡建立基本的範例表格，若你原本有現成的建表語法可以替換
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id BIGINT PRIMARY KEY,
            name TEXT,
            level INT DEFAULT 1,
            hp INT DEFAULT 100,
            gold INT DEFAULT 0
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            item_name TEXT,
            quantity INT DEFAULT 1
        );
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ 雲端資料庫表格檢查與初始化完成！")

@bot.event
async def on_ready():
    print(f"✅ 機器人已成功登入為：{bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"✅ 已成功同步 {len(synced)} 個斜線指令！")
    except Exception as e:
        print(f"❌ 斜線指令同步失敗：{e}")

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
    # 1. 啟動時先初始化雲端資料庫表格
    try:
        init_db()
    except Exception as e:
        print(f"❌ 資料庫初始化失敗，請檢查 DATABASE_URL 是否正確：{e}")
        return

    # 2. 載入 cogs 模組
    await load_extensions()
    
    if TOKEN:
        # 3. 啟動 Discord 機器人
        await bot.start(TOKEN)
    else:
        print("❌ 錯誤：找不到 DISCORD_TOKEN，請檢查 .env 檔案或 Render 環境變數設定！")

if __name__ == "__main__":
    # 1. 先啟動網頁伺服器，讓 Render 的 Port 檢查通過
    keep_alive()
    # 2. 執行主異步程式
    asyncio.run(main())
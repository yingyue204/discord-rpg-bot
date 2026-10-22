import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class Bag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bag", description="查看你的隨身背包與道具")
    async def bag(self, interaction: discord.Interaction):
        conn = sqlite3.connect("rpg.db")
        cursor = conn.cursor()
        
        # 確保背包資料表存在，避免剛開局查詢時報錯
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER,
                PRIMARY KEY (user_id, item_name)
            )
        """)
        
        # 查詢該玩家擁有的所有道具與數量
        cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (interaction.user.id,))
        items = cursor.fetchall()
        conn.close()

        # 建立漂亮的嵌入式背包介面
        embed = discord.Embed(
            title=f"🎒 [{interaction.user.name} 的隨身背包]",
            color=discord.Color.blue()
        )
        
        if items:
            # 將所有道具列出來
            description = "\n".join([f"• **{item_name}** x{qty}" for item_name, qty in items])
            embed.description = description
        else:
            embed.description = "背包空空如也～快去使用 `/adventure` 冒險搜刮道具吧！"

        embed.set_footer(text="提示：使用 /adventure 獲取更多稀有裝備與道具！")

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Bag(bot))
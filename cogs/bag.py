import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class Bag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bag", description="查看你的隨身背包與道具清單")
    async def bag(self, interaction: discord.Interaction):
        # 1. 立即延期回應，避免 Discord 3秒逾時
        await interaction.response.defer(ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()

        # 查詢使用者的背包道具
        cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = %s", (interaction.user.id,))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()

        embed = discord.Embed(
            title=f"📦 [{interaction.user.name} · 隨身背包]",
            color=discord.Color.gold()
        )

        if not results:
            embed.description = "你的背包目前空空如也，快去使用 `/adventure` 進行冒險搜刮吧！"
        else:
            items_text = ""
            for item_name, quantity in results:
                items_text += f"• **{item_name}** x {quantity}\n"
            embed.add_field(name="🎒 持有道具清單", value=items_text, inline=False)

        # 2. 使用 followup 發送私密訊息
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Bag(bot))
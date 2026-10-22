import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class Bag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bag", description="查看隨身背包道具")
    async def bag(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (interaction.user.id,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        embed = discord.Embed(title=f"📦 [{interaction.user.name} · 隨身背包]", color=discord.Color.gold())
        if not results:
            embed.description = "背包空空如也，快去使用 `/adventure` 冒險搜刮吧！"
        else:
            items_text = "".join([f"• **{name}** x {qty}\n" for name, qty in results])
            embed.add_field(name="🎒 持有道具清單", value=items_text, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Bag(bot))
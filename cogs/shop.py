import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shop", description="前往特務商城購買道具")
    async def shop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="🛒 【特務商城】",
            description="目前商城正在補貨中，敬請期待後續更新！",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))
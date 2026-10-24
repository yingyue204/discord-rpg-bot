import discord
from discord.ext import commands
from discord import app_commands
from db import equip_item_in_db

class Equipment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="equip", description="從背包中穿戴指定的武器或防具")
    @app_commands.describe(item_name="你想穿戴的裝備完整名稱（例如：【精良】光束劍）")
    async def equip(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        success, message = equip_item_in_db(user_id, item_name)
        
        embed = discord.Embed(
            title="🛡️ 【裝備系統】",
            description=message,
            color=discord.Color.green() if success else discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.app_commands_to_sync() if hasattr(bot, 'app_commands_to_sync') else None
    await bot.add_cog(Equipment(bot))
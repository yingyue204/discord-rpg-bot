import discord
from discord.ext import commands
from discord import app_commands
from db import SHOP_ITEMS

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="系統商店", description="開啟系統商店查看可購買的道具與材料")
    async def system_shop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="🛒 【系統商店】",
            description="以下是目前販售的商品清單：\n請使用 `/購買` 指令來購入道具！",
            color=discord.Color.blue()
        )
        
        for name, data in SHOP_ITEMS.items():
            embed.add_field(name=f"{name} (`{data['price']} G`)", value=data["description"], inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))
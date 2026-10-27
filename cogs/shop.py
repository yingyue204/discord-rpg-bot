import discord
from discord.ext import commands
from discord import app_commands
from db import SHOP_ITEMS, buy_item_in_db

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 💡 自動完成：讓玩家輸入 /購買 時，可以直接從清單中挑選商品
    async def item_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        choices = []
        for name, data in SHOP_ITEMS.items():
            display_name = f"{name} ({data['price']} G)"
            if current.lower() in name.lower() or current == "":
                choices.append(app_commands.Choice(name=display_name, value=name))
        return choices[:25]  # Discord 限制最多 25 個選項

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

    @app_commands.command(name="購買", description="從系統商店中購買指定的道具、材料或素材")
    @app_commands.describe(item_name="想購買的商品名稱", quantity="購買數量（預設為 1）")
    @app_commands.autocomplete(item_name=item_autocomplete)
    async def buy_item(self, interaction: discord.Interaction, item_name: str, quantity: int = 1):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        if quantity <= 0:
            await interaction.followup.send("❌ 購買數量必須大於 0！", ephemeral=True)
            return

        # 呼叫 db.py 中的安全購買邏輯
        success, msg = buy_item_in_db(user_id, item_name, quantity)

        embed = discord.Embed(
            title="🛒 【系統商店交易】",
            description=msg,
            color=discord.Color.gold() if success else discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))
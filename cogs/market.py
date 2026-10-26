import discord
from discord.ext import commands
from discord import app_commands
from db import get_active_sellers, get_listings_by_seller, buy_market_item
import traceback

class SellerSelect(discord.ui.Select):
    def __init__(self, sellers):
        options = []
        if not sellers:
            options.append(discord.SelectOption(label="目前沒有其他玩家上架商品", value="none", description="快去當第一個上架的玩家吧！"))
        else:
            for seller_id, seller_name in sellers:
                options.append(discord.SelectOption(
                    label=f"{seller_name} 的商店",
                    value=str(seller_id),
                    description="點擊進入查看販售中的商品",
                    emoji="🏪"
                ))
        super().__init__(placeholder="請選擇要造訪的玩家商店...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("❌ 目前沒有其他玩家的商店可造訪。", ephemeral=True)
            return
            
        seller_id = int(self.values[0])
        items = get_listings_by_seller(seller_id)
        
        if not items:
            await interaction.response.send_message("❌ 該玩家目前已經沒有上架商品了。", ephemeral=True)
            return
            
        view = PlayerStoreView(seller_id, items)
        embed = discord.Embed(
            title="🏪 【玩家個人商店】",
            description="請從下方選單中選擇你想要購買的商品：",
            color=discord.Color.gold()
        )
        for listing_id, item_name, price, qty in items:
            embed.add_field(name=item_name, value=f"具備數量: `{qty}` | 售價: `{price} G`", inline=False)
            
        await interaction.response.edit_message(embed=embed, view=view)

class ItemBuySelect(discord.ui.Select):
    def __init__(self, items):
        options = []
        for listing_id, item_name, price, qty in items:
            options.append(discord.SelectOption(
                label=f"{item_name} (數量: {qty})",
                value=str(listing_id),
                description=f"價格: {price} G",
                emoji="💰"
            ))
        super().__init__(placeholder="選擇想要購買的商品...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        listing_id = int(self.values[0])
        success, message = buy_market_item(interaction.user.id, listing_id)
        
        embed = discord.Embed(
            title="🛒 【交易結果】",
            description=message,
            color=discord.Color.green() if success else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PlayerStoreView(discord.ui.View):
    def __init__(self, seller_id, items):
        super().__init__(timeout=60)
        self.seller_id = seller_id
        self.add_item(ItemBuySelect(items))
        
    @discord.ui.button(label="⬅️ 返回商店大廳", style=discord.ButtonStyle.secondary)
    async def back_to_lobby(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MarketMainView(interaction.user.id)
        embed = discord.Embed(
            title="🛒 【自由玩家市場】",
            description="歡迎來到玩家自由市場！\n請點擊下方按鈕或透過選單選擇你要執行的操作：",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)

class MarketMainView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id
        
        # 直接從 db 載入其他玩家選單
        sellers = get_active_sellers(user_id)
        self.add_item(SellerSelect(sellers))

    @discord.ui.button(label="🏷️ 我要上架商品", style=discord.ButtonStyle.success, row=1)
    async def list_item_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("💡 請使用指令 `/market sell <道具名稱> <價格> <數量>` 來將道具上架至市場！", ephemeral=True)

class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="market", description="開啟玩家自由市場")
    async def market(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = discord.Embed(
                title="🛒 【自由玩家市場】",
                description="歡迎來到玩家自由市場！\n在這裡你可以跟其他特務進行自由貿易。\n\n🛡️ **安全機制**：系統已自動過濾掉你自己的商店，防止洗錢行為。",
                color=discord.Color.blue()
            )
            embed.set_footer(text="💡 請從下方選單選擇你想逛的玩家商店。")
            
            view = MarketMainView(interaction.user.id)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ 發生系統錯誤：`{e}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Market(bot))
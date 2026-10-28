import discord
from discord.ext import commands
from discord import app_commands
from db import SHOP_ITEMS, buy_item_in_db, sell_item_to_shop_in_db, get_db_connection

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 💡 購買商品的自動完成
    async def buy_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        choices = []
        for name, data in SHOP_ITEMS.items():
            display_name = f"{name} ({data['price']} G)"
            if current.lower() in name.lower() or current == "":
                choices.append(app_commands.Choice(name=display_name, value=name))
        return choices[:25]

    # 💡 販賣商品的自動完成（安全讀取背包）
    async def sell_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        user_id = interaction.user.id
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            choices = []
            for row in rows:
                name = row["item_name"]
                qty = row["quantity"]
                display_name = f"{name} (擁有: {qty} 個)"
                if current.lower() in name.lower():
                    choices.append(app_commands.Choice(name=display_name, value=name))
            return choices[:25]
        except Exception:
            return []
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

    @app_commands.command(name="系統商店", description="開啟系統商店查看可購買的道具與材料")
    async def system_shop(self, interaction: discord.Interaction):
        # 1. 第一時間 defer 防止逾時
        await interaction.response.defer(ephemeral=True)
        try:
            embed = discord.Embed(
                title="🛒 【系統商店】",
                description="以下是目前販售的商品清單：\n請使用 `/購買` 或 `/賣出` 指令來進行交易！",
                color=discord.Color.blue()
            )
            
            for name, data in SHOP_ITEMS.items():
                embed.add_field(name=f"{name} (`{data['price']} G`)", value=data["description"], inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"❌ 系統商店顯示錯誤: {e}")
            try:
                await interaction.followup.send(f"❌ 發生未預期的錯誤：`{e}`", ephemeral=True)
            except:
                pass

    @app_commands.command(name="購買", description="從系統商店中購買指定的道具、材料或素材")
    @app_commands.rename(item_name="商品名稱", quantity="購買數量")
    @app_commands.describe(item_name="想購買的商品名稱", quantity="購買數量（預設為 1）")
    @app_commands.autocomplete(item_name=buy_autocomplete)
    async def buy_item(self, interaction: discord.Interaction, item_name: str, quantity: int = 1):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        if quantity <= 0:
            await interaction.followup.send("❌ 購買數量必須大於 0！", ephemeral=True)
            return

        try:
            success, msg = buy_item_in_db(user_id, item_name, quantity)
            embed = discord.Embed(
                title="🛒 【系統商店交易】",
                description=msg,
                color=discord.Color.gold() if success else discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"❌ 購買指令錯誤: {e}")
            await interaction.followup.send(f"❌ 購買過程發生未預期的錯誤：`{e}`", ephemeral=True)

    @app_commands.command(name="賣出", description="將背包中的多餘道具、材料或魚獲販售給系統商店換取金幣")
    @app_commands.rename(item_name="道具名稱", quantity="販售數量")
    @app_commands.describe(item_name="你想賣出的道具名稱", quantity="販售數量（預設為 1）")
    @app_commands.autocomplete(item_name=sell_autocomplete)
    async def sell_item(self, interaction: discord.Interaction, item_name: str, quantity: int = 1):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        if quantity <= 0:
            await interaction.followup.send("❌ 販賣數量必須大於 0！", ephemeral=True)
            return

        try:
            success, msg = sell_item_to_shop_in_db(user_id, item_name, quantity)
            embed = discord.Embed(
                title="💰 【系統商店回收中心】",
                description=msg,
                color=discord.Color.gold() if success else discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"❌ 賣出指令錯誤: {e}")
            await interaction.followup.send(f"❌ 販賣過程發生未預期的錯誤：`{e}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))
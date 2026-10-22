import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.select(
        placeholder="請選擇想要購買的道具...",
        options=[
            discord.SelectOption(label="生命藥水", description="恢復生命與應急使用 | 價格: 30 G", value="生命藥水"),
            discord.SelectOption(label="能量飲料", description="提升戰鬥續航力 | 價格: 50 G", value="能量飲料"),
        ]
    )
    async def select_shop(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer(ephemeral=True)
        item_name = select.values[0]
        cost = 30 if item_name == "生命藥水" else 50

        conn = get_db_connection()
        cursor = conn.cursor()

        # 檢查金幣
        cursor.execute("SELECT gold FROM players WHERE user_id = %s", (interaction.user.id,))
        res = cursor.fetchone()
        if not res or res[0] < cost:
            cursor.close()
            conn.close()
            await interaction.followup.send(f"❌ 你的金幣不足！購買【{item_name}】需要 {cost} G。", ephemeral=True)
            return

        # 扣除金幣並加入背包
        cursor.execute("UPDATE players SET gold = gold - %s WHERE user_id = %s", (cost, interaction.user.id))
        cursor.execute("""
            INSERT INTO inventory (user_id, item_name, quantity)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_id, item_name) DO UPDATE SET quantity = inventory.quantity + 1
        """, (interaction.user.id, item_name))
        conn.commit()
        cursor.close()
        conn.close()

        await interaction.followup.send(f"✅ 成功購買【{item_name}】！花費了 {cost} G，已放入背包。", ephemeral=True)

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shop", description="前往特務商城購買道具")
    async def shop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="🛒 【特務商城】",
            description="歡迎來到特務商城！請從下方選單選擇你要購買的補給品：\n\n• **生命藥水** - 30 G\n• **能量飲料** - 50 G",
            color=discord.Color.blue()
        )
        view = ShopView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))
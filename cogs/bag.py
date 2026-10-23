import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection
from db import use_item_in_db  # 引入剛剛寫好的資料庫函式

class BagCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="use", description="使用背包中的道具")
    @app_commands.describe(item_name="你想使用的道具名稱")
    async def use_item(self, interaction: discord.Interaction, item_name: str):
        # 呼叫資料庫處理邏輯
        success, message = use_item_in_db(interaction.user.id, item_name)
        
        if success:
            embed = discord.Embed(
                title="📦 道具使用成功",
                description=f"你使用了 **{item_name}**！\n效果：{message}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ 使用失敗",
                description=message,
                color=discord.Color.red()
            )
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(BagCog(bot))

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
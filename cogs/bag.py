import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection, use_item_in_db

class Bag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bag", description="查看你的隨身背包與道具")
    async def bag(self, interaction: discord.Interaction):
        # ⚡ 立即延遲回應，防止 3 秒超時
        await interaction.response.defer(ephemeral=True)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (interaction.user.id,))
            items = cursor.fetchall()
            cursor.close()
            conn.close()

            embed = discord.Embed(
                title=f"📦 [{interaction.user.display_name} · 隨身背包]",
                color=discord.Color.blue()
            )

            if not items:
                embed.description = "你的背包空空如也..."
            else:
                desc_list = []
                for item_name, qty in items:
                    desc_list.append(f"• **{item_name}** x `{qty}`")
                embed.description = "\n".join(desc_list)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ 發生錯誤：`{e}`", ephemeral=True)

    @app_commands.command(name="use", description="使用背包中的道具（例如：生命藥水）")
    @app_commands.describe(item_name="要使用的道具名稱")
    async def use_item(self, interaction: discord.Interaction, item_name: str):
        # ⚡ 立即延遲回應，防止 3 秒超時導致「該申請未回應」
        await interaction.response.defer(ephemeral=True)

        try:
            # 呼叫 db.py 中的道具使用邏輯
            success, msg = use_item_in_db(interaction.user.id, item_name)
            
            if success:
                embed = discord.Embed(title="📦 【道具使用成功】", description=msg, color=discord.Color.green())
            else:
                embed = discord.Embed(title="⚠️ 【道具使用失敗】", description=msg, color=discord.Color.orange())
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ 發生未預期的錯誤：`{e}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Bag(bot))
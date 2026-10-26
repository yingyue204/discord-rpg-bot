import discord
from discord.ext import commands
from discord import app_commands
from db import get_player_farm

class Farm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="農場", description="查看你的私人農場土地與作物狀態")
    async def farm_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        # 安全取得農場資料（已在 db.py 做過 try...finally 防死鎖）
        plots = get_player_farm(user_id)

        embed = discord.Embed(
            title="🌾 【私人農場】",
            description="以下是你的農田狀態：",
            color=discord.Color.green()
        )
        
        for plot in plots:
            status = plot["status"]
            if status == "empty":
                status_text = "🟢 空地 (可使用 /種植)"
            elif status == "growing":
                status_text = f"🌱 生長中 ({plot['crop_name']})"
            else:
                status_text = f"✨ 已成熟！ ({plot['crop_name']})"
                
            embed.add_field(name=f"第 {plot['plot_index']} 號田", value=status_text, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Farm(bot))
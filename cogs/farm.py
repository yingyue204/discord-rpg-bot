import discord
from discord.ext import commands
from discord import app_commands
import time
from db import get_player_farm, plant_crop, harvest_crop
import traceback

class Farm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    farm_group = app_commands.Group(name="農場", description="農場生活系統")

    @farm_group.command(name="農場狀態", description="查看你的農場狀態")
    async def farm_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            plots = get_player_farm(interaction.user.id)
            embed = discord.Embed(
                title="🌾 【個人農場】",
                description="照顧作物、享受田園風光，同時累積微薄的經驗值成長！",
                color=discord.Color.green()
            )
            
            current_time = time.time()
            for plot_index, crop_name, ready_timestamp, status in plots:
                if status == 'empty':
                    value = "🪹 狀態：空地（可使用 `/farm plant` 種植）"
                else:
                    remaining = int(ready_timestamp - current_time)
                    if remaining <= 0:
                        value = f"✨ 狀態：**{crop_name}** 已成熟！快使用 `/farm harvest` 收成！"
                    else:
                        value = f"🌱 狀態：**{crop_name}** 生長中...（剩餘 `{remaining}` 秒）"
                
                embed.add_field(name=f"第 {plot_index} 號田", value=value, inline=False)
                
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ 發生系統錯誤：`{e}`", ephemeral=True)

    @farm_group.command(name="農場作物", description="在指定農田種植作物")
    @app_commands.describe(plot_index="農田編號 (1~3)", crop_name="作物名稱 (需擁有對應種子，例如：小麥)")
    async def farm_plant(self, interaction: discord.Interaction, plot_index: int, crop_name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            if plot_index < 1 or plot_index > 3:
                await interaction.followup.send("❌ 農田編號只能是 1、2 或 3！", ephemeral=True)
                return
                
            success, message = plant_crop(interaction.user.id, plot_index, crop_name)
            embed = discord.Embed(
                title="🌱 【農場種植】",
                description=message,
                color=discord.Color.green() if success else discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ 發生系統錯誤：`{e}`", ephemeral=True)

    @farm_group.command(name="農作物", description="收成已成熟的農作物")
    @app_commands.describe(plot_index="農田編號 (1~3)")
    async def farm_harvest(self, interaction: discord.Interaction, plot_index: int):
        await interaction.response.defer(ephemeral=True)
        try:
            if plot_index < 1 or plot_index > 3:
                await interaction.followup.send("❌ 農田編號只能是 1、2 或 3！", ephemeral=True)
                return
                
            success, message = harvest_crop(interaction.user.id, plot_index)
            embed = discord.Embed(
                title="🌾 【農場收成】",
                description=message,
                color=discord.Color.green() if success else discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ 發生系統錯誤：`{e}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Farm(bot))
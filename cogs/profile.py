import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="屬性", description="查看個人特務檔案")
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role, hp, max_hp, atk, def, speed, gold FROM players WHERE user_id = ?", (interaction.user.id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result or not result[0]:
            role, hp, max_hp, atk, def_val, speed, gold = "未選擇", 100, 100, 25, 10, 20, 100
        else:
            role, hp, max_hp, atk, def_val, speed, gold = result

        embed = discord.Embed(title=f"📊 [{interaction.user.name} · 特務檔案]", color=discord.Color.green())
        embed.add_field(name="🏷️ 當前職業", value=f"**{role}**", inline=False)
        embed.add_field(name="❤️ 生命值", value=f"{hp}/{max_hp}", inline=True)
        embed.add_field(name="⚔️ 攻擊力", value=f"{atk}", inline=True)
        embed.add_field(name="🛡️ 防禦力", value=f"{def_val}", inline=True)
        embed.add_field(name="⚡ 速度", value=f"{speed}", inline=True)
        embed.add_field(name="💰 金幣", value=f"{gold} G", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Profile(bot))
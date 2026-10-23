import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="屬性", description="查看自己的個人特務檔案與屬性數值")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查詢玩家資料（只讀取 hp, max_hp, atk, def, gold，不再包含 spd/速度）
        cursor.execute("SELECT role, hp, max_hp, atk, def, gold FROM players WHERE user_id = ?", (interaction.user.id,))
        player = cursor.fetchone()

        if not player or not player[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/setup_roles` 面板選擇職業。", ephemeral=True)
            return

        role_name, hp, max_hp, atk, player_def, gold = player
        cursor.close()
        conn.close()

        # 建立個人檔案 Embed（已將速度欄位完全刪除）
        embed = discord.Embed(
            title=f"📊 [{interaction.user.display_name} · 特務檔案]",
            color=discord.Color.green()
        )
        embed.add_field(name="🏷️ 當前職業", value=f"**{role_name}**", inline=False)
        embed.add_field(name="❤️ 生命值", value=f"{hp}/{max_hp}", inline=True)
        embed.add_field(name="⚔️ 攻擊力", value=f"{atk}", inline=True)
        embed.add_field(name="🛡️ 防禦力", value=f"{player_def}", inline=True)
        embed.add_field(name="💰 金幣", value=f"{gold} G", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Status(bot))
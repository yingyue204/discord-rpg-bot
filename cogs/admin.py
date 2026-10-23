import discord
from discord.ext import commands
from discord import app_commands
from db import reset_player_data

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reset_player", description="【管理員專用】重置指定玩家的遊戲記錄與背包")
    @app_commands.describe(member="要重置記錄的玩家")
    @app_commands.checks.has_permissions(administrator=True)  # 限制必須是伺服器管理員
    async def reset_player(self, interaction: discord.Interaction, member: discord.Member):
        # 呼叫 db.py 中的清除函式
        reset_player_data(member.id)

        embed = discord.Embed(
            title="⚙️ 【管理員操作】記錄已重置",
            description=f"已成功清除玩家 **{member.display_name}** 的所有角色記錄與背包道具！\n該玩家現在可以重新選擇身份並展開全新測試。",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 權限不足時的防呆提示
    @reset_player.error
    async def reset_player_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ 你沒有權限使用此指令！此指令僅限具有**管理員 (Administrator)** 權限的人使用。", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ 發生錯誤：{error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
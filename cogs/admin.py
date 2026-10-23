import discord
from discord.ext import commands
from discord import app_commands
from db import reset_player_data

# 請在這裡設定你的職業身份組名稱清單
ROLE_NAMES = ["駭客", "磁暴重裝", "異能覺醒", "神射手"]

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reset_player", description="【管理員專用】重置指定玩家的遊戲記錄、背包與身份組")
    @app_commands.describe(member="要重置記錄的玩家")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_player(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)

        # 1. 清除資料庫數據（players 表格 + inventory 背包）
        reset_player_data(member.id)

        # 2. 找出玩家身上擁有的職業身份組並自動移除
        removed_roles = []
        for role in member.roles:
            if role.name in ROLE_NAMES:
                try:
                    await member.remove_roles(role)
                    removed_roles.append(role.name)
                except discord.Forbidden:
                    await interaction.followup.send("⚠️ 機器人權限不足，無法移除身份組！請確保機器人的身分組位階高於職業身分組。", ephemeral=True)
                    return

        # 3. 組成回應訊息
        role_msg = f"並移除了身份組：**{', '.join(removed_roles)}**" if removed_roles else "（該玩家當前沒有相關職業身份組）"
        
        embed = discord.Embed(
            title="⚙️ 【管理員操作】記錄與身份組已重置",
            description=f"已成功清除玩家 **{member.display_name}** 的所有遊戲記錄與背包，{role_msg}！\n該玩家現在可以重新使用 `/選擇身份` 進行全新測試。",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @reset_player.error
    async def reset_player_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ 你沒有權限使用此指令！此指令僅限具有**管理員 (Administrator)** 權限的人使用。", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ 發生錯誤：{error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
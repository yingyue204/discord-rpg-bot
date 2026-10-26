import discord
from discord.ext import commands
from discord import app_commands
from db import reset_player_data

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="重製玩家資料", description="【管理員】重置指定玩家的遊戲資料與身分組")
    @app_commands.describe(member="要重置的玩家")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_player(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)

        user_id = member.id
        guild = interaction.guild

        # 1. 清除資料庫中的角色與背包資料
        reset_player_data(user_id)

        # 2. 移除該玩家身上的所有職業身分組
        role_names = ["駭客", "磁暴重裝", "異能覺醒", "神射手"]
        removed_roles = []
        for r_name in role_names:
            role_obj = discord.utils.get(guild.roles, name=r_name)
            if role_obj and role_obj in member.roles:
                try:
                    await member.remove_roles(role_obj)
                    removed_roles.append(r_name)
                except discord.Forbidden:
                    pass

        # 3. 清除當前頻道中由機器人發送的歷史訊息
        deleted_msgs_count = 0
        try:
            # 優先使用 bulk 快速批量刪除
            deleted = await interaction.channel.purge(
                limit=100, 
                check=lambda m: m.author == interaction.client.user,
                bulk=True
            )
            deleted_msgs_count = len(deleted)
        except discord.HTTPException:
            # 若包含超過 14 天的舊訊息，降級改用逐筆刪除 (bulk=False)
            try:
                deleted = await interaction.channel.purge(
                    limit=100, 
                    check=lambda m: m.author == interaction.client.user,
                    bulk=False
                )
                deleted_msgs_count = len(deleted)
            except Exception:
                pass
        except discord.Forbidden:
            pass

        await interaction.followup.send(
            f"✅ 成功重置玩家 **{member.display_name}** 的資料！\n"
            f"• 已清空資料庫記錄與背包\n"
            f"• 已移除身分組：`{', '.join(removed_roles) if removed_roles else '無'}`\n"
            f"• 已清理頻道中機器人的 `{deleted_msgs_count}` 則回覆紀錄",
            ephemeral=True
        )

    @reset_player.error
    async def reset_player_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ 你沒有權限使用此指令！", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
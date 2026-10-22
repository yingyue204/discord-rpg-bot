import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class RoleSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    ROLE_STATS = {
        "駭客": {"hp": 100, "atk": 25, "def": 10, "speed": 35},
        "磁暴重裝": {"hp": 180, "atk": 18, "def": 35, "speed": 15},
        "異能覺醒": {"hp": 110, "atk": 35, "def": 15, "speed": 20},
        "神射手": {"hp": 115, "atk": 30, "def": 16, "speed": 25}
    }

    @discord.ui.select(
        placeholder="請選擇你的特務職業...",
        options=[
            discord.SelectOption(label="駭客", description="專精系統超頻與極速專家"),
            discord.SelectOption(label="磁暴重裝", description="重型外骨骼防禦專家"),
            discord.SelectOption(label="異能覺醒", description="高攻擊力超自然異能者"),
            discord.SelectOption(label="神射手", description="高穿透電磁步槍遠程專家"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer(ephemeral=True)
        selected_role = select.values[0]
        stats = self.ROLE_STATS[selected_role]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT role FROM players WHERE user_id = ?", (interaction.user.id,))
        result = cursor.fetchone()

        if result and result[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send(f"⚠️ 你已經綁定過職業【**{result[0]}**】了！", ephemeral=True)
            return

        cursor.execute("""
            INSERT OR REPLACE INTO players (user_id, role, hp, max_hp, atk, def, speed, gold)
            VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT gold FROM players WHERE user_id = ?), 100))
        """, (interaction.user.id, selected_role, stats["hp"], stats["hp"], stats["atk"], stats["def"], stats["speed"], interaction.user.id))

        conn.commit()
        cursor.close()
        conn.close()

        guild = interaction.guild
        member = interaction.user
        role_to_give = discord.utils.get(guild.roles, name=selected_role)
        role_msg = ""
        if role_to_give:
            try:
                await member.add_roles(role_to_give)
                role_msg = f"\n✨ 已成功為你掛載 Discord 身分組：【{selected_role}】"
            except Exception as e:
                role_msg = f"\n⚠️ 身分組賦予失敗：{e}"

        await interaction.followup.send(
            f"🎉 成功選擇職業【**{selected_role}**】！\n❤️ 血量: {stats['hp']} | ⚔️ 攻擊力: {stats['atk']}{role_msg}",
            ephemeral=True
        )

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_roles")
    @commands.has_permissions(administrator=True)
    async def setup_roles_prefix(self, ctx):
        try:
            await ctx.message.delete()
        except:
            pass
        embed = discord.Embed(title="💻 【虛擬次元觀測站 · 特務職業指南】", description="請從下方選單選擇職業身份：")
        view = RoleSelectView()
        await ctx.send(embed=embed, view=view)

    @app_commands.command(name="選擇身份", description="選擇你的角色職業身份")
    async def select_role_cmd(self, interaction: discord.Interaction):
        view = RoleSelectView()
        await interaction.response.send_message("請點選下方選單選擇你的職業身份：", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Roles(bot))
import discord
from discord import app_commands
from discord.ext import commands

ALL_CLASSES = ["駭客", "磁暴重裝", "異能覺醒", "神射手"]

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(self.RoleSelectView())

    class RoleSelectView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        async def assign_discord_role(self, interaction: discord.Interaction, target_role_name: str):
            await interaction.response.defer(ephemeral=True)
            guild = interaction.guild
            member = interaction.user

            if not guild:
                await interaction.followup.send("❌ 此指令只能在伺服器中使用！", ephemeral=True)
                return

            existing_roles = [r.name for r in member.roles if any(k in r.name for k in ALL_CLASSES)]
            
            if existing_roles:
                current_role_name = existing_roles[0].name
                await interaction.followup.send(
                    f"⛔ **無法變更職業！**\n你已經選擇過初始職業：**【{current_role_name}】**。\n職業選擇後即無法自行更換！", 
                    ephemeral=True
                )
                return

            target_role = discord.utils.get(guild.roles, name=target_role_name)
            if not target_role:
                try:
                    target_role = await guild.create_role(name=target_role_name, reason="RPG 機器人自動建立職業身分組")
                except discord.Forbidden:
                    await interaction.followup.send(f"⚠️ 機器人權限不足，無法自動建立身分組【{target_role_name}】！", ephemeral=True)
                    return

            try:
                await member.add_roles(target_role)
                await interaction.followup.send(f"🎉 **綁定成功！**\n你已綁定 Discord 職業身分組：**【{target_role.name}】**！職業已鎖定。", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("⚠️ 機器人權限不足（請將機器人的身分組順序拉到最高）！", ephemeral=True)

        @discord.ui.button(label="駭客", style=discord.ButtonStyle.primary, custom_id="role_hacker_btn")
        async def role_hacker(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.assign_discord_role(interaction, "駭客")

        @discord.ui.button(label="磁暴重裝", style=discord.ButtonStyle.success, custom_id="role_heavy_btn")
        async def role_heavy(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.assign_discord_role(interaction, "磁暴重裝")

        @discord.ui.button(label="異能覺醒", style=discord.ButtonStyle.danger, custom_id="role_esper_btn")
        async def role_esper(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.assign_discord_role(interaction, "異能覺醒")

        @discord.ui.button(label="神射手", style=discord.ButtonStyle.secondary, custom_id="role_archer_btn")
        async def role_archer(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.assign_discord_role(interaction, "神射手")

    @app_commands.command(name="選擇身分", description="選擇你的冒險職業，選擇後將永久鎖定")
    async def choose_role(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="🏷️ [虛擬次元觀測站・特務身分領取]",
            description="⚠️ **注意：職業一經選擇即無法更換，請謹慎考慮！**\n請詳閱下方特務職業檔案後，點擊對應按鈕進行身分綁定。",
            color=discord.Color.blue()
        )
        embed.add_field(name="駭客", value="• 職業簡介：專精於系統超頻與軟體穿透的極速專家。\n• 初始屬性：❤️ 血量 100 | ⚔️ 攻擊 25 | 🛡️ 防禦 10 | ⚡ 速度 35 | 🌟 爆擊 20%", inline=False)
        embed.add_field(name="磁暴重裝", value="• 職業簡介：配備重型外骨骼動力裝甲與電磁防禦盾。\n• 初始屬性：❤️ 血量 180 | ⚔️ 攻擊 18 | 🛡️ 防禦 35 | ⚡ 速度 15 | 🌟 爆擊 5%", inline=False)
        embed.add_field(name="異能覺醒", value="• 職業簡介：突破人體與科技極限的超自然異能者。\n• 初始屬性：❤️ 血量 110 | ⚔️ 攻擊 35 (最高) | 🛡️ 防禦 15 | ⚡ 速度 22 | 🌟 爆擊 5%", inline=False)
        embed.add_field(name="神射手", value="• 職業簡介：配備高倍率戰術鏡與高穿透電磁步槍的遠程專家。\n• 初始屬性：❤️ 血量 115 | ⚔️ 攻擊 30 | 🛡️ 防禦 10 | ⚡ 速度 26 | 🌟 爆擊 15%", inline=False)
        await interaction.followup.send(embed=embed, view=self.RoleSelectView(), ephemeral=True)

    @commands.command(name="setup_roles", description="發送純職業介紹說明面板")
    @commands.has_permissions(administrator=True)
    async def setup_roles_prefix(self, ctx):
        try:
            await ctx.message.delete()
        except:
            pass

        embed = discord.Embed(
            title="📖 [虛擬次元觀測站・特務職業指南]",
            description="歡迎來到虛擬次元！以下為各大特務職業的詳細介紹與初始屬性配置：",
            color=discord.Color.dark_embed()
        )
        embed.add_field(name="駭客", value="• 職業簡介：專精於系統超頻與軟體穿透的極速專家。\n• 初始屬性：❤️ 血量 100 | ⚔️ 攻擊 25 | 🛡️ 防禦 10 | ⚡ 速度 35 | 🌟 爆擊 20%", inline=False)
        embed.add_field(name="磁暴重裝", value="• 職業簡介：配備重型外骨骼動力裝甲與電磁防禦盾。\n• 初始屬性：❤️ 血量 180 | ⚔️ 攻擊 18 | 🛡️ 防禦 35 | ⚡ 速度 15 | 🌟 爆擊 5%", inline=False)
        embed.add_field(name="異能覺醒", value="• 職業簡介：突破人體與科技極限的超自然異能者。\n• 初始屬性：❤️ 血量 110 | ⚔️ 攻擊 35 (最高) | 🛡️ 防禦 15 | ⚡ 速度 22 | 🌟 爆擊 5%", inline=False)
        embed.add_field(name="神射手", value="• 職業簡介：配備高倍率戰術鏡與高穿透電磁步槍的遠程專家。\n• 初始屬性：❤️ 血量 115 | ⚔️ 攻擊 30 | 🛡️ 防禦 10 | ⚡ 速度 26 | 🌟 爆擊 15%", inline=False)
        embed.set_footer(text="請使用 /選擇身分 指令來進行正式的職業身分綁定。")
        await ctx.send(embed=embed, view=self.RoleSelectView())

async def setup(bot):
    await bot.add_cog(Roles(bot))
import discord
from discord.ext import commands
from discord import app_commands
from db import get_player_status

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="屬性", description="查看個人屬性面板與成長進度")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        player = get_player_status(interaction.user.id)
        if not player:
            await interaction.followup.send("❌ 你尚未建立角色，請先選擇職業！", ephemeral=True)
            return

        # 解構資料庫回傳的數值
        (role_name, level, exp, hp, max_hp, mp, max_mp, 
         stamina, max_stamina, atk, defense, gold, 
         weapon_name, weapon_atk, armor_name, armor_def) = player

        # 計算當前等級所需的升級總經驗值 (與 gain_player_exp 公式一致)
        exp_needed = level * 100

        embed = discord.Embed(
            title=f"🛡️ 【{interaction.user.display_name} 的特務屬性】",
            color=discord.Color.blue()
        )
        
        # 🌟 核心重點：加入等級與經驗值進度
        embed.add_field(name="👑 職業與等級", value=f"**職業**：{role_name or '無'}\n**等級**：`Lv. {level}`", inline=True)
        embed.add_field(name="✨ 經驗值進度", value=f"`{exp} / {exp_needed} EXP`", inline=True)
        embed.add_field(name="💰 持有金幣", value=f"`{gold} G`", inline=True)

        embed.add_field(name="❤️ 生命值 (HP)", value=f"`{hp} / {max_hp}`", inline=True)
        embed.add_field(name="💧 魔力值 (MP)", value=f"`{mp} / {max_mp}`", inline=True)
        embed.add_field(name="⚡ 体力值 (Stamina)", value=f"`{stamina} / {max_stamina}`", inline=True)

        embed.add_field(name="⚔️ 攻擊力", value=f"`{atk}` (+{weapon_atk})", inline=True)
        embed.add_field(name="🛡️ 防禦力", value=f"`{defense}` (+{armor_def})", inline=True)
        embed.add_field(name="🗡️ 裝備", value=f"武器: {weapon_name or '無'}\n防具: {armor_name or '無'}", inline=True)

        embed.set_footer(text="💡 打怪或農場收成都可以獲得經驗值來提升等級！")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Profile(bot))
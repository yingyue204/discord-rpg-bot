import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="屬性", description="查看你的特務個人數值與狀態")
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        
        conn = sqlite3.connect("rpg_game.db")
        cursor = conn.cursor()
        cursor.execute("SELECT hp, atk, defense, gold FROM players WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            # 若無記錄則初始化預設數值
            cursor.execute("INSERT INTO players (user_id, hp, atk, defense, gold) VALUES (?, 100, 25, 10, 50)", (user_id,))
            conn.commit()
            hp, atk, defense, gold = 100, 25, 10, 50
        else:
            hp, atk, defense, gold = row
            
        conn.close()
        
        embed = discord.Embed(
            title=f"📊 [{interaction.user.display_name}・特務檔案]",
            color=discord.Color.green()
        )
        embed.add_field(name="❤️ 生命值 (HP)", value=str(hp), inline=True)
        embed.add_field(name="⚔️ 攻擊力", value=str(atk), inline=True)
        embed.add_field(name="🛡️ 防禦力", value=str(defense), inline=True)
        embed.add_field(name="💰 金幣資產", value=f"{gold} G", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Profile(bot))
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="屬性", description="查看你的特務個人數值與狀態")
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        
        conn = sqlite3.connect("rpg_game.db")
        cursor = conn.cursor()
        cursor.execute("SELECT hp, atk, defense, gold FROM players WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            # 若無記錄則初始化預設數值
            cursor.execute("INSERT INTO players (user_id, hp, atk, defense, gold) VALUES (?, 100, 25, 10, 50)", (user_id,))
            conn.commit()
            hp, atk, defense, gold = 100, 25, 10, 50
        else:
            hp, atk, defense, gold = row
            
        conn.close()
        
        embed = discord.Embed(
            title=f"📊 [{interaction.user.display_name}・特務檔案]",
            color=discord.Color.green()
        )
        embed.add_field(name="❤️ 生命值 (HP)", value=str(hp), inline=True)
        embed.add_field(name="⚔️ 攻擊力", value=str(atk), inline=True)
        embed.add_field(name="🛡️ 防禦力", value=str(defense), inline=True)
        embed.add_field(name="💰 金幣資產", value=f"{gold} G", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Profile(bot))

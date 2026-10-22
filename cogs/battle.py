import discord
from discord.ext import commands
from discord import app_commands
import random
from db import get_db_connection

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="打怪", description="遭遇怪物並進行戰鬥")
    async def battle(self, interaction: discord.Interaction):
        await interaction.response.defer()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role, hp, atk, def, gold FROM players WHERE user_id = ?", (interaction.user.id,))
        player = cursor.fetchone()

        if not player or not player[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 你尚未選擇職業！請先使用 `/選擇身份`。", ephemeral=True)
            return

        role_name, player_hp, player_atk, player_def, player_gold = player
        monster = random.choice([
            {"name": "👾 變異流浪體", "hp": 60, "atk": 15, "gold": 15},
            {"name": "🤖 狂暴巡邏機械", "hp": 90, "atk": 22, "gold": 25}
        ])
        
        player_dmg = max(1, player_atk - 2)
        reward_gold = monster["gold"]

        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (reward_gold, interaction.user.id))
        conn.commit()
        cursor.close()
        conn.close()

        embed = discord.Embed(title="🎉 【戰鬥勝利！】", color=discord.Color.green())
        embed.description = f"你對 **{monster['name']}** 造成了 **{player_dmg}** 點傷害並成功擊敗對方！"
        embed.add_field(name="💰 戰利品", value=f"**+{reward_gold} G**", inline=True)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Battle(bot))
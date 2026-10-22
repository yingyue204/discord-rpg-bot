import discord
from discord.ext import commands
from discord import app_commands
import random
from db import get_db_connection

class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="adventure", description="前往野外進行冒險與搜刮")
    async def adventure(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        found_item = random.choice(["急救包", "稀有金屬", "生命藥水", "鐵劍碎片"])
        found_gold = random.randint(5, 15)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("INSERT OR IGNORE INTO players (user_id, gold, hp) VALUES (?, 100, 100)", (interaction.user.id,))
        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (found_gold, interaction.user.id))
        
        cursor.execute("""
            INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)
            ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + 1
        """, (interaction.user.id, found_item))

        conn.commit()
        cursor.close()
        conn.close()

        embed = discord.Embed(title="🛡️ 【冒險搜刮成功】", color=discord.Color.green())
        embed.add_field(name="📦 獲得道具", value=f"**{found_item} x1**", inline=True)
        embed.add_field(name="💰 獲得金幣", value=f"**+{found_gold} G**", inline=True)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Adventure(bot))
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

class Bag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="背包", description="查看你目前擁有的所有冒險物資與道具")
    async def bag(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        
        conn = sqlite3.connect("rpg_game.db")
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        embed = discord.Embed(
            title=f"🎒 [{interaction.user.display_name} 的隨身背包]",
            color=discord.Color.gold()
        )
        
        if rows:
            desc = ""
            for item, qty in rows:
                desc += f"• **{item}** x {qty}\n"
            embed.description = desc
        else:
            embed.description = "你的背包目前空空如也，快去 `/新手村` 搜刮物資吧！"
            
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Bag(bot))
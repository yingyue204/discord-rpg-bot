import discord
from discord.ext import commands
from discord import app_commands
import random
from db import get_db_connection

class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="adventure", description="前往新手村或野外進行冒險與搜刮！")
    async def adventure(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        possible_items = ["急救包", "稀有金屬", "生命藥水", "鐵劍碎片"]
        found_item = random.choice(possible_items)
        found_gold = random.randint(5, 15)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO players (user_id, gold, hp) 
            VALUES (%s, 100, 100) 
            ON CONFLICT (user_id) DO NOTHING
        """, (interaction.user.id,))
        
        cursor.execute("UPDATE players SET gold = gold + %s WHERE user_id = %s", (found_gold, interaction.user.id))

        cursor.execute("SELECT quantity FROM inventory WHERE user_id = %s AND item_name = %s", (interaction.user.id, found_item))
        result = cursor.fetchone()

        if result:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = %s AND item_name = %s", (interaction.user.id, found_item))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (%s, %s, 1)", (interaction.user.id, found_item))

        conn.commit()
        cursor.close()
        conn.close()

        embed = discord.Embed(
            title="🛡️ 【冒險成功：艾底索德 (Episode-0)】",
            description=f"你在探索的途中有了收穫！",
            color=discord.Color.green()
        )
        embed.add_field(name="📦 獲得道具", value=f"**{found_item} x1**", inline=True)
        embed.add_field(name="💰 獲得金幣", value=f"**{found_gold} G**", inline=True)
        embed.set_footer(text="提示：使用 /屬性 或 /adventure 可以隨時進行互動！")

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Adventure(bot))
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shop", description="查看武器與道具商店")
    async def shop(self, interaction: discord.Interaction):
        conn = sqlite3.connect("rpg.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS inventory (user_id INTEGER, item_name TEXT, quantity INTEGER)")
        conn.commit()
        conn.close()

        embed = discord.Embed(title="🛒 冒險者商店", description="使用 `/buy <商品名稱>` 來購買武器或道具！", color=discord.Color.gold())
        embed.add_field(name="⚔️ 鐵劍 (攻擊力 +10)", value="價格: 100 G", inline=False)
        embed.add_field(name="🛡️ 鐵甲 (防禦力 +5)", value="價格: 80 G", inline=False)
        embed.add_field(name="🧪 生命藥水 (恢復 50 HP)", value="價格: 30 G", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="購買商店中的物品")
    @app_commands.describe(item="你想購買的物品名稱")
    @app_commands.choices(item=[
        app_commands.Choice(name="鐵劍", value="iron_sword"),
        app_commands.Choice(name="鐵甲", value="iron_armor"),
        app_commands.Choice(name="生命藥水", value="health_potion")
    ])
    async def buy(self, interaction: discord.Interaction, item: str):
        prices = {
            "iron_sword": 100,
            "iron_armor": 80,
            "health_potion": 30
        }
        item_names = {
            "iron_sword": "鐵劍",
            "iron_armor": "鐵甲",
            "health_potion": "生命藥水"
        }
        
        cost = prices[item]
        item_name = item_names[item]

        conn = sqlite3.connect("rpg.db")
        cursor = conn.cursor()
        
        # 檢查玩家金幣
        cursor.execute("SELECT gold FROM players WHERE user_id = ?", (interaction.user.id,))
        result = cursor.fetchone()
        
        if not result or result[0] < cost:
            conn.close()
            await interaction.response.send_message(f"❌ 你的金幣不足！購買 **{item_name}** 需要 {cost} G。", ephemeral=True)
            return

        # 扣除金幣並加入背包
        cursor.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (cost, interaction.user.id))
        
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (interaction.user.id, item_name))
        inv_result = cursor.fetchone()
        
        if inv_result:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (interaction.user.id, item_name))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (interaction.user.id, item_name))
            
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"🎉 成功購買 **{item_name}**！花費了 {cost} G。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))
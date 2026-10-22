import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection  # 引入雲端資料庫連線模組

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shop", description="查看武器與道具商店價格")
    async def shop(self, interaction: discord.Interaction):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 確保背包表格存在 (PostgreSQL 語法)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                item_name TEXT,
                quantity INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

        # 建立帶有明確價格標示的商店面板
        embed = discord.Embed(
            title="🛒 【虛擬次元 · 特務裝備商店】", 
            description="請使用 `/buy <商品名稱>` 來進行裝備或道具購買！\n━━━━━━━━━━━━━━━━━━━━", 
            color=discord.Color.gold()
        )
        embed.add_field(name="⚔️ 鐵劍 (武器)", value="• 屬性效果：攻擊力 +10\n販售價格：**100 G**", inline=False)
        embed.add_field(name="🛡️ 鐵甲 (防具)", value="• 屬性效果：防禦力 +5\n販售價格：**80 G**", inline=False)
        embed.add_field(name="🧪 生命藥水 (消耗品)", value="• 屬性效果：恢復 50 HP\n販售價格：**30 G**", inline=False)
        embed.set_footer(text="提示：可以使用 /adventure 冒險獲取金幣來購買裝備！")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="購買商店中的物品")
    @app_commands.describe(item="你想購買的物品名稱")
    @app_commands.choices(item=[
        app_commands.Choice(name="⚔️ 鐵劍 (100 G)", value="iron_sword"),
        app_commands.Choice(name="🛡️ 鐵甲 (80 G)", value="iron_armor"),
        app_commands.Choice(name="🧪 生命藥水 (30 G)", value="health_potion")
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

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 檢查玩家金幣 (使用 %s 佔位符)
        cursor.execute("SELECT gold FROM players WHERE user_id = %s", (interaction.user.id,))
        result = cursor.fetchone()
        
        if not result or result[0] < cost:
            cursor.close()
            conn.close()
            await interaction.response.send_message(f"❌ 你的金幣不足！購買 **{item_name}** 需要 {cost} G。", ephemeral=True)
            return

        # 扣除金幣並加入背包 (使用 %s 佔位符)
        cursor.execute("UPDATE players SET gold = gold - %s WHERE user_id = %s", (cost, interaction.user.id))
        
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = %s AND item_name = %s", (interaction.user.id, item_name))
        inv_result = cursor.fetchone()
        
        if inv_result:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = %s AND item_name = %s", (interaction.user.id, item_name))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (%s, %s, 1)", (interaction.user.id, item_name))
            
        conn.commit()
        cursor.close()
        conn.close()

        await interaction.response.send_message(f"🎉 成功購買 **{item_name}**！花費了 {cost} G。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))
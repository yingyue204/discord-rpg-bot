import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# 商店商品清單與詳細介紹
SHOP_ITEMS = {
    "生命藥水": {"price": 30, "desc": "基礎治療道具，使用後恢復 30 點生命值。"},
    "急救包": {"price": 60, "desc": "高效急救醫療包，使用後恢復 50 點生命值。"},
    "魔力藥水": {"price": 40, "desc": "補充精神力的藥劑，使用後恢復 20 點 MP。"},
    "能量飲料": {"price": 75, "desc": "高科技提神飲料，使用後瞬間恢復 40 點 MP。"},
    "神秘寶箱": {"price": 200, "desc": "內含各品質武器與防具的神秘寶箱，可使用 `/open_chest` 開啟。"}
}

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shop", description="查看新手村商店與商品介紹")
    async def shop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="🛒 【新手村補給商店】",
            description="歡迎來到商店！使用 `/buy [道具名稱]` 即可購買心儀的物資。",
            color=discord.Color.gold()
        )

        for item_name, data in SHOP_ITEMS.items():
            embed.add_field(
                name=f"📌 {item_name} — 💰 `{data['price']} G`",
                value=f"• **介紹**：{data['desc']}",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="buy", description="從商店購買指定道具")
    @app_commands.describe(item_name="想購買的道具名稱", quantity="購買數量（預設 1 個）")
    async def buy(self, interaction: discord.Interaction, item_name: str, quantity: int = 1):
        await interaction.response.defer(ephemeral=True)

        if item_name not in SHOP_ITEMS:
            await interaction.followup.send(f"❌ 商店中沒有販售 **{item_name}**！請輸入 `/shop` 查看商品清單。", ephemeral=True)
            return

        if quantity <= 0:
            await interaction.followup.send("❌ 購買數量必須大於 0！", ephemeral=True)
            return

        total_cost = SHOP_ITEMS[item_name]["price"] * quantity

        conn = get_db_connection()
        cursor = conn.cursor()

        # 檢查玩家金幣
        cursor.execute("INSERT OR IGNORE INTO players (user_id, gold) VALUES (?, 0)", (interaction.user.id,))
        conn.commit()

        cursor.execute("SELECT gold FROM players WHERE user_id = ?", (interaction.user.id,))
        player_gold = cursor.fetchone()[0]

        if player_gold < total_cost:
            cursor.close()
            conn.close()
            await interaction.followup.send(
                f"❌ 你的金幣不足！購買 `{quantity}` 個 **{item_name}** 需要 `{total_cost} G`，但你身上只有 `{player_gold} G`。",
                ephemeral=True
            )
            return

        # 扣除金幣
        cursor.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (total_cost, interaction.user.id))

        # 新增道具到背包
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (interaction.user.id, item_name))
        item_row = cursor.fetchone()

        if item_row:
            cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?", (quantity, interaction.user.id, item_name))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)", (interaction.user.id, item_name, quantity))

        conn.commit()
        cursor.close()
        conn.close()

        embed = discord.Embed(
            title="🛍️ 【購買成功】",
            description=f"成功購買了 **{item_name}** x `{quantity}`！\n總共花費：`{total_cost} G`",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))
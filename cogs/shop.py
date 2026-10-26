import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# 商店商品清單與詳細介紹
# 🛒 完整綜合商城商品資料庫設定
SHOP_ITEMS = {
    # 🧪 1. 藥水與補給品類
    "生命藥水": {
        "price": 30,
        "type": "consumable",
        "description": "基礎治療道具，使用後恢復 30 點生命值。"
    },
    "急救包": {
        "price": 60,
        "type": "consumable",
        "description": "高效急救醫療包，使用後恢復 50 點生命值。"
    },
    "魔力藥水": {
        "price": 40,
        "type": "consumable",
        "description": "補充精神力的藥劑，使用後恢復 20 點 MP。"
    },
    "能量飲料": {
        "price": 75,
        "type": "consumable",
        "description": "高科技提神飲料，使用後瞬間恢復 40 點 MP。"
    },

    # 🎁 2. 特殊道具與寶箱類
    "神秘寶箱": {
        "price": 200,
        "type": "special",
        "description": "內含各品質武器與防具的神秘寶箱，可使用 `/open_chest` 開啟。"
    },

    # 🌾 3. 農場作物／種子類
    "小麥": {
        "price": 20, 
        "type": "material", 
        "description": "基礎烘焙與麵食原料，用途極廣。"
    },
    "米": {
        "price": 25, 
        "type": "material", 
        "description": "香甜白米，製作壽司與飯類料理必備。"
    },
    "蔬菜": {
        "price": 30, 
        "type": "material", 
        "description": "新鮮蔬菜，提供均衡營養的烹飪配料。"
    },
    "水果": {
        "price": 35, 
        "type": "material", 
        "description": "多汁水果，可用於製作香檳氣泡水與甜點。"
    },
    "香料": {
        "price": 40, 
        "type": "material", 
        "description": "去腥提味的關鍵調味料，主廚料理不可或缺。"
    },
    "蔥": {
        "price": 25, 
        "type": "material", 
        "description": "香氣十足的青蔥，製作蔥油餅的靈魂。"
    },
    "鮮魚": {
        "price": 50, 
        "type": "material", 
        "description": "新鮮漁獲，用於製作壽司與香煎魚。"
    },

    # 🥩 4. 基礎肉品類
    "生肉": {
        "price": 45, 
        "type": "material", 
        "description": "多種中西式肉類料理的基礎原料。"
    },

    # 🔨 5. 料理台升級專用素材
    "鐵塊": {
        "price": 200, 
        "type": "upgrade", 
        "description": "堅固的鐵塊，料理台升級至 Lv.2 的必要素材（需求 5 個）。"
    },
    "魔導金屬": {
        "price": 1000, 
        "type": "upgrade", 
        "description": "稀有的魔法金屬，料理台升級至 Lv.3 的必要素材（需求 3 個）。"
    },

    # 🏡 6. 牧場動物與飼養許可
    "乳牛": {
        "price": 300, 
        "type": "animal", 
        "description": "溫馴的乳牛，放置於牧場柵欄後可定時產出「牛奶」。"
    },
    "肉牛": {
        "price": 400, 
        "type": "animal", 
        "description": "壯碩的肉牛，放置於牧場柵欄後可定時產出「高級肉塊」。"
    },
    "豬": {
        "price": 250, 
        "type": "animal", 
        "description": "活力十足的家豬，放置於牧場柵欄後可定時產出「五花肉」。"
    },
    "雞": {
        "price": 150, 
        "type": "animal", 
        "description": "會下蛋的母雞，放置於牧場柵欄後可定時產出「雞蛋」。"
    }
}

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="系統商店", description="查看系統商店與商品介紹")
    async def shop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="🛒 【系統補給商店】",
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

    @app_commands.command(name="購買", description="從商店購買指定道具")
    @app_commands.rename(item_name="商品名稱", quantity="購買數量")  # 🌟 控制兩個黑框皆顯示為中文
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
        try:
            # 檢查玩家金幣
            cursor.execute("INSERT OR IGNORE INTO players (user_id, gold) VALUES (?, 0)", (interaction.user.id,))
            conn.commit()

            cursor.execute("SELECT gold FROM players WHERE user_id = ?", (interaction.user.id,))
            player_gold = cursor.fetchone()[0]

            if player_gold < total_cost:
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

            embed = discord.Embed(
                title="🛍️ 【購買成功】",
                description=f"成功購買了 **{item_name}** x `{quantity}`！\n總共花費：`{total_cost} G`",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        finally:
            cursor.close()
            conn.close()

async def setup(bot):
    await bot.add_cog(Shop(bot))
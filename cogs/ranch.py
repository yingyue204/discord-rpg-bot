import time
import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# 牧場動物資料設定
ANIMAL_TYPES = {
    "乳牛": {"cost": 300, "product": "牛奶", "time": 60},    # 60秒收穫一次
    "肉牛": {"cost": 400, "product": "高級肉塊", "time": 90},
    "豬": {"cost": 250, "product": "五花肉", "time": 50},
    "雞": {"cost": 150, "product": "雞蛋", "time": 30}
}

class RanchView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="🐮 查看與收穫牧場", style=discord.ButtonStyle.success)
    async def view_ranch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的牧場！", ephemeral=True)
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT animal_index, animal_type, feed_timestamp, status FROM ranch_animals WHERE user_id = ?", (self.user_id,))
        plots = {row["animal_index"]: dict(row) for row in cursor.fetchall()}
        cursor.close()
        conn.close()

        now = time.time()
        desc = "🌾 **你的私人牧場狀態**（共有 4 個柵欄）：\n\n"
        
        for i in range(1, 5):
            if i in plots:
                p = plots[i]
                aname = p["animal_type"]
                ready_time = p["feed_timestamp"] + ANIMAL_TYPES[aname]["time"]
                
                if now >= ready_time or p["status"] == "ready":
                    desc += f"柵欄 `{i}`: 🐂 **{aname}** ➔ 🟢 **可以收穫了！**\n"
                else:
                    left = int(ready_time - now)
                    desc += f"柵欄 `{i}`: 🐂 **{aname}** ➔ ⏳ 成長中 (剩餘 `{left}s`)\n"
            else:
                desc += f"柵欄 `{i}`: 📭 **(空柵欄 - 可用 `/購買動物` 購入)**\n"

        embed = discord.Embed(title="🏡 【牧場管理中心】", description=desc, color=discord.Color.green())
        embed.set_footer(text="💡 使用下方按鈕進行收穫或返回。")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🌾 收穫所有成熟產物", style=discord.ButtonStyle.primary)
    async def harvest_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的牧場！", ephemeral=True)
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT animal_index, animal_type, feed_timestamp FROM ranch_animals WHERE user_id = ?", (self.user_id,))
        animals = cursor.fetchall()

        now = time.time()
        harvested_items = {}

        for a in animals:
            idx, aname, feed_time = a["animal_index"], a["animal_type"], a["feed_timestamp"]
            req_time = ANIMAL_TYPES[aname]["time"]

            if now >= (feed_time + req_time):
                product = ANIMAL_TYPES[aname]["product"]
                harvested_items[product] = harvested_items.get(product, 0) + 1
                
                # 重置計時器，讓動物進入下一輪生產
                cursor.execute("UPDATE ranch_animals SET feed_timestamp = ? WHERE user_id = ? AND animal_index = ?", (now, self.user_id, idx))

        if not harvested_items:
            conn.close()
            await interaction.response.send_message("⏳ 目前沒有任何動物成熟可以收穫喔！", ephemeral=True)
            return

        # 將收穫物放入背包
        reward_text = ""
        for prod, qty in harvested_items.items():
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, prod))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?", (qty, self.user_id, prod))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)", (self.user_id, prod, qty))
            reward_text += f"- **{prod}** x `{qty}`\n"

        conn.commit()
        cursor.close()
        conn.close()

        await interaction.response.send_message(f"🎉 **收穫成功！** 你從牧場獲得了以下產物：\n{reward_text}", ephemeral=True)

class Ranch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="牧場", description="開啟私人牧場管理中心，查看動物狀態與收穫產物")
    async def ranch(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role_name FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        cursor.close()
        conn.close()

        if not player or not player[0]:
            await interaction.followup.send("⚠️ 請先建立角色才能使用牧場！", ephemeral=True)
            return

        embed = discord.Embed(
            title="🏡 【冒險者牧場】",
            description="歡迎來到牧場！在這裡可以飼養乳牛、肉牛、豬和雞，定時收穫豐富的肉品與副產品。\n\n請點擊下方按鈕查看或收穫：",
            color=discord.Color.from_rgb(222, 184, 135)
        )
        
        view = RanchView(user_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="購買動物", description="在牧場空柵欄中購入並飼養動物")
    @app_commands.describe(柵欄編號="牧場的欄位編號 (1~4)", 動物種類="想購買的動物名稱")
    @app_commands.choices(動物種類=[
        app_commands.Choice(name="乳牛 (產出:牛奶 / 300G)", value="乳牛"),
        app_commands.Choice(name="肉牛 (產出:高級肉塊 / 400G)", value="肉牛"),
        app_commands.Choice(name="豬 (產出:五花肉 / 250G)", value="豬"),
        app_commands.Choice(name="雞 (產出:雞蛋 / 150G)", value="雞")
    ])
    async def buy_animal(self, interaction: discord.Interaction, 柵欄編號: int, 動物種類: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        if 柵欄編號 < 1 or 柵欄編號 > 4:
            await interaction.followup.send("⚠️ 柵欄編號必須介於 1 到 4 之間！", ephemeral=True)
            return

        cost = ANIMAL_TYPES[動物種類]["cost"]

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 檢查玩家與金幣
        cursor.execute("SELECT role_name, gold FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        
        if not player or not player["role_name"]:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 請先建立角色才能使用牧場！", ephemeral=True)
            return

        if player["gold"] < cost:
            cursor.close()
            conn.close()
            await interaction.followup.send(f"❌ 購買 **{動物種類}** 需要 `{cost} G`，你的金幣不足！（目前有 `{player['gold']} G`）", ephemeral=True)
            return

        # 檢查該柵欄是否已有動物
        cursor.execute("SELECT * FROM ranch_animals WHERE user_id = ? AND animal_index = ?", (user_id, 柵欄編號))
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            conn.close()
            await interaction.followup.send(f"⚠️ 柵欄 `{柵欄編號}` 已經有動物在裡面了！", ephemeral=True)
            return

        # 扣除金幣並放入動物
        cursor.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (cost, user_id))
        cursor.execute("""
            INSERT INTO ranch_animals (user_id, animal_index, animal_type, feed_timestamp, status)
            VALUES (?, ?, ?, ?, 'ready')
        """, (user_id, 柵欄編號, 動物種類, time.time()))

        conn.commit()
        cursor.close()
        conn.close()

        await interaction.followup.send(f"✅ 成功花費 `{cost} G` 購入 **{動物種類}** 並安置在第 `{柵欄編號}` 個柵欄！", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ranch(bot))
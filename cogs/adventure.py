import random
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands

class VillageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔍 搜刮物資", style=discord.ButtonStyle.green, custom_id="village_loot")
    async def loot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        
        # 隨機抽選戰利品
        items = ["稀有金屬", "能量核心", "急救包", "普通廢鐵"]
        weights = [10, 20, 30, 40]
        found_item = random.choices(items, weights=weights, k=1)[0]
        
        # 寫入資料庫背包
        conn = sqlite3.connect("rpg_game.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + 1",
            (user_id, found_item)
        )
        conn.commit()
        conn.close()
        
        await interaction.followup.send(f"📦 搜刮成功！你在角落發現了：**【{found_item}】**！", ephemeral=True)

    @discord.ui.button(label="⚔️ 出村打怪", style=discord.ButtonStyle.red, custom_id="village_fight")
    async def fight_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        monster = random.choice(["荒野機械兵", "狂暴突變體", "駭客殘影"])
        damage = random.randint(5, 20)
        gold_reward = random.randint(10, 50)
        
        conn = sqlite3.connect("rpg_game.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (gold_reward, interaction.user.id))
        conn.commit()
        conn.close()
        
        await interaction.followup.send(
            f"⚔️ 你遭遇了野外敵人 **【{monster}】**！經過一番激戰...\n"
            f"💥 你擊敗了敵人，但承受了 {damage} 點傷害。\n"
            f"💰 獲得戰利品懸賞金：**{gold_reward} 金幣**！",
            ephemeral=True
        )

class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(VillageView())

    @app_commands.command(name="新手村", description="進入安全的新手村，選擇搜刮物資或出村打怪！")
    async def village(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        view = VillageView()
        await interaction.followup.send(content="🛡️ **[歡迎來到新手村：艾庇索德 (Episode-0)]**\n請點擊下方按鈕開始你的冒險：", view=view)

async def setup(bot):
    await bot.add_cog(Adventure(bot))
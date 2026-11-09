import time
import asyncio
import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# 🌊 各水域與對應設定
FISHING_SPOTS = {
    "家園小溪": {
        "req_rod": "木製釣竿",
        "stamina": 5,
        "wait_min": 2,
        "wait_max": 4,
        "drops": [
            ("鮮魚", 60),
            ("海帶", 20),
            ("廢鐵罐", 15),
            ("神祕寶箱", 5)
        ]
    },
    "神秘湖泊": {
        "req_rod": "強化金屬釣竿",
        "stamina": 10,
        "wait_min": 3,
        "wait_max": 5,
        "drops": [
            ("鮭魚", 45),
            ("鰻魚", 35),
            ("鮮魚", 15),
            ("神祕寶箱", 5)
        ]
    },
    "深海遺跡": {
        "req_rod": "魔導釣竿",
        "stamina": 20,
        "wait_min": 3,
        "wait_max": 6,
        "drops": [
            ("鮪魚", 40),
            ("河豚", 35),
            ("神祕寶箱", 15),
            ("魔導金屬", 10)
        ]
    }
}

# ⚡ QTE 互動拉竿按鈕介面
class FishPullView(discord.ui.View):
    def __init__(self, user_id, spot_name, caught_item, stamina_cost):
        super().__init__(timeout=3.0)  # 3 秒內沒按就脫鉤逃跑
        self.user_id = user_id
        self.spot_name = spot_name
        self.caught_item = caught_item
        self.stamina_cost = stamina_cost
        self.clicked = False
        self.message = None

    @discord.ui.button(label="⚡ 拉竿 (Pull!)", style=discord.ButtonStyle.danger)
    async def pull_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的釣竿！", ephemeral=True)
            return

        self.clicked = True
        self.stop()

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 1. 扣除體力
            cursor.execute("UPDATE players SET stamina = stamina - ? WHERE user_id = ?", (self.stamina_cost, self.user_id))

            # 2. 發放獎勵
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, self.caught_item))
            inv_row = cursor.fetchone()

            if inv_row:
                cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (self.user_id, self.caught_item))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (self.user_id, self.caught_item))

            # 若釣到廢鐵罐，額外給予隨機金幣
            found_gold = random.randint(2, 6) if self.caught_item == "廢鐵罐" else 0
            if found_gold > 0:
                cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (found_gold, self.user_id))

            conn.commit()

            button.disabled = True
            button.label = "🎉 收線成功！"
            button.style = discord.ButtonStyle.success

            embed = discord.Embed(
                title="🎣 【釣魚成功！】",
                description=f"手速真快！你在 **{self.spot_name}** 成功拉起水下大魚！\n\n🎁 獲得產物：**{self.caught_item}** x `1`",
                color=discord.Color.green()
            )
            if found_gold > 0:
                embed.add_field(name="💰 意外發現", value=f"在廢鐵罐裡找到了 **+{found_gold} G**！", inline=False)

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            conn.rollback()
            await interaction.response.send_message(f"❌ 獎勵發放發生錯誤: `{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

    async def on_timeout(self):
        if not self.clicked:
            for child in self.children:
                child.disabled = True
                child.label = "🐟 魚脫鉤逃跑了..."
                child.style = discord.ButtonStyle.secondary

            embed = discord.Embed(
                title="❌ 【釣魚失敗】",
                description="太慢拉竿了！水下的魚咬走魚餌後溜走了，白白浪費了等待的時間...",
                color=discord.Color.red()
            )
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except:
                    pass

class Fish(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="釣魚", description="選擇水域揮竿釣魚，挑戰 3 秒極速拉竿 QTE！")
    @app_commands.rename(water_spot="水域選擇")
    @app_commands.describe(water_spot="選擇你想前往的釣魚水域")
    @app_commands.choices(water_spot=[
        app_commands.Choice(name="🏞️ 家園小溪 (門檻: 木製釣竿 / 消耗 5 體)", value="家園小溪"),
        app_commands.Choice(name="🌊 神秘湖泊 (門檻: 強化金屬釣竿 / 消耗 10 體)", value="神秘湖泊"),
        app_commands.Choice(name="🏛️ 深海遺跡 (門檻: 魔導釣竿 / 消耗 20 體)", value="深海遺跡")
    ])
    async def fish(self, interaction: discord.Interaction, water_spot: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        spot_info = FISHING_SPOTS[water_spot]
        req_rod = spot_info["req_rod"]
        stamina_cost = spot_info["stamina"]

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 1. 檢查玩家狀態、體力與倒地
            cursor.execute("SELECT hp, stamina, max_stamina FROM players WHERE user_id = ?", (user_id,))
            player = cursor.fetchone()

            if not player:
                await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/setup_roles` 選擇職業。", ephemeral=True)
                return

            hp, stamina, max_stamina = player

            if hp <= 0:
                await interaction.followup.send("❌ 你目前處於倒地狀態，無法進行釣魚！請先前往診所治療。", ephemeral=True)
                return

            if stamina < stamina_cost:
                embed = discord.Embed(
                    title="⚡ 【體力耗盡】",
                    description=f"前往 **{water_spot}** 體力不足！\n當前體力：`{stamina}/{max_stamina}`（需要 `{stamina_cost}` 點）",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # 2. 檢查背包是否有對應釣竿
            cursor.execute("SELECT item_name FROM inventory WHERE user_id = ?", (user_id,))
            user_items = [row["item_name"] for row in cursor.fetchall()]

            if req_rod != "木製釣竿" and req_rod not in user_items:
                await interaction.followup.send(f"⚠️ 前往 **{water_spot}** 需要裝備 **【{req_rod}】**！請先透過商店購買或解鎖。", ephemeral=True)
                return

            # 3. 隨機計算抽獎掉落物
            drops = spot_info["drops"]
            items, weights = zip(*drops)
            caught_item = random.choices(items, weights=weights, k=1)[0]

            # 4. 進入「等待浮標反應」階段
            embed_wait = discord.Embed(
                title=f"🎣 【{water_spot}】靜心垂釣中...",
                description="拋出釣竿，靜靜等待水面的動靜...\n*(請保持專注，浮標下沉時只有 3 秒反應時間！)*",
                color=discord.Color.blue()
            )
            msg = await interaction.followup.send(embed=embed_wait, ephemeral=True)

            # 隨機等待秒數
            wait_time = random.randint(spot_info["wait_min"], spot_info["wait_max"])
            await asyncio.sleep(wait_time)

            # 5. 浮標拉起，跳出 QTE 按鈕
            embed_bite = discord.Embed(
                title="⚡ 【魚咬鉤了！！】",
                description="**浮標急速下沉！水中有大魚上鉤，立刻點擊下方按鈕拉竿！！**",
                color=discord.Color.gold()
            )
            view = FishPullView(user_id, water_spot, caught_item, stamina_cost)
            view.message = msg

            await interaction.edit_original_response(embed=embed_bite, view=view)

        except Exception as e:
            conn.rollback()
            print(f"❌ 釣魚指令發生錯誤: {e}")
            try:
                await interaction.followup.send(f"❌ 釣魚過程發生未預期的錯誤：`{e}`", ephemeral=True)
            except:
                pass
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

async def setup(bot):
    await bot.add_cog(Fish(bot))
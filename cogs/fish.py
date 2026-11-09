import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# 🎣 釣魚區域與魚獲資料設定
FISHING_SPOTS = {
    "新手河畔": {
        "description": "平靜的河岸，適合初學者練習釣魚，偶爾能釣到廢棄物。",
        "stamina": 10,
        "drops": [
            ("小魚", 50),
            ("草魚", 30),
            ("廢鐵罐", 20)
        ]
    },
    "神祕湖泊": {
        "description": "深不見底的湖泊，水質清澈，棲息著較為珍貴的魚類。",
        "stamina": 20,
        "drops": [
            ("草魚", 40),
            ("鮭魚", 35),
            ("黃金鯉魚", 15),
            ("神祕寶箱", 10)
        ]
    },
    "深海漁場": {
        "description": "波濤洶湧的深海，充滿未知與高級漁獲，對體力消耗極大！",
        "stamina": 35,
        "drops": [
            ("鮭魚", 30),
            ("黃金鯉魚", 30),
            ("深海巨魷", 25),
            ("神祕寶箱", 15)
        ]
    }
}

# 🎯 第五人格風格的校準 QTE 互動介面
class FishingCalibrationView(discord.ui.View):
    def __init__(self, user_id, spot_name, caught_item, stamina_cost):
        super().__init__(timeout=3.5)  # 3.5秒內必須點擊
        self.user_id = user_id
        self.spot_name = spot_name
        self.caught_item = caught_item
        self.stamina_cost = stamina_cost
        self.clicked = False
        self.message = None

        # 隨機決定甜蜜點位置 (1 ~ 10)
        self.sweet_spot = random.randint(3, 7)

    @discord.ui.button(label="🎯 釣魚校準 (Calibrate!)", style=discord.ButtonStyle.danger)
    async def calibrate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的釣竿！", ephemeral=True)
            return

        self.clicked = True
        self.stop()

        hit_position = random.randint(1, 10)
        diff = abs(hit_position - self.sweet_spot)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 📦 背包容量檢查
            cursor.execute("SELECT COUNT(*) as slots FROM inventory WHERE user_id = ? AND quantity > 0", (self.user_id,))
            current_slots = cursor.fetchone()["slots"]

            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, self.caught_item))
            inv_row = cursor.fetchone()

            cursor.execute("SELECT max_bag_slots FROM players WHERE user_id = ?", (self.user_id,))
            player_row = cursor.fetchone()
            max_slots = player_row["max_bag_slots"] if player_row and "max_bag_slots" in player_row.keys() and player_row["max_bag_slots"] else 20

            if not inv_row and current_slots >= max_slots:
                button.disabled = True
                button.label = "🎒 背包空間不足"
                button.style = discord.ButtonStyle.secondary
                embed = discord.Embed(
                    title="⚠️ 【背包空間已滿】",
                    description=f"你成功釣起了 **{self.caught_item}**，但隨身背包已滿 (`{current_slots}/{max_slots}` 格)！\n💡 請先使用 `/存入倉庫` 整理背包。",
                    color=discord.Color.orange()
                )
                await interaction.response.edit_message(embed=embed, view=self)
                return

            # 扣除體力
            cursor.execute("UPDATE players SET stamina = stamina - ? WHERE user_id = ?", (self.stamina_cost, self.user_id))

            # 判定成果 (差 0 格為完美 Perfect，給 2 個)
            give_qty = 2 if diff == 0 else 1
            result_title = "🎉 【完美校準！大豐收】" if diff == 0 else "🎣 【校準成功！】"

            if inv_row:
                cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?", (give_qty, self.user_id, self.caught_item))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)", (self.user_id, self.caught_item, give_qty))

            found_gold = random.randint(5, 15) if self.caught_item == "廢鐵罐" else 0
            if found_gold > 0:
                cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (found_gold, self.user_id))

            conn.commit()

            button.disabled = True
            button.label = "✨ 校準成功！"
            button.style = discord.ButtonStyle.success

            bar = ""
            for i in range(1, 11):
                if i == hit_position:
                    bar += "📍"
                elif abs(i - self.sweet_spot) <= 1:
                    bar += "🟩"
                else:
                    bar += "⬛"

            embed = discord.Embed(
                title=result_title,
                description=f"你在 **{self.spot_name}** 進行了精準的拉竿校準！\n\n"
                            f"🎚️ **校準條**：`{bar}`\n"
                            f"🎁 獲得產物：**{self.caught_item}** x `{give_qty}`",
                color=discord.Color.green() if diff == 0 else discord.Color.blue()
            )
            if found_gold > 0:
                embed.add_field(name="💰 意外發現", value=f"在廢鐵罐裡找到了 **+{found_gold} G**！", inline=False)

            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            conn.rollback()
            await interaction.response.send_message(f"❌ 發生錯誤：`{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

    async def on_timeout(self):
        if not self.clicked:
            for child in self.children:
                child.disabled = True
                child.label = "💥 校準失敗 (脫鉤)"
                child.style = discord.ButtonStyle.secondary

            embed = discord.Embed(
                title="❌ 【校準失敗·脫鉤逃跑】",
                description="太可惜了！你在指針通過時來不及按下滑動按鈕，魚咬破魚線逃走了...",
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

    @app_commands.command(name="釣魚", description="前往指定的釣魚場揮竿釣魚")
    @app_commands.rename(spot="釣魚地點")
    @app_commands.choices(spot=[
        app_commands.Choice(name="新手河畔 (消耗 10 體力)", value="新手河畔"),
        app_commands.Choice(name="神祕湖泊 (消耗 20 體力)", value="神祕湖泊"),
        app_commands.Choice(name="深海漁場 (消耗 35 體力)", value="深海漁場")
    ])
    @app_commands.describe(spot="你想前往的釣魚地點")
    async def fish(self, interaction: discord.Interaction, spot: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT hp, stamina, max_stamina FROM players WHERE user_id = ?", (user_id,))
            player = cursor.fetchone()

            if not player:
                await interaction.followup.send("⚠️ 你尚未建立角色！請先使用 `/setup_roles` 選擇職業。", ephemeral=True)
                return

            hp, stamina, max_stamina = player

            if hp <= 0:
                await interaction.followup.send("⚠️ 你目前處於倒地狀態，無法釣魚！請先前往診所治療。", ephemeral=True)
                return

            spot_info = FISHING_SPOTS.get(spot, FISHING_SPOTS["新手河畔"])
            cost = spot_info["stamina"]

            if stamina < cost:
                embed = discord.Embed(
                    title="⚡ 【體力耗盡】",
                    description=f"你的體力不足以支撐這次釣魚！\n當前體力：`{stamina}/{max_stamina}` (需要 `{cost}` 點)\n\n💡 請先食用食物或透過莊園休息來恢復體力！",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # 決定釣到的魚獲
            items, weights = zip(*spot_info["drops"])
            caught_item = random.choices(items, weights=weights, k=1)[0]

            embed = discord.Embed(
                title=f"🎣 【{spot}·魚訊浮現！】",
                description=f"水面傳來陣陣波動，似乎有東西上鉤了！\n\n⚠️ **請在 3.5 秒內點擊下方按鈕進行指針校準！**",
                color=discord.Color.blue()
            )

            view = FishingCalibrationView(user_id, spot, caught_item, cost)
            sent_message = await interaction.followup.send(embed=embed, view=view, wait=True)
            view.message = sent_message

        except Exception as e:
            conn.rollback()
            await interaction.followup.send(f"❌ 釣魚過程發生錯誤：`{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

# 🌟 關鍵：所有 Cog 檔案都必須具備這個 setup 函式，否則會報 NoEntryPointError
async def setup(bot):
    await bot.add_cog(Fish(bot))
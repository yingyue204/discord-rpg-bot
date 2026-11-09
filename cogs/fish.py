import asyncio
import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

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

class IdentityVCalibrationView(discord.ui.View):
    def __init__(self, user_id, spot_name, caught_item, stamina_cost):
        super().__init__(timeout=5.0)  # 總共給 5 秒讓指針晃動
        self.user_id = user_id
        self.spot_name = spot_name
        self.caught_item = caught_item
        self.stamina_cost = stamina_cost
        
        self.is_finished = False
        self.message = None
        
        # 綠色判定區設定（總共 10 格，例如第 4, 5, 6 格是綠色安全區）
        self.green_zones = [4, 5, 6]
        
        # 指針初始位置與移動方向 (1 = 往右, -1 = 往左)
        self.pointer_pos = 1
        self.direction = 1

    def render_bar(self):
        bar = ""
        for i in range(1, 11):
            if i == self.pointer_pos:
                bar += "📍"  # 正在左右晃動的指標
            elif i in self.green_zones:
                bar += "🟩"  # 綠色成功判定區
            else:
                bar += "⬛"
        return f"`[{bar}]`"

    @discord.ui.button(label="🎯 點擊校準！", style=discord.ButtonStyle.danger)
    async def click_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的釣竿！", ephemeral=True)
            return

        if self.is_finished:
            return

        self.is_finished = True
        self.stop()

        # 1. 立即回應 defer，讓 Discord 知道我們正在處理，防止「未及時回應」
        await interaction.response.defer()

        success = self.pointer_pos in self.green_zones

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            for child in self.children:
                child.disabled = True

            # 🛠️ 扣除體力與 1 點魚竿耐久度
            cursor.execute("UPDATE players SET stamina = stamina - ?, rod_durability = rod_durability - 1 WHERE user_id = ?", (self.stamina_cost, self.user_id))

            if not success:
                # 💥 失敗：魚脫鉤
                conn.commit()
                embed = discord.Embed(
                    title="❌ 【校準失敗·魚兒脫鉤】",
                    description=f"指針停在了錯誤的位置（格數 `{self.pointer_pos}`）！你錯過了綠色區域，魚線斷裂，魚逃跑了...\n⚠️ **魚竿耐久度 `-1`**",
                    color=discord.Color.red()
                )
                button.label = "💥 脫鉤失敗"
                button.style = discord.ButtonStyle.secondary
                # 2. 使用 interaction.followup.edit_message 完美更新延遲回應後的訊息
                await interaction.edit_original_response(embed=embed, view=self)
                return

            # 📦 背包容量檢查
            cursor.execute("SELECT COUNT(*) as slots FROM inventory WHERE user_id = ? AND quantity > 0", (self.user_id,))
            current_slots = cursor.fetchone()["slots"]

            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, self.caught_item))
            inv_row = cursor.fetchone()

            cursor.execute("SELECT max_bag_slots FROM players WHERE user_id = ?", (self.user_id,))
            player_row = cursor.fetchone()
            max_slots = player_row["max_bag_slots"] if player_row and "max_bag_slots" in player_row.keys() and player_row["max_bag_slots"] else 20

            if not inv_row and current_slots >= max_slots:
                conn.commit()  # 雖然背包滿沒拿到魚，但耐久跟體力照常扣除
                embed = discord.Embed(
                    title="⚠️ 【背包空間已滿】",
                    description=f"你成功釣起了 **{self.caught_item}**，但隨身背包已滿 (`{current_slots}/{max_slots}` 格)，魚又被放回水裡了！\n💡 請先使用 `/存入倉庫` 整理背包。",
                    color=discord.Color.orange()
                )
                button.label = "🎒 背包滿"
                await interaction.edit_original_response(embed=embed, view=self)
                return

            # 發放獎勵
            give_qty = 1
            if inv_row:
                cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?", (give_qty, self.user_id, self.caught_item))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (self.user_id, self.caught_item))

            found_gold = random.randint(5, 15) if self.caught_item == "廢鐵罐" else 0
            if found_gold > 0:
                cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (found_gold, self.user_id))

            conn.commit()

            button.label = "✨ 校準成功！"
            button.style = discord.ButtonStyle.success

            embed = discord.Embed(
                title="🎉 【校準成功！釣魚成功】",
                description=f"你在綠色判定區精準按下了按鈕！成功從 **{self.spot_name}** 釣起了寶貝。\n\n"
                            f"🎚️ **最終指針位置**：{self.render_bar()}\n"
                            f"🎁 獲得產物：**{self.caught_item}** x `{give_qty}`\n"
                            f"🛠️ **魚竿耐久度 `-1`**",
                color=discord.Color.green()
            )
            if found_gold > 0:
                embed.add_field(name="💰 意外發現", value=f"在廢鐵罐裡找到了 **+{found_gold} G**！", inline=False)

            await interaction.edit_original_response(embed=embed, view=self)

        except Exception as e:
            conn.rollback()
            try:
                await interaction.followup.send(f"❌ 發生錯誤：`{e}`", ephemeral=True)
            except:
                pass
        finally:
            cursor.close()
            conn.close()

async def setup(bot):
    await bot.add_cog(Fish(bot))
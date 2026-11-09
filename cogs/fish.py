import asyncio
import random
import discord
from discord.ext import commands
from db import get_db_connection

class FishingCalibrationView(discord.ui.View):
    def __init__(self, user_id, spot_name, caught_item, stamina_cost):
        super().__init__(timeout=3.5)  # 3.5秒內必須完成校準
        self.user_id = user_id
        self.spot_name = spot_name
        self.caught_item = caught_item
        self.stamina_cost = stamina_cost
        self.clicked = False
        self.message = None

        # 隨機決定這次校準的「完美區間」位置 (例如總共 10 格，第 4~6 格是甜蜜點)
        self.sweet_spot = random.randint(3, 7)

    @discord.ui.button(label="🎯 釣魚校準 (Calibrate!)", style=discord.ButtonStyle.danger)
    async def calibrate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的釣竿！", ephemeral=True)
            return

        self.clicked = True
        self.stop()

        # 模擬第五人格的指針隨機停在某個位置 (1 ~ 10)
        hit_position = random.randint(1, 10)
        
        # 判定結果：如果停在 sweet_spot 附近 ±1 格算 Perfect，否則算 Good，差太多算失敗
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

            # 根據判定給予獎勵數量（Perfect 給 2 個，Good 給 1 個）
            give_qty = 2 if diff == 0 else 1
            result_title = "🎉 【完美校準！大豐收】" if diff == 0 else "🎣 【校準成功！】"

            if inv_row:
                cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?", (give_qty, self.user_id, self.caught_item))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)", (self.user_id, self.caught_item, give_qty))

            found_gold = random.randint(3, 8) if self.caught_item == "廢鐵罐" else 0
            if found_gold > 0:
                cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (found_gold, self.user_id))

            conn.commit()

            button.disabled = True
            button.label = "✨ 校準成功！"
            button.style = discord.ButtonStyle.success

            # 畫出視覺化進度條給玩家看指針位置
            bar = ""
            for i in range(1, 11):
                if i == hit_position:
                    bar += "📍"  # 玩家按下的指針
                elif abs(i - self.sweet_spot) <= 1:
                    bar += "🟩"  # 安全判定區
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
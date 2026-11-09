import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from db import get_db_connection

# 🏡 莊園升級配方與等級設定
MANOR_LEVELS = {
    1: {"name": "破舊小木屋", "cost_gold": 0, "cost_mat": "小麥", "cost_qty": 0, "desc": "最樸素的庇護所，僅有簡單的床鋪與一小塊土地。"},
    2: {"name": "溫馨田園小屋", "cost_gold": 1000, "cost_mat": "鐵塊", "cost_qty": 3, "desc": "擴建了廚房與客廳，體力恢復速度提升，休息時能感受到家的溫暖。"},
    3: {"name": "豪華鄉村莊園", "cost_gold": 3000, "cost_mat": "魔導金屬", "cost_qty": 2, "desc": "擁有寬敞的寵物庭院與大倉庫，生活機能完善。"},
    4: {"name": "王國皇家城堡", "cost_gold": 10000, "cost_mat": "魔導金屬", "cost_qty": 10, "desc": "尊貴的象徵，享有每日王國補助與極致的休憩體驗。"}
}

class Manor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 💡 確保玩家擁有莊園資料的輔助函式
    def get_or_create_manor(self, cursor, user_id):
        cursor.execute("SELECT * FROM manors WHERE user_id = ?", (user_id,))
        manor = cursor.fetchone()
        if not manor:
            # 初始化時給予一個已經超過 4 小時冷卻的時間，確保初次可以使用
            initial_time = (datetime.now() - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO manors (user_id, manor_lvl, room_unlocked, last_harvest) VALUES (?, 1, '基礎臥室', ?)", 
                           (user_id, initial_time))
            cursor.execute("SELECT * FROM manors WHERE user_id = ?", (user_id,))
            manor = cursor.fetchone()
        return manor

    @app_commands.command(name="我的莊園", description="檢視你的個人莊園狀態、等級與設施")
    async def view_manor(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            manor = self.get_or_create_manor(cursor, user_id)
            lvl = manor["manor_lvl"]
            info = MANOR_LEVELS[lvl]

            embed = discord.Embed(
                title=f"🏠 【{interaction.user.name} 的個人莊園】",
                description=f"歡迎回到屬於你的避風港。\n\n"
                            f"📌 **莊園階級**：`Lv.{lvl} - {info['name']}`\n"
                            f"📜 **建築特色**：{info['desc']}\n"
                            f"🛏️ **已解鎖設施**：{manor['room_unlocked']}\n\n"
                            f"💡 **可用指令**：\n"
                            f"• `/莊園休息` - 在臥室休息恢復體力\n"
                            f"• `/莊園收成` - 定期領取莊園的被動產出\n"
                            f"• `/擴建莊園` - 提升莊園等級與解鎖更多功能",
                color=discord.Color.from_rgb(139, 69, 19)
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ 查詢莊園失敗：`{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

    @app_commands.command(name="莊園休息", description="在莊園臥室裡好好休息，恢復體力與生命值")
    async def rest_manor(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT hp, max_hp, stamina, max_stamina FROM players WHERE user_id = ?", (user_id,))
            player = cursor.fetchone()
            if not player:
                await interaction.followup.send("⚠️ 你尚未建立角色！", ephemeral=True)
                return

            hp, max_hp, stamina, max_stamina = player
            
            if stamina >= max_stamina and hp >= max_hp:
                await interaction.followup.send("💤 你現在精神飽滿，不需要特別休息！", ephemeral=True)
                return

            new_stamina = max_stamina
            new_hp = min(max_hp, hp + 30)
            cursor.execute("UPDATE players SET stamina = ?, hp = ? WHERE user_id = ?", (new_stamina, new_hp, user_id))
            conn.commit()

            embed = discord.Embed(
                title="🛏️ 【莊園休憩時刻】",
                description=f"你在舒適的床鋪上沉沉睡去，享受了一段寧靜的時光。\n\n"
                            f"✨ **恢復成果**：\n"
                            f"• 體力：`{stamina}` ➔ **`{new_stamina}/{max_stamina}`** (完全恢復)\n"
                            f"• 生命值：`{hp}` ➔ **`{new_hp}/{max_hp}`** (+30 HP)",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            conn.rollback()
            await interaction.followup.send(f"❌ 休息過程發生錯誤：`{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

    @app_commands.command(name="莊園收成", description="巡視莊園並領取定時產出的隨機資源與金幣")
    async def harvest_manor(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            manor = self.get_or_create_manor(cursor, user_id)
            last_harvest_str = manor["last_harvest"]
            
            if "." in last_harvest_str:
                last_harvest_str = last_harvest_str.split(".")[0]

            try:
                last_time = datetime.strptime(last_harvest_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # 萬一格式崩潰，直接強制給予過期時間以防萬一
                last_time = datetime.now() - timedelta(hours=5)

            now = datetime.now()
            cooldown = timedelta(hours=4)

            # 🛡️ 關鍵除錯防護：如果時間差異常（例如被卡死在未來、或是時間戳異常損壞），強制自動重置為可收成狀態！
            if last_time > now or (now - last_time).days > 30:
                last_time = now - timedelta(hours=5)

            if now - last_time < cooldown:
                remaining = cooldown - (now - last_time)
                hrs, rem_sec = divmod(int(remaining.total_seconds()), 3600)
                mins = rem_sec // 60
                await interaction.followup.send(f"⏳ 你的莊園還在生產中！還需要等待 **{hrs} 小時 {mins} 分鐘** 才能再次收成。", ephemeral=True)
                return

            # 根據莊園等級給予隨機獎勵
            lvl = manor["manor_lvl"]
            import random
            gold_reward = random.randint(50 * lvl, 150 * lvl)
            material_pool = ["小麥", "番茄", "高麗菜", "胡蘿蔔", "蘋果", "鮮魚"]
            reward_mat = random.choice(material_pool)
            reward_qty = random.randint(1, 2 * lvl)

            # 📦 背包容量檢查 (預設 20 格種類上限)
            cursor.execute("SELECT COUNT(*) as slots FROM inventory WHERE user_id = ? AND quantity > 0", (user_id,))
            current_slots = cursor.fetchone()["slots"]

            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, reward_mat))
            inv = cursor.fetchone()

            cursor.execute("SELECT max_bag_slots FROM players WHERE user_id = ?", (user_id,))
            player_row = cursor.fetchone()
            max_slots = player_row["max_bag_slots"] if player_row and "max_bag_slots" in player_row.keys() and player_row["max_bag_slots"] else 20

            if not inv and current_slots >= max_slots:
                await interaction.followup.send(f"⚠️ 你的隨身背包已滿 (`{current_slots}/{max_slots}` 格)，無法放下莊園產出的新物資【{reward_mat}】！\n💡 請先使用 `/存入倉庫` 整理背包。", ephemeral=True)
                return

            # 🌟 確實更新上次收成時間為「現在」
            new_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE manors SET last_harvest = ? WHERE user_id = ?", (new_time_str, user_id))
            
            # 給予金幣
            cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (gold_reward, user_id))

            # 給予背包道具
            if inv:
                cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?", (reward_qty, user_id, reward_mat))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)", (user_id, reward_mat, reward_qty))

            conn.commit()

            embed = discord.Embed(
                title="🌾 【莊園巡視與收成】",
                description=f"你迎著清晨的微風巡視莊園，管家呈上了這段期間的收穫與收益：\n\n"
                            f"💰 獲得金幣：**+{gold_reward} G**\n"
                            f"📦 獲得物資：**{reward_mat}** x `{reward_qty}`",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            conn.rollback()
            await interaction.followup.send(f"❌ 收成過程發生錯誤：`{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

    @app_commands.command(name="擴建莊園", description="消耗金幣與指定材料，將莊園升級到下一個階級")
    async def upgrade_manor(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            manor = self.get_or_create_manor(cursor, user_id)
            current_lvl = manor["manor_lvl"]
            next_lvl = current_lvl + 1

            if next_lvl > 4:
                await interaction.followup.send("🎉 你的莊園已經達到最高等級（王國皇家城堡），無須再擴建！", ephemeral=True)
                return

            req = MANOR_LEVELS[next_lvl]
            cost_gold = req["cost_gold"]
            cost_mat = req["cost_mat"]
            cost_qty = req["cost_qty"]

            cursor.execute("SELECT gold FROM players WHERE user_id = ?", (user_id,))
            player = cursor.fetchone()
            if not player or player["gold"] < cost_gold:
                await interaction.followup.send(f"❌ 金幣不足！擴建至 **{req['name']}** 需要 `{cost_gold} G`。", ephemeral=True)
                return

            user_mat_qty = 0
            if cost_qty > 0:
                cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, cost_mat))
                inv = cursor.fetchone()
                user_mat_qty = inv["quantity"] if inv else 0
                if user_mat_qty < cost_qty:
                    await interaction.followup.send(f"❌ 材料不足！擴建需要 **{cost_mat}** x `{cost_qty}`（你目前有 `{user_mat_qty} 個`）。", ephemeral=True)
                    return

            cursor.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (cost_gold, user_id))
            if cost_qty > 0:
                cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?", (cost_qty, user_id, cost_mat))

            new_room_desc = f"基礎臥室、豪華客廳與專屬庭院 (Lv.{next_lvl})"
            cursor.execute("UPDATE manors SET manor_lvl = ?, room_unlocked = ? WHERE user_id = ?", (next_lvl, new_room_desc, user_id))
            conn.commit()

            embed = discord.Embed(
                title="🏰 【莊園擴建成功！】",
                description=f"經過一番大興土木，你的莊園成功升級為 **`{req['name']}`**！\n\n"
                            f"✨ **全新氣象**：{req['desc']}\n"
                            f"📈 產出效率與休憩效果已同步提升！",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            conn.rollback()
            await interaction.followup.send(f"❌ 擴建過程發生錯誤：`{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

async def setup(bot):
    await bot.add_cog(Manor(bot))
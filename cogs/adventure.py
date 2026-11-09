import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="冒險", description="前往未知區域進行快速冒險與搜刮（隨機遭遇突發怪物與寶箱）")
    async def adventure(self, interaction: discord.Interaction):
        # 務必第一步 defer，防止 Discord 逾時
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 1. 從資料庫取得玩家的當前血量與體力
            cursor.execute("SELECT hp, max_hp, stamina, max_stamina FROM players WHERE user_id = ?", (user_id,))
            player_data = cursor.fetchone()

            if not player_data:
                await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/setup_roles` 選擇職業。", ephemeral=True)
                return

            hp, max_hp, stamina, max_stamina = player_data

            # 2. 🏥 檢查玩家是否處於血量歸零／倒地狀態（直接送診所）
            if hp <= 0:
                new_hp = 50  # 診所急救恢復的血量
                cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
                conn.commit()

                embed = discord.Embed(
                    title="🏥 【新手村診所·緊急送醫】",
                    description=f"你目前處於倒地狀態，無法進行冒險！已被緊急送往新手村診所治療。\n💖 當前血量已恢復至：`{new_hp}` / `{max_hp}`",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # 3. ⚡ 檢查體力是否足夠（每次探索消耗 15 點體力）
            stamina_cost = 15
            if stamina < stamina_cost:
                embed = discord.Embed(
                    title="⚡ 【體力耗盡】",
                    description=f"你的體力不足以支撐這次探索！\n當前體力：`{stamina}/{max_stamina}` (需要 `{stamina_cost}` 點)\n\n💡 請食用食物或透過莊園休息來恢復體力，才能繼續冒險！",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # ⚔️ 25% 機率在冒險途中突發遭遇野生怪物伏擊！
            encounter_ambush = random.random() < 0.25
            if encounter_ambush:
                # 扣除體力
                new_stamina = stamina - stamina_cost
                cursor.execute("UPDATE players SET stamina = ? WHERE user_id = ?", (new_stamina, user_id))
                conn.commit()

                # 提前關閉連線，避免在跳轉戰鬥模組時佔用資料庫
                cursor.close()
                conn.close()

                from cogs.battle import BattleChoiceView

                monster_names = ["廢土伏擊者", "迷路防禦機械", "暴走掠奪者"]
                monster_name = random.choice(monster_names)
                monster_hp = random.randint(30, 60)
                monster_atk = random.randint(6, 16)

                embed = discord.Embed(
                    title="⚡ 【冒險突發狀況！遭遇敵人伏擊！】",
                    description="你在搜刮廢墟時不小心驚動了潛伏的怪物，必須立刻做出反應！",
                    color=discord.Color.red()
                )
                embed.add_field(name="🤖 突發怪物", value=f"**{monster_name}**", inline=True)
                embed.add_field(name="❤️ 血量", value=f"`{monster_hp}` HP", inline=True)
                embed.add_field(name="⚔️ 攻擊力", value=f"`{monster_atk}` ATK", inline=True)
                embed.set_footer(text="💡 擊敗突發敵人有更高的寶箱掉落機會！60秒未操作將自動過期。")

                view = BattleChoiceView(user_id, monster_name, monster_hp, monster_atk)
                sent_message = await interaction.followup.send(embed=embed, view=view, ephemeral=True, wait=True)
                view.message = sent_message
                return

            # 🎒 平安搜刮邏輯與掉落物決定
            got_chest = random.random() < 0.1
            found_item = "神秘寶箱" if got_chest else random.choice(["生命藥水", "急救包", "鐵劍碎片"])

            # 📦 背包容量檢查 (預設 20 格種類上限)
            cursor.execute("SELECT COUNT(*) as slots FROM inventory WHERE user_id = ? AND quantity > 0", (user_id,))
            current_slots = cursor.fetchone()["slots"]

            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, found_item))
            item_row = cursor.fetchone()

            cursor.execute("SELECT max_bag_slots FROM players WHERE user_id = ?", (user_id,))
            player_row = cursor.fetchone()
            max_slots = player_row["max_bag_slots"] if player_row and "max_bag_slots" in player_row.keys() and player_row["max_bag_slots"] else 20

            # 若背包已滿且獲得的是新道具種類，則提示玩家
            if not item_row and current_slots >= max_slots:
                embed = discord.Embed(
                    title="⚠️ 【背包空間已滿】",
                    description=f"你在廢墟中找到了戰利品【{found_item}】，但你的隨身背包已滿 (`{current_slots}/{max_slots}` 格)，無法再放下新種類的道具！\n\n💡 請先前往 `/存入倉庫` 整理背包後再出發冒險。",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # 4. 扣除體力與發放獎勵
            new_stamina = stamina - stamina_cost
            cursor.execute("UPDATE players SET stamina = ? WHERE user_id = ?", (new_stamina, user_id))

            if item_row:
                cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, found_item))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, found_item))

            found_gold = random.randint(5, 15)
            cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (found_gold, user_id))
            conn.commit()

            embed = discord.Embed(
                title="🛡️ 【冒險搜刮成功】", 
                description=f"你成功探索了這片區域並安全返回！ (體力: `{new_stamina}/{max_stamina}`)",
                color=discord.Color.green()
            )
            if got_chest:
                embed.add_field(name="🎁 驚喜發現", value="**✨ 神秘寶箱 x 1**（極低機率幸運獲得！）", inline=True)
            else:
                embed.add_field(name="📦 獲得道具", value=f"**{found_item}** x `1`", inline=True)

            embed.add_field(name="💰 獲得金幣", value=f"**+{found_gold} G**", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            conn.rollback()
            await interaction.followup.send(f"❌ 冒險過程發生錯誤：`{e}`", ephemeral=True)
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

# 🌟 必須具備 setup 函式以供機器人載入 Cog
async def setup(bot):
    await bot.add_cog(Adventure(bot))
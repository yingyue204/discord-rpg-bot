import random
import traceback
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class BattleChoiceView(discord.ui.View):
    def __init__(self, user_id, monster_name, monster_hp, monster_atk):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.monster_name = monster_name
        self.monster_hp = monster_hp
        self.monster_atk = monster_atk

    @discord.ui.button(label="⚔️ 普通攻擊", style=discord.ButtonStyle.primary)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的戰鬥！", ephemeral=True)
            return
        await self.process_turn(interaction, action="attack")

    @discord.ui.button(label="⚡ 技能攻擊 (耗 15 MP)", style=discord.ButtonStyle.success)
    async def skill_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的戰鬥！", ephemeral=True)
            return
        await self.process_turn(interaction, action="skill")

    @discord.ui.button(label="🏃 逃跑", style=discord.ButtonStyle.danger)
    async def flee_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的戰鬥！", ephemeral=True)
            return
        
        await interaction.response.defer()
        for child in self.children:
            child.disabled = True
        
        embed = discord.Embed(
            title="🏃 【戰鬥逃跑】",
            description=f"你迅速撤退，成功從 **{self.monster_name}** 面前逃脫了！",
            color=discord.Color.orange()
        )
        await interaction.edit_original_response(embed=embed, view=self)
        self.stop()

    async def process_turn(self, interaction: discord.Interaction, action: str):
        # 🛡️ 第一時間宣告 defer，絕對不讓 Discord 3秒逾時
        await interaction.response.defer()

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 確保資料庫有這些欄位，避免抓取崩潰
            cursor.execute("""
                SELECT hp, max_hp, atk, def, weapon_atk, armor_def, level, exp, mp,
                       COALESCE(weapon_durability, 50) as w_dur, 
                       COALESCE(armor_durability, 50) as a_dur 
                FROM players WHERE user_id = ?
            """, (self.user_id,))
            player = cursor.fetchone()
            if not player:
                await interaction.followup.send("⚠️ 找不到你的角色資料！", ephemeral=True)
                return

            hp, max_hp, base_atk, base_def, weapon_atk, armor_def, level, exp, current_mp, w_dur, a_dur = player
            total_atk = base_atk + (weapon_atk or 0)
            total_def = base_def + (armor_def or 0)

            real_atk = total_atk if w_dur > 0 else max(1, int(total_atk * 0.3))
            real_def = total_def if a_dur > 0 else int(total_def * 0.3)

            # 1. 玩家攻擊回合
            if action == "attack":
                player_dmg = max(5, real_atk - random.randint(0, 5))
                action_desc = f"你對 **{self.monster_name}** 發動普通攻擊，造成了 `{player_dmg}` 點傷害！"
            
            elif action == "skill":
                if (current_mp or 0) < 15:
                    await interaction.followup.send("❌ 你的魔力值 (MP) 不足 15 點！", ephemeral=True)
                    return

                cursor.execute("UPDATE players SET mp = mp - 15 WHERE user_id = ?", (self.user_id,))
                conn.commit()
            
                player_dmg = max(12, int(real_atk * 1.5) - random.randint(0, 3))
                action_desc = f"你消耗 15 MP 施放強力技能，對 **{self.monster_name}** 造成了 `{player_dmg}` 點重創！"

            self.monster_hp -= player_dmg

            # 消耗 1 點武器耐久
            new_w_dur = max(0, w_dur - 1)
            cursor.execute("UPDATE players SET weapon_durability = ? WHERE user_id = ?", (new_w_dur, self.user_id))

            # 2. 檢查怪物是否死亡（戰鬥勝利）
            if self.monster_hp <= 0:
                gold_reward = random.randint(15, 30)
                dropped_item = random.choice(["生命藥水", "鐵劍碎片", "魔力藥水"]) if random.random() < 0.4 else None
            
                cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (gold_reward, self.user_id))
            
                exp += 80
                next_level_exp = level * 100
                level_up_msg = ""
                while exp >= next_level_exp:
                    exp -= next_level_exp
                    level += 1
                    next_level_exp = level * 100
                    level_up_msg += f"\n🎉 **等級提升！** 恭喜升到 **Lv.{level}**（生命上限與攻擊力提升！）"
                    cursor.execute("""
                        UPDATE players 
                        SET level = ?, exp = ?, max_hp = max_hp + 20, hp = max_hp + 20, atk = atk + 3 
                        WHERE user_id = ?
                    """, (level, exp, self.user_id))

                if not level_up_msg:
                    cursor.execute("UPDATE players SET exp = ? WHERE user_id = ?", (exp, self.user_id))

                reward_text = f"💰 獲得金幣：`+{gold_reward} G`\n✨ 獲得經驗：`+80 EXP`{level_up_msg}"

                if dropped_item:
                    cursor.execute("SELECT COUNT(*) as slots FROM inventory WHERE user_id = ? AND quantity > 0", (self.user_id,))
                    current_slots = cursor.fetchone()["slots"]

                    cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, dropped_item))
                    row = cursor.fetchone()

                    cursor.execute("SELECT max_bag_slots FROM players WHERE user_id = ?", (self.user_id,))
                    player_row = cursor.fetchone()
                    max_slots = player_row["max_bag_slots"] if player_row and "max_bag_slots" in player_row.keys() and player_row["max_bag_slots"] else 20

                    if not row and current_slots >= max_slots:
                        reward_text += f"\n⚠️ **戰利品掉落【{dropped_item}】，但隨身背包已滿 (`{current_slots}/{max_slots}`)，不小心遺失在荒野中！**"
                    else:
                        if row:
                            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (self.user_id, dropped_item))
                        else:
                            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (self.user_id, dropped_item))
                        reward_text += f"\n🎁 獲得戰利品：**{dropped_item}** x `1`"

                conn.commit()

                for child in self.children:
                    child.disabled = True

                embed = discord.Embed(
                    title=f"⚔️ 【戰鬥勝利！成功擊敗 {self.monster_name}】",
                    description=f"{action_desc}\n\n{reward_text}\n\n🛠️ **戰後武器耐久**：`{new_w_dur}/50`",
                    color=discord.Color.green()
                )
                if new_w_dur == 0:
                    embed.add_field(name="⚠️ 裝備警告", value="你的武器已經破損，攻擊力大幅下降！請盡快前往鐵匠鋪修復。", inline=False)

                await interaction.edit_original_response(embed=embed, view=self)
                self.stop()
                return

            # 3. 怪物反擊回合
            monster_dmg = max(1, self.monster_atk - int(real_def * 0.4))
            hp = max(0, hp - monster_dmg)
            
            new_a_dur = max(0, a_dur - 1)
            cursor.execute("UPDATE players SET hp = ?, armor_durability = ? WHERE user_id = ?", (hp, new_a_dur, self.user_id))
            conn.commit()

            # 4. 檢查玩家是否倒地
            if hp <= 0:
                new_hp = 50 
                cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, self.user_id))
                conn.commit()

                for child in self.children:
                    child.disabled = True

                embed = discord.Embed(
                    title="🏥 【新手村診所·緊急送醫】",
                    description=f"**{self.monster_name}** 反擊造成了 `{monster_dmg}` 點傷害。\n你體力不支倒地，已被緊急送往新手村診所治療！\n💖 當前血量已恢復至：`{new_hp}`",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=embed, view=self)
                self.stop()
                return

            # 5. 更新戰鬥面板（繼續下一回合）
            turn_desc = f"{action_desc}\n💥 **{self.monster_name}** 反擊造成了 `{monster_dmg}` 點傷害！"
            if new_w_dur == 0:
                turn_desc += "\n⚠️ *你的武器已破損！*"
            if new_a_dur == 0:
                turn_desc += "\n⚠️ *你的防具已破裂！*"

            embed = discord.Embed(
                title="⚔️ 【回合戰鬥進行中】",
                description=turn_desc,
                color=discord.Color.gold()
            )
            embed.add_field(name="🤖 怪物狀態", value=f"**{self.monster_name}**\n❤️ 剩餘血量：`{self.monster_hp}` HP", inline=True)
            embed.add_field(name="🛡️ 你的狀態", value=f"❤️ 血量：`{hp}/{max_hp}`\n🛠️ 武器耐久：`{new_w_dur}/50`\n🛡️ 防具耐久：`{new_a_dur}/50`", inline=True)
            embed.set_footer(text="💡 60秒未操作將自動過期。")

            await interaction.edit_original_response(embed=embed, view=self)

        except Exception as e:
            traceback.print_exc()
            conn.rollback()
            try:
                await interaction.followup.send(f"❌ 戰鬥發生錯誤：`{e}`", ephemeral=True)
            except:
                pass
        finally:
            cursor.close()
            conn.close()

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="打怪", description="在荒野中尋找野生怪物進行主動戰鬥")
    async def battle(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role_name, hp, max_hp, COALESCE(weapon_durability, 50), COALESCE(armor_durability, 50) FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        cursor.close()
        conn.close()

        if not player or not player[0]:
            await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/setup_roles` 選擇職業。", ephemeral=True)
            return

        if player[1] <= 0:
            await interaction.followup.send("⚠️ 你目前處於倒地狀態，無法進行戰鬥！請先透過冒險或診所恢復。", ephemeral=True)
            return

        monster_names = ["荒野流民", "廢土狂徒", "失控機械兵", "暴走掠奪者"]
        monster_name = random.choice(monster_names)
        monster_hp = random.randint(45, 75)
        monster_atk = random.randint(10, 22)

        w_dur, a_dur = player[3], player[4]

        embed = discord.Embed(
            title="⚔️ 【遭遇野生怪物！】",
            description="你在荒野中鎖定了一隻目標，準備迎戰！",
            color=discord.Color.orange()
        )
        embed.add_field(name="🤖 目標怪物", value=f"**{monster_name}**", inline=True)
        embed.add_field(name="❤️ 血量", value=f"`{monster_hp}` HP", inline=True)
        embed.add_field(name="⚔️ 攻擊力", value=f"`{monster_atk}` ATK", inline=True)
        embed.add_field(name="🛠️ 當前裝備狀況", value=f"武器耐久: `{w_dur}/50`\n防具耐久: `{a_dur}/50`", inline=False)
        embed.set_footer(text="💡 60秒未操作將自動過期。")

        view = BattleChoiceView(user_id, monster_name, monster_hp, monster_atk)
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Battle(bot))
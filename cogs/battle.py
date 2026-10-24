import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection, update_and_get_mp, consume_mp

MP_COST_PER_BATTLE = 10  # 每次打怪消耗 10 點 MP

class BattleChoiceView(discord.ui.View):
    def __init__(self, user_id, monster_name, monster_hp, monster_atk, is_adventure_ambush=False):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.monster_name = monster_name
        self.monster_hp = monster_hp
        self.monster_atk = monster_atk
        self.is_adventure_ambush = is_adventure_ambush

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的戰鬥遭遇！", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="發動攻擊", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if not self.is_adventure_ambush:
            current_mp, max_mp = update_and_get_mp(self.user_id)
            if current_mp < MP_COST_PER_BATTLE:
                await interaction.followup.send("❌ 你的 MP 不足，無法發動攻擊！", ephemeral=True)
                return
            consume_mp(self.user_id, MP_COST_PER_BATTLE)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hp, max_hp, atk, def, weapon_atk, armor_net, gold 
            FROM players WHERE user_id = ?
        """, (self.user_id,))
        # 修正欄位抓取對應
        cursor.execute("""
            SELECT hp, max_hp, atk, def, weapon_atk, armor_def, gold 
            FROM players WHERE user_id = ?
        """, (self.user_id,))
        player = cursor.fetchone()
        
        hp, max_hp, base_atk, base_def, weapon_atk, armor_def, gold = player

        # ⚔️ 計算總攻擊力與總防禦力（基礎數值 + 裝備加成）
        total_atk = base_atk + weapon_atk
        total_def = base_def + armor_def

        m_hp = self.monster_hp
        turns = 0
        total_damage_taken = 0

        while m_hp > 0 and hp > 0 and turns < 10:
            turns += 1
            # 玩家攻擊力套用總 ATK
            damage_to_monster = max(1, total_atk + random.randint(-2, 3))
            m_hp -= damage_to_monster

            if m_hp <= 0:
                break

            # 🛡️ 怪物攻擊力套用防禦力減傷：damage = 怪物攻擊力 - 玩家總防禦力（保險起見最低扣 1 血）
            net_monster_damage = self.monster_atk - total_def
            damage_to_player = max(1, net_monster_damage + random.randint(-1, 2))
            
            hp -= damage_to_player
            total_damage_taken += damage_to_player

        hp = max(0, hp)

        if hp > 0:
            reward_gold = random.randint(20, 40) if self.is_adventure_ambush else random.randint(15, 35)
            
            chest_chance = 0.50 if self.is_adventure_ambush else 0.30
            got_chest = random.random() < chest_chance
            
            if got_chest:
                cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = '神秘寶箱'", (self.user_id,))
                if cursor.fetchone():
                    cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = '神秘寶箱'", (self.user_id,))
                else:
                    cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, '神秘寶箱', 1)", (self.user_id,))

            cursor.execute("UPDATE players SET hp = ?, gold = gold + ? WHERE user_id = ?", (hp, gold + reward_gold, self.user_id))
            conn.commit()
            cursor.close()
            conn.close()

            embed = discord.Embed(title="🎉 【戰鬥勝利！】", color=discord.Color.green())
            desc = (
                f"你成功擊敗了 🤖 **{self.monster_name}**（歷時 `{turns}` 回合）！\n\n"
                f"⚔️ **總攻擊力**：`{total_atk}` | 🛡️ **總防禦力**：`{total_def}`\n"
                f"⚔️ **戰鬥結算**：承受了 `{total_damage_taken}` 點傷害（剩餘血量：`{hp}/{max_hp}`）\n"
                f"💰 **獲得獎勵**：`+{reward_gold} G`"
            )
            if got_chest:
                desc += "\n🎁 **額外戰利品**：獲得了 **✨ 神秘寶箱 x 1**！"
            
            embed.description = desc
            self.stop()
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            recovered_hp = min(max_hp, 50)
            cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (recovered_hp, self.user_id))
            conn.commit()
            cursor.close()
            conn.close()

            embed = discord.Embed(title="🏥💥 【戰鬥失敗 · 倒地送醫】", color=discord.Color.blue())
            embed.description = (
                f"你在與 🤖 **{self.monster_name}** 激戰後不敵倒地！\n"
                f"緊急被抬進了**新手村診所**進行治療... 🩺\n\n"
                f"❤️ **當前血量已恢復至**：`{recovered_hp}/{max_hp}`"
            )
            self.stop()
            await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="嘗試逃跑", style=discord.ButtonStyle.secondary, emoji="🏃")
    async def run_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = discord.Embed(
            title="🏃 【安全撤退】",
            description=f"你成功甩開了 🤖 **{self.monster_name}**，平安脫離戰場！",
            color=discord.Color.gold()
        )
        self.stop()
        await interaction.edit_original_response(embed=embed, view=None)

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="打怪", description="發動戰鬥遭遇野生怪物，透過武器與防禦力迎戰")
    async def fight(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id

        current_mp, max_mp = update_and_get_mp(user_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role, hp, max_hp FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()

        if not player or not player[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/setup_roles` 選擇職業。", ephemeral=True)
            return

        role, hp, max_hp = player

        if hp <= 0:
            new_hp = min(max_hp, 50)
            cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
            conn.commit()
            cursor.close()
            conn.close()
            embed = discord.Embed(title="🏥 【新手村診所】", color=discord.Color.blue())
            embed.description = f"你目前處於倒地狀態，已被送往診所治療！\n❤️ 血量恢復至：`{new_hp}/{max_hp}`"
            await interaction.followup.send(embed=embed)
            return

        cursor.close()
        conn.close()

        if current_mp < MP_COST_PER_BATTLE:
            await interaction.followup.send(f"⚡ 魔力不足！當前 MP：`{current_mp}/{max_mp}`，打怪需 `{MP_COST_PER_BATTLE}` MP。", ephemeral=True)
            return

        monster_names = ["狂暴巡邏機械", "變異流浪者", "廢土鋼鐵蜥蜴", "失控維護機器人"]
        monster_name = random.choice(monster_names)
        monster_hp = random.randint(40, 90)
        monster_atk = random.randint(12, 22) # 微調怪物攻擊力，搭配防禦減傷系統更合理

        embed = discord.Embed(title="⚠️ 【遭遇野生敵對目標！】", color=discord.Color.orange())
        embed.add_field(name="🤖 怪物", value=f"**{monster_name}**", inline=True)
        embed.add_field(name="❤️ 血量", value=f"`{monster_hp}` HP", inline=True)
        embed.add_field(name="⚔️ 攻擊力", value=f"`{monster_atk}` ATK", inline=True)
        embed.set_footer(text=f"💡 戰鬥消耗 {MP_COST_PER_BATTLE} MP，防禦力將有效抵擋怪物傷害！")

        view = BattleChoiceView(user_id, monster_name, monster_hp, monster_atk, is_adventure_ambush=False)
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Battle(bot))
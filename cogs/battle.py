import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection, update_and_get_mp, consume_mp

MP_COST_PER_BATTLE = 10  # 每次打怪消耗 10 點 MP

# ⚔️ 戰鬥選擇按鈕介面 (Attack / Run Away)
class BattleChoiceView(discord.ui.View):
    def __init__(self, user_id, monster_name, monster_hp, monster_atk):
        super().__init__(timeout=60) # 60秒未操作自動過期
        self.user_id = user_id
        self.monster_name = monster_name
        self.monster_hp = monster_hp
        self.monster_atk = monster_atk

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 這不是你的遭遇戰！請自己輸入 `/打怪`。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="發動攻擊", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        current_mp, max_mp = update_and_get_mp(self.user_id)
        if current_mp < MP_COST_PER_BATTLE:
            await interaction.followup.send("❌ 你的 MP 不足，無法發動攻擊！", ephemeral=True)
            return

        consume_mp(self.user_id, MP_COST_PER_BATTLE)
        remained_mp = current_mp - MP_COST_PER_BATTLE

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role, hp, max_hp, atk, def, gold FROM players WHERE user_id = ?", (self.user_id,))
        player = cursor.fetchone()
        role, hp, max_hp, atk, player_def, gold = player

        m_hp = self.monster_hp
        turns = 0
        total_damage_taken = 0

        while m_hp > 0 and hp > 0 and turns < 10:
            turns += 1
            damage_to_monster = max(1, atk + random.randint(-2, 3))
            m_hp -= damage_to_monster

            if m_hp <= 0:
                break

            damage_to_player = max(1, self.monster_atk - player_def + random.randint(-1, 2))
            hp -= damage_to_player
            total_damage_taken += damage_to_player

        # 確保血量不會低於 0
        hp = max(0, hp)

        # 4. 戰鬥結果判斷
        if hp > 0:
            # 戰鬥勝利
            reward_gold = random.randint(10, 20)
            cursor.execute("UPDATE players SET hp = ?, gold = gold + ? WHERE user_id = ?", (hp, gold + reward_gold, self.user_id))
            conn.commit()
            cursor.close()
            conn.close()

            embed = discord.Embed(title="🎉 【戰鬥勝利！】", color=discord.Color.green())
            embed.description = (
                f"你與 🤖 **{self.monster_name}** 展開了激烈的 `{turns}` 回合戰鬥，成功將其擊敗！\n\n"
                f"⚔️ **戰鬥結算**：承受了 `{total_damage_taken}` 點傷害（剩餘血量：`{hp}/{max_hp}`）\n"
                f"💧 **消耗魔力**：`-{MP_COST_PER_BATTLE} MP`（剩餘魔力：`{remained_mp}/{max_mp}`）\n"
                f"💰 **獲得戰利品**：`+{reward_gold} G`"
            )
            self.stop()
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            # 戰鬥失敗（hp == 0）➔ 瞬間觸發新手村診所急救！
            recovered_hp = min(max_hp, 50)
            cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (recovered_hp, self.user_id))
            conn.commit()
            cursor.close()
            conn.close()

            embed = discord.Embed(
                title="🏥💥 【戰鬥失敗 · 倒地送醫】",
                color=discord.Color.blue()
            )
            embed.description = (
                f"你在與 🤖 **{self.monster_name}** 激戰後不敵倒地，生命值歸零！\n"
                f"路過的熱心特務立刻將你緊急抬進了**新手村診所**進行急救... 🩺\n\n"
                f"❤️ **診所已將你恢復至**：`{recovered_hp}/{max_hp}` 點生命值"
            )
            self.stop()
            await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="嘗試逃跑", style=discord.ButtonStyle.secondary, emoji="🏃")
    async def run_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        embed = discord.Embed(
            title="🏃 【安全撤退】",
            description=f"你評估了自身狀態後，決定避開 🤖 **{self.monster_name}**！\n你悄悄地離開了現場，**沒有消耗任何 MP**。",
            color=discord.Color.gold()
        )
        self.stop()
        await interaction.edit_original_response(embed=embed, view=None)


class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="打怪", description="發動戰鬥遭遇野生怪物，可先觀察怪物血量決定戰鬥或逃跑")
    async def fight(self, interaction: discord.Interaction):
        await interaction.response.defer()

        user_id = interaction.user.id

        # 1. 刷新 MP 並檢查
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

        # 🏥 如果原本就處於倒地狀態，直接送往診所
        if hp <= 0:
            new_hp = min(max_hp, 50)
            cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
            conn.commit()
            cursor.close()
            conn.close()

            embed = discord.Embed(
                title="🏥 【新手村診所】",
                color=discord.Color.blue()
            )
            embed.description = (
                f"你目前處於 **倒地狀態**，無法進行戰鬥！\n"
                f"路過的熱心特務把你緊急抬進了新手村診所進行急救治療... 🩺\n\n"
                f"❤️ **當前血量已恢復至**：`{new_hp}/{max_hp}`"
            )
            await interaction.followup.send(embed=embed)
            return

        cursor.close()
        conn.close()

        # 💧 檢查 MP 是否足夠預備戰鬥
        if current_mp < MP_COST_PER_BATTLE:
            embed = discord.Embed(
                title="⚡ 【魔力耗盡】",
                description=(
                    f"你的魔力值不足，無法進入戰鬥區域！\n\n"
                    f"💧 **當前魔力**：`{current_mp}/{max_mp}` (每次打怪需 `{MP_COST_PER_BATTLE}` MP)\n"
                    f"💡 **解決方式**：使用 `/use 魔力藥水` 或 `/use 能量飲料` 恢復 MP，也可等待自然恢復。"
                ),
                color=discord.Color.purple()
            )
            await interaction.followup.send(embed=embed)
            return

        # 🎲 隨機生成遭遇的怪物（含 40~90 血量）
        monster_names = ["狂暴巡邏機械", "變異流浪者", "廢土鋼鐵蜥蜴", "失控維護機器人"]
        monster_name = random.choice(monster_names)
        monster_hp = random.randint(40, 90)
        monster_atk = random.randint(10, 25)

        embed = discord.Embed(
            title="⚠️ 【遭遇野生敵對目標！】",
            description=f"前方區域發現了野生怪物！請確認對方數值後決定行動：",
            color=discord.Color.orange()
        )
        embed.add_field(name="🤖 怪物名稱", value=f"**{monster_name}**", inline=True)
        embed.add_field(name="❤️ 怪物血量", value=`{monster_hp}` HP", inline=True)
        embed.add_field(name="⚔️ 預估攻擊力", value=f"`{monster_atk}` ATK", inline=True)
        embed.set_footer(text=f"💡 戰鬥將消耗 {MP_COST_PER_BATTLE} MP，選擇逃跑則不消耗 MP。")

        view = BattleChoiceView(user_id, monster_name, monster_hp, monster_atk)
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Battle(bot))
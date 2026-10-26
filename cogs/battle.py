import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection, gain_player_exp

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
        
        for child in self.children:
            child.disabled = True
        
        embed = discord.Embed(
            title="🏃 【戰鬥逃跑】",
            description=f"你迅速撤退，成功從 **{self.monster_name}** 面前逃脫了！",
            color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def process_turn(self, interaction: discord.Interaction, action: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 取得玩家最新數值與裝備加成
            cursor.execute("""
                SELECT hp, max_hp, atk, def, weapon_atk, armor_def 
                FROM players WHERE user_id = ?
            """, (self.user_id,))
            player = cursor.fetchone()
            if not player:
                await interaction.response.send_message("⚠️ 找不到你的角色資料！", ephemeral=True)
                return

            hp, max_hp, base_atk, base_def, weapon_atk, armor_def = player
            total_atk = base_atk + (weapon_atk or 0)
            total_def = base_def + (armor_def or 0)

            # 1. 玩家攻擊回合
            if action == "attack":
                player_dmg = max(5, total_atk - random.randint(0, 5))
                action_desc = f"你對 **{self.monster_name}** 發動普通攻擊，造成了 `{player_dmg}` 點傷害！"
            
            elif action == "skill":
                # 檢查玩家 MP 是否足夠
                cursor.execute("SELECT mp FROM players WHERE user_id = ?", (self.user_id,))
                current_mp = cursor.fetchone()[0]
            
                if current_mp < 15:
                    await interaction.response.send_message("❌ 你的魔力值 (MP) 不足！", ephemeral=True)
                    return

                # 扣除 15 MP
                cursor.execute("UPDATE players SET mp = mp - 15 WHERE user_id = ?", (self.user_id,))
                conn.commit()
            
                player_dmg = max(12, int(total_atk * 1.5) - random.randint(0, 3))
                action_desc = f"你消耗 15 MP 施放強力技能，對 **{self.monster_name}** 造成了 `{player_dmg}` 點重創！"

            self.monster_hp -= player_dmg

            # 2. 檢查怪物是否死亡（戰鬥勝利）
            if self.monster_hp <= 0:
                gold_reward = random.randint(15, 30)
                dropped_item = random.choice(["生命藥水", "鐵劍碎片", "魔力藥水"]) if random.random() < 0.4 else None
            
                cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (gold_reward, self.user_id))
            
                reward_text = f"💰 獲得金幣：`+{gold_reward} G`"
                
                success_exp, exp_msg = gain_player_exp(self.user_id, exp_amount=80)
                reward_text += f"\n✨ 獲得經驗：`+80 EXP`\n{exp_msg}"

                if dropped_item:
                    cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, dropped_item))
                    row = cursor.fetchone()
                    if row:
                        cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (self.user_id, dropped_item))
                    else:
                        cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (self.user_id, dropped_item))
                    reward_text += f"\n🎁 獲得戰利品：**{dropped_item}** x `1`"

                conn.commit()

                for child in self.children:
                    child.disabled = True

                embed = discord.Embed(
                    title="🎉 【戰鬥勝利！】",
                    description=f"你成功擊敗了 **{self.monster_name}**！\n\n{action_desc}\n\n**【戰利品結算】**\n{reward_text}",
                    color=discord.Color.green()
                )
                await interaction.response.edit_message(embed=embed, view=self)
                self.stop()
                return

            # 3. 怪物反擊回合
            monster_dmg = max(1, self.monster_atk - int(total_def * 0.4))
            hp = max(0, hp - monster_dmg)
        
            cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (hp, self.user_id))
            conn.commit()

            # 4. 檢查玩家是否倒地（當下送醫機制）
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
                await interaction.response.edit_message(embed=embed, view=self)
                self.stop()
                return

            # 5. 更新戰鬥面板（繼續下一回合）
            embed = discord.Embed(
                title="⚔️ 【回合戰鬥進行中】",
                description=action_desc,
                color=discord.Color.gold()
            )
            embed.add_field(name="🤖 怪物狀態", value=f"**{self.monster_name}**\n❤️ 剩餘血量：`{self.monster_hp}` HP", inline=True)
            embed.add_field(name="🛡️ 你的狀態", value=f"❤️ 血量：`{hp}/{max_hp}`\n⚔️ 攻擊力：`{total_atk}`", inline=True)
            embed.set_footer(text="💡 60秒未操作將自動過期。")

            await interaction.response.edit_message(embed=embed, view=self)

        finally:
            cursor.close()
            conn.close()

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="打怪", description="在荒野中尋找野生怪物進行主動戰鬥")
    async def battle(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role_name, hp, max_hp FROM players WHERE user_id = ?", (user_id,))
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

        embed = discord.Embed(
            title="⚔️ 【遭遇野生怪物！】",
            description="你在荒野中鎖定了一隻目標，準備迎戰！",
            color=discord.Color.orange()
        )
        embed.add_field(name="🤖 目標怪物", value=f"**{monster_name}**", inline=True)
        embed.add_field(name="❤️ 血量", value=f"`{monster_hp}` HP", inline=True)
        embed.add_field(name="⚔️ 攻擊力", value=f"`{monster_atk}` ATK", inline=True)
        embed.set_footer(text="💡 60秒未操作將自動過期。")

        view = BattleChoiceView(user_id, monster_name, monster_hp, monster_atk)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Battle(bot))
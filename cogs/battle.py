import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="打怪", description="遭遇怪物並進行回合制戰鬥")
    async def battle(self, interaction: discord.Interaction):
        await interaction.response.defer()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role, hp, atk, def, gold FROM players WHERE user_id = ?", (interaction.user.id,))
        player = cursor.fetchone()

        if not player or not player[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/setup_roles` 選擇職業。", ephemeral=True)
            return

        role_name, player_hp, player_atk, player_def, player_gold = player
        
        if player_hp <= 0:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 你目前處於倒地狀態，無法打怪！請先使用生命藥水 (`/use`) 恢復生命值。", ephemeral=True)
            return

        # 隨機挑選一隻怪物（怪物具備總血量 hp、攻擊力 atk、金幣範圍）
        monster_template = random.choice([
            {"name": "👾 變異流浪體", "hp": 60, "atk": 15, "gold_min": 10, "gold_max": 20},
            {"name": "🤖 狂暴巡邏機械", "hp": 90, "atk": 22, "gold_min": 20, "gold_max": 35}
        ])
        
        monster_hp = monster_template["hp"]
        monster_name = monster_template["name"]
        monster_atk = monster_template["atk"]
        
        # 每回合造成的傷害計算（根據玩家攻擊力與怪物防禦，最低為 1）
        player_dmg = max(1, player_atk - 2)
        monster_dmg = max(1, monster_atk - player_def)

        # 🔄 回合制模擬戰鬥（直到其中一方血量歸零）
        rounds = 0
        total_damage_taken = 0
        
        while monster_hp > 0 and player_hp > 0:
            rounds += 1
            
            # 1. 玩家攻擊怪物
            monster_hp -= player_dmg
            if monster_hp <= 0:
                break  # 怪物血量歸零，戰鬥結束
                
            # 2. 怪物反擊玩家
            player_hp -= monster_dmg
            total_damage_taken += monster_dmg

        # 計算最後玩家剩餘血量
        current_hp = max(0, player_hp)
        is_fainted = (current_hp == 0)

        # 更新資料庫中的玩家血量
        cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (current_hp, interaction.user.id))

        # 戰鬥失敗處理
        if is_fainted:
            conn.commit()
            cursor.close()
            conn.close()
            embed = discord.Embed(title="💀 【戰鬥失敗】", color=discord.Color.red())
            embed.description = f"你在與 **{monster_name}** 激戰了 **{rounds}** 個回合後不敵倒地...\n總共承受了 **{total_damage_taken}** 點反擊傷害，生命值歸零！"
            await interaction.followup.send(embed=embed)
            return

        # 戰鬥勝利，計算隨機金幣
        reward_gold = random.randint(monster_template["gold_min"], monster_template["gold_max"])
        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (reward_gold, interaction.user.id))
        conn.commit()
        cursor.close()
        conn.close()

        # 回傳戰鬥結果（包含總回合數與實際承受的總反擊傷害）
        embed = discord.Embed(title="🎉 【戰鬥勝利！】", color=discord.Color.green())
        embed.description = f"你與 **{monster_name}** 展開了激烈的 **{rounds}** 回合戰鬥，成功將其擊敗！"
        embed.add_field(
            name="⚔️ 戰鬥結算", 
            value=f"每回合傷害：`{player_dmg}`\n承受反擊總計：**-{total_damage_taken} HP** (剩餘血量: `{current_hp}`)", 
            inline=False
        )
        embed.add_field(name="💰 獲得戰利品", value=f"**+{reward_gold} G**", inline=True)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Battle(bot))
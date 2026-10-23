import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection, take_damage  # 1. 務必要引入 take_damage

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="打怪", description="遭遇怪物並進行戰鬥")
    async def battle(self, interaction: discord.Interaction):
        await interaction.response.defer()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role, hp, atk, def, gold FROM players WHERE user_id = ?", (interaction.user.id,))
        player = cursor.fetchone()

        if not player or not player[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/選擇身份`。", ephemeral=True)
            return

        role_name, player_hp, player_atk, player_def, player_gold = player
        
        # 檢查是否已經倒地
        if player_hp <= 0:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 你目前處於倒地狀態，無法打怪！請先使用生命藥水 (`/use`) 恢復生命值。", ephemeral=True)
            return

        # 隨機挑選一隻怪物
        monster = random.choice([
            {"name": "👾 變異流浪體", "hp": 60, "atk": 15, "gold": 15},
            {"name": "🤖 狂暴巡邏機械", "hp": 90, "atk": 22, "gold": 25}
        ])
        
        player_dmg = max(1, player_atk - 2)
        
        # 計算怪物對玩家造成的傷害（怪物的 ATK 減去玩家的 DEF，最低為 1 點）
        monster_dmg = max(1, monster["atk"] - player_def)
        
        # 先關閉當前的查詢連線，避免與 take_damage 內部連線衝突
        cursor.close()
        conn.close()

        # 2. 核心：呼叫 db.py 中的 take_damage 進行被動扣血
        new_hp, is_fainted = take_damage(interaction.user.id, monster_dmg)

        # 如果血量歸零，判定戰鬥失敗
        if is_fainted:
            embed = discord.Embed(title="💀 【戰鬥失敗】", color=discord.Color.red())
            embed.description = f"你在與 **{monster['name']}** 的交鋒中不敵，受到了 **{monster_dmg}** 點傷害！\n生命值歸零，倒下了..."
            await interaction.followup.send(embed=embed)
            return

        # 3. 戰鬥勝利，重新連線發放金幣
        conn = get_db_connection()
        cursor = conn.cursor()
        reward_gold = monster["gold"]
        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (reward_gold, interaction.user.id))
        conn.commit()
        cursor.close()
        conn.close()

        # 回傳戰鬥結果與扣血資訊
        embed = discord.Embed(title="🎉 【戰鬥勝利！】", color=discord.Color.green())
        embed.description = f"你對 **{monster['name']}** 造成了 **{player_dmg}** 點傷害並成功擊敗對方！"
        embed.add_field(name="⚔️ 戰鬥消耗", value=f"承受反擊：**-{monster_dmg} HP** (剩餘血量: `{new_hp}`)", inline=False)
        embed.add_field(name="💰 獲得戰利品", value=f"**+{reward_gold} G**", inline=True)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Battle(bot))
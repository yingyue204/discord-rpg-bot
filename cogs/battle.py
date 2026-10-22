import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="打怪", description="前往野外遭遇怪物並展開戰鬥！")
    async def battle(self, interaction: discord.Interaction):
        conn = sqlite3.connect("rpg.db")
        cursor = conn.cursor()

        # 確保玩家表格存在並讀取屬性
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                role TEXT,
                hp INTEGER DEFAULT 100,
                max_hp INTEGER DEFAULT 100,
                atk INTEGER DEFAULT 25,
                def INTEGER DEFAULT 10,
                speed INTEGER DEFAULT 20,
                gold INTEGER DEFAULT 100
            )
        """)

        cursor.execute("SELECT role, hp, atk, def, gold FROM players WHERE user_id = ?", (interaction.user.id,))
        player = cursor.fetchone()

        if not player or not player[0]:
            conn.close()
            await interaction.response.send_message("⚠️ 你尚未選擇職業！請先使用 `/選擇身份` 或在頻道點選職業選單。", ephemeral=True)
            return

        role_name, player_hp, player_atk, player_def, player_gold = player

        # 隨機遭遇怪物
        monsters = [
            {"name": "👾 變異流浪體", "hp": 60, "atk": 15, "exp": 20, "gold": 15},
            {"name": "🤖 狂暴巡邏機械", "hp": 90, "atk": 22, "exp": 35, "gold": 25},
            {"name": "🕷️ 電磁毒蛛", "hp": 50, "atk": 18, "exp": 15, "gold": 10}
        ]
        monster = random.choice(monsters)
        monster_hp = monster["hp"]

        # 簡單回合戰鬥計算
        # 玩家造成的傷害 = 玩家攻擊力 - 怪物簡化防禦 (最少 1)
        player_dmg = max(1, player_atk - 2)
        # 怪物造成的傷害 = 怪物攻擊力 - 玩家防禦力 (最少 1)
        monster_dmg = max(1, monster["atk"] - player_def)

        # 戰鬥過程簡述
        logs = []
        logs.append(f"⚔️ 你發動攻擊，對 **{monster['name']}** 造成了 **{player_dmg}** 點傷害！")
        monster_hp -= player_dmg

        if monster_hp <= 0:
            reward_gold = monster["gold"]
            cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (reward_gold, interaction.user.id))
            conn.commit()
            conn.close()

            embed = discord.Embed(
                title="🎉 【戰鬥勝利！】",
                description=f"你成功擊敗了 **{monster['name']}**！\n\n" + "\n".join(logs),
                color=discord.Color.green()
            )
            embed.add_field(name="💰 獲得戰利品", value=f"**+{reward_gold} G**", inline=True)
            await interaction.response.send_message(embed=embed)
            return

        logs.append(f"💥 **{monster['name']}** 進行反擊，對你造成了 **{monster_dmg}** 點傷害！")
        new_hp = max(0, player_hp - monster_dmg)

        # 更新玩家剩餘血量
        cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, interaction.user.id))
        
        # 玩家勝利（進行第二回合判定）
        reward_gold = monster["gold"]
        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (reward_gold, interaction.user.id))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title=f"⚔️ 【遭遇戰：{monster['name']}】",
            description="\n".join(logs),
            color=discord.Color.orange()
        )
        embed.add_field(name="❤️ 你的剩餘血量", value=f"**{new_hp} HP**", inline=True)
        embed.add_field(name="💰 獲得獎勵", value=f"**+{reward_gold} G**", inline=True)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Battle(bot))
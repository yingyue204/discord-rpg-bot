import discord
from discord.ext import commands
from discord import app_commands
import random
from db import get_db_connection  # 引入雲端資料庫連線模組

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="打怪", description="前往野外遭遇怪物並展開戰鬥！")
    async def battle(self, interaction: discord.Interaction):
        conn = get_db_connection()
        cursor = conn.cursor()

        # 確保玩家表格存在並讀取屬性 (PostgreSQL 語法)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id BIGINT PRIMARY KEY,
                role TEXT,
                hp INTEGER DEFAULT 100,
                max_hp INTEGER DEFAULT 100,
                atk INTEGER DEFAULT 25,
                def INTEGER DEFAULT 10,
                speed INTEGER DEFAULT 20,
                gold INTEGER DEFAULT 100
            )
        """)
        conn.commit()

        # 查詢玩家資料 (使用 %s 佔位符)
        cursor.execute("SELECT role, hp, atk, def, gold FROM players WHERE user_id = %s", (interaction.user.id,))
        player = cursor.fetchone()

        if not player or not player[0]:
            cursor.close()
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
        player_dmg = max(1, player_atk - 2)
        monster_dmg = max(1, monster["atk"] - player_def)

        # 戰鬥過程簡述
        logs = []
        logs.append(f"⚔️ 你發動攻擊，對 **{monster['name']}** 造成了 **{player_dmg}** 點傷害！")
        monster_hp -= player_dmg

        if monster_hp <= 0:
            reward_gold = monster["gold"]
            cursor.execute("UPDATE players SET gold = gold + %s WHERE user_id = %s", (reward_gold, interaction.user.id))
            conn.commit()
            cursor.close()
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

        # 更新玩家剩餘血量並發放獎勵 (使用 %s 佔位符)
        reward_gold = monster["gold"]
        cursor.execute("UPDATE players SET hp = %s, gold = gold + %s WHERE user_id = %s", (new_hp, reward_gold, interaction.user.id))
        conn.commit()
        cursor.close()
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
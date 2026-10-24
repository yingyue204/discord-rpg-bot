import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection
from cogs.battle import BattleChoiceView  # 引用戰鬥按鈕來處理突發怪物

class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="adventure", description="前往未知區域進行冒險與搜刮（低機率獲取寶箱，可能遭遇突發怪物）")
    async def adventure(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role, hp, max_hp, gold FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()

        if not player or not player[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/setup_roles` 選擇職業。", ephemeral=True)
            return

        role_name, hp, max_hp, gold = player

        # 🏥 檢查倒地狀態
        if hp <= 0:
            new_hp = min(max_hp, 50)
            cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
            conn.commit()
            cursor.close()
            conn.close()

            embed = discord.Embed(title="🏥 【新手村診所】", color=discord.Color.blue())
            embed.description = f"你處於倒地狀態無法冒險！已被熱心特務送至診所急救。\n❤️ 當前血量：`{new_hp}/{max_hp}`"
            await interaction.followup.send(embed=embed)
            return

        cursor.close()
        conn.close()

        # ⚔️ 25% 機率在冒險途中突發遭遇野生怪物！
        encounter_ambush = random.random() < 0.25
        if encounter_ambush:
            monster_names = ["廢土伏擊者", "迷路防禦機械", "暴走掠奪者"]
            monster_name = random.choice(monster_names)
            monster_hp = random.randint(30, 60)
            monster_atk = random.randint(6, 16)

            embed = discord.Embed(
                title="⚡ 【冒險突發狀況！遭遇敵人伏擊！】",
                description="你在搜刮廢墟時不小心驚動了潛伏的怪物，必須立刻做出反應！（此戰鬥不消耗 MP）",
                color=discord.Color.red()
            )
            embed.add_field(name="🤖 突發怪物", value=f"**{monster_name}**", inline=True)
            embed.add_field(name="❤️ 血量", value=f"`{monster_hp}` HP", inline=True)
            embed.add_field(name="⚔️ 攻擊力", value=f"`{monster_atk}` ATK", inline=True)
            embed.set_footer(text="💡 擊敗突發敵人有更高的寶箱掉落機會！60秒未操作將自動過期。")

            # 呼叫 BattleChoiceView，標記為冒險突發戰鬥 (is_adventure_ambush=True)
            view = BattleChoiceView(user_id, monster_name, monster_hp, monster_atk, is_adventure_ambush=True)
            
            # 傳送訊息並將訊息物件綁定給 view.message，以便 60 秒超時後自動更新按鈕狀態
            sent_message = await interaction.followup.send(embed=embed, view=view, wait=True)
            view.message = sent_message
            return

        # 🎒 平安搜刮邏輯
        found_gold = random.randint(5, 15)
        
        # 冒險獲得寶箱的機率
        got_chest = random.random() < 0.1
        if got_chest:
            found_item = "神秘寶箱"
        else:
            found_item = random.choice(["生命藥水", "急救包", "鐵劍碎片"])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, found_item))
        item_row = cursor.fetchone()
        
        if item_row:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, found_item))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, found_item))

        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (found_gold, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        embed = discord.Embed(title="🛡️ 【冒險搜刮成功】", color=discord.Color.green())
        if got_chest:
            embed.add_field(name="🎁 驚喜發現", value="**✨ 神秘寶箱 x 1**（極低機率幸運獲得！）", inline=True)
        else:
            embed.add_field(name="📦 獲得道具", value=f"**{found_item}** x `1`", inline=True)
            
        embed.add_field(name="💰 獲得金幣", value=f"**+{found_gold} G**", inline=True)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Adventure(bot))
import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class Adventure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="adventure", description="前往未知區域進行冒險與搜刮")
    async def adventure(self, interaction: discord.Interaction):
        await interaction.response.defer()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role, hp, max_hp, gold FROM players WHERE user_id = ?", (interaction.user.id,))
        player = cursor.fetchone()

        if not player or not player[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/setup_roles` 選擇職業。", ephemeral=True)
            return

        role_name, hp, max_hp, gold = player

        # 🏥 檢查是否處於倒地狀態 (hp <= 0)
        if hp <= 0:
            # 診所治療：從當前血量 (0) 恢復 50 點，但上限不超過 max_hp
            new_hp = min(max_hp, hp + 50)
            actual_healed = new_hp - hp

            cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, interaction.user.id))
            conn.commit()
            cursor.close()
            conn.close()

            embed = discord.Embed(
                title="🏥 【新手村診所】",
                color=discord.Color.blue()
            )
            embed.description = (
                f"你目前處於 **倒地狀態**，無法進行危險的冒險！\n"
                f"路過的熱心特務把你緊急抬進了新手村診所進行急救治療... 🩺\n\n"
                f"❤️ **恢復了 `{actual_healed}` 點生命值**\n"
                f"📊 **當前血量**：`{new_hp}/{max_hp}`"
            )
            await interaction.followup.send(embed=embed)
            return

        # 🎒 血量正常，執行原本的冒險搜刮邏輯
        found_gold = random.randint(5, 20)
        found_item = random.choice(["生命藥水", "急救包", "鐵劍碎片"])
        
        # 檢查背包是否已有該道具
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (interaction.user.id, found_item))
        item_row = cursor.fetchone()
        
        if item_row:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (interaction.user.id, found_item))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (interaction.user.id, found_item))

        # 增加金幣
        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (interaction.user.id, found_gold))
        conn.commit()
        cursor.close()
        conn.close()

        # 回傳冒險成功結果
        embed = discord.Embed(title="🛡️ 【冒險搜刮成功】", color=discord.Color.green())
        embed.add_field(name="📦 獲得道具", value=f"**{found_item}** x `1`", inline=True)
        embed.add_field(name="💰 獲得金幣", value=f"**+{found_gold} G**", inline=True)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Adventure(bot))
import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class Fish(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="釣魚", description="前往水域揮竿釣魚，獲取鮮魚與各種水產資源（消耗 10 點體力）")
    async def fish(self, interaction: discord.Interaction):
        # 務必第一時間 defer，防止 Discord 逾時
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 1. 檢查玩家狀態與體力
            cursor.execute("SELECT hp, stamina, max_stamina FROM players WHERE user_id = ?", (user_id,))
            player = cursor.fetchone()

            if not player:
                await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/setup_roles` 選擇職業。", ephemeral=True)
                return

            hp, stamina, max_stamina = player

            if hp <= 0:
                await interaction.followup.send("❌ 你目前處於倒地狀態，無法進行釣魚！請先前往診所治療。", ephemeral=True)
                return

            stamina_cost = 10
            if stamina < stamina_cost:
                embed = discord.Embed(
                    title="⚡ 【體力耗盡】",
                    description=f"你的體力不足以支撐揮竿！\n當前體力：`{stamina}/{max_stamina}`（需要 `{stamina_cost}` 點）\n\n💡 請吃點食物或休息後再試！",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # 2. 扣除體力
            new_stamina = stamina - stamina_cost
            cursor.execute("UPDATE players SET stamina = ? WHERE user_id = ?", (new_stamina, user_id))

            # 3. 釣魚權重抽獎 (Item, Weight)
            fish_drops = [
                ("鮮魚", 55),       # 料理核心材料
                ("廢鐵罐", 25),     # 廢棄物，可以賣給系統換零錢
                ("神祕寶箱", 5),    # 極低機率大獎
                ("海帶", 15)        # 額外生活素材
            ]
            items, weights = zip(*fish_drops)
            caught_item = random.choices(items, weights=weights, k=1)[0]
            
            # 如果釣到廢鐵罐，額外贈送少量金幣
            found_gold = random.randint(2, 6) if caught_item == "廢鐵罐" else 0

            # 4. 更新背包與金幣
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, caught_item))
            inv_row = cursor.fetchone()

            if inv_row:
                cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, caught_item))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, caught_item))

            if found_gold > 0:
                cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (found_gold, user_id))

            conn.commit()

            # 5. 回報結果
            embed = discord.Embed(title="🎣 【快樂釣魚時光】", color=discord.Color.blue())
            embed.add_field(name="🐟 收獲成果", value=f"你耐心地在水邊等待，成功釣到了 **{caught_item}** x `1`！", inline=False)
            
            if found_gold > 0:
                embed.add_field(name="💰 意外發現", value=f"你在廢鐵罐裡找到了藏著的 **+{found_gold} G**！", inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            conn.rollback()
            print(f"❌ 釣魚指令發生錯誤: {e}")
            try:
                await interaction.followup.send(f"❌ 釣魚過程發生未預期的錯誤：`{e}`", ephemeral=True)
            except:
                pass
        finally:
            # 🛡️ 鐵布衫防護：絕對確保連線關閉，絕不卡死
            try:
                cursor.close()
                conn.close()
            except:
                pass

async def setup(bot):
    await bot.add_cog(Fish(bot))
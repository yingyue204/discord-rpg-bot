import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from db import get_db_connection, get_player_farm

class Farm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="農場", description="查看你的私人農場土地與作物狀態")
    async def farm_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        plots = get_player_farm(user_id)

        embed = discord.Embed(
            title="🌾 【私人農場】",
            description="以下是你的農田狀態：\n*(提示：可使用 /種植 與 /收成 來管理農作物)*",
            color=discord.Color.green()
        )
        
        for plot in plots:
            status = plot["status"]
            if status == "empty":
                status_text = "🟢 空地 (可使用 /種植)"
            elif status == "growing":
                status_text = f"🌱 生長中 (`{plot['crop_name']}`)"
            else:
                status_text = f"✨ 已成熟！ (`{plot['crop_name']}`)"
                
            embed.add_field(name=f"第 {plot['plot_index']} 號田", value=status_text, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="種植", description="選擇一塊空地種下種子")
    @app_commands.rename(plot_index="田地編號", seed_name="種子名稱")
    @app_commands.describe(plot_index="你想種在哪一塊田 (例如 1, 2, 3...)", seed_name="你想種植的種子名稱")
    async def plant_crop(self, interaction: discord.Interaction, plot_index: int, seed_name: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 1. 檢查玩家背包是否有該種子
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, seed_name))
            inv = cursor.fetchone()
            if not inv or inv["quantity"] <= 0:
                await interaction.followup.send(f"❌ 你的背包裡沒有【{seed_name}】！請先前往商店購買。", ephemeral=True)
                return

            # 2. 檢查該田地狀態
            cursor.execute("SELECT * FROM farm WHERE user_id = ? AND plot_index = ?", (user_id, plot_index))
            plot = cursor.fetchone()
            if not plot:
                await interaction.followup.send(f"⚠️ 找不到編號為 `{plot_index}` 的田地！", ephemeral=True)
                return

            if plot["status"] != "empty":
                await interaction.followup.send(f"⚠️ 第 `{plot_index}` 號田目前不是空地（已有作物正在生長或已成熟）！", ephemeral=True)
                return

            # 將種子名稱轉為對應收成作物名稱（例如「小麥種子」-> 產出「小麥」）
            crop_name = seed_name.replace("種子", "")
            # 設定成熟時間（例如 5 分鐘後成熟，可依需求調整）
            harvest_time = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

            # 3. 扣除 1 個種子
            if inv["quantity"] == 1:
                cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, seed_name))
            else:
                cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, seed_name))

            # 4. 更新農田狀態
            cursor.execute("""
                UPDATE farm SET status = 'growing', crop_name = ?, harvest_time = ? 
                WHERE user_id = ? AND plot_index = ?
            """, (crop_name, harvest_time, user_id, plot_index))
            conn.commit()

            embed = discord.Embed(
                title="🌱 【種植成功】",
                description=f"你在第 **{plot_index}** 號田種下了 **{seed_name}**！\n\n⏳ 預計成熟作物：**{crop_name}**（大約 5 分鐘後成熟）",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            conn.rollback()
            await interaction.followup.send(f"❌ 種植過程發生錯誤：`{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

    @app_commands.command(name="收成", description="收成你農場中已經成熟的作物")
    @app_commands.rename(plot_index="田地編號")
    @app_commands.describe(plot_index="你想收成哪一塊田的作物")
    async def harvest_crop(self, interaction: discord.Interaction, plot_index: int):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 1. 檢查該田地狀態
            cursor.execute("SELECT * FROM farm WHERE user_id = ? AND plot_index = ?", (user_id, plot_index))
            plot = cursor.fetchone()
            if not plot:
                await interaction.followup.send(f"⚠️ 找不到編號為 `{plot_index}` 的田地！", ephemeral=True)
                return

            if plot["status"] == "empty":
                await interaction.followup.send(f"⚠️ 第 `{plot_index}` 號田是空的，沒有東西可以收成！", ephemeral=True)
                return

            # 檢查是否已過成熟時間
            harvest_time = datetime.strptime(plot["harvest_time"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() < harvest_time:
                rem_sec = int((harvest_time - datetime.now()).total_seconds())
                mins, secs = divmod(rem_sec, 60)
                await interaction.followup.send(f"⏳ 作物還沒成熟！還需要等待 **{mins} 分 {secs} 秒**。", ephemeral=True)
                return

            crop_name = plot["crop_name"]

            # 2. 📦 背包容量檢查 (預設 20 格種類上限)
            cursor.execute("SELECT COUNT(*) as slots FROM inventory WHERE user_id = ? AND quantity > 0", (user_id,))
            current_slots = cursor.fetchone()["slots"]

            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, crop_name))
            inv_row = cursor.fetchone()

            cursor.execute("SELECT max_bag_slots FROM players WHERE user_id = ?", (user_id,))
            player_row = cursor.fetchone()
            max_slots = player_row["max_bag_slots"] if player_row and "max_bag_slots" in player_row.keys() and player_row["max_bag_slots"] else 20

            if not inv_row and current_slots >= max_slots:
                await interaction.followup.send(f"⚠️ 你的隨身背包已滿 (`{current_slots}/{max_slots}` 格)，無法放下新種類的作物【{crop_name}】！\n\n💡 請先使用 `/存入倉庫` 整理背包。", ephemeral=True)
                return

            # 3. 發放收成作物 (產量隨機 2~4 個)
            import random
            yield_qty = random.randint(2, 4)

            if inv_row:
                cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?", (yield_qty, user_id, crop_name))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)", (user_id, crop_name, yield_qty))

            # 4. 重置農田為空地
            cursor.execute("""
                UPDATE farm SET status = 'empty', crop_name = NULL, harvest_time = NULL 
                WHERE user_id = ? AND plot_index = ?
            """, (user_id, plot_index))
            conn.commit()

            embed = discord.Embed(
                title="✨ 【農場大豐收！】",
                description=f"你成功收成了第 **{plot_index}** 號田！\n\n📦 獲得產物：**{crop_name}** x `{yield_qty}`",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            conn.rollback()
            await interaction.followup.send(f"❌ 收成過程發生錯誤：`{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

async def setup(bot):
    await bot.add_cog(Farm(bot))
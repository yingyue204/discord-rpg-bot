import time
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# 作物生長時間設定（秒）
CROP_GROWTH_TIMES = {
    "小麥": 30,
    "米": 45,
    "蔬菜": 40,
    "水果": 50,
    "香料": 60,
    "蔥": 25
}

class Farm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="農場", description="查看你的農田土地與作物狀態")
    async def farm(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT plot_index, crop_name, ready_timestamp, status FROM farm_plots WHERE user_id = ?", (user_id,))
        plots = {row["plot_index"]: dict(row) for row in cursor.fetchall()}
        cursor.close()
        conn.close()

        now = time.time()
        desc = "🌾 **你的私人農田**（共有 4 塊田地）：\n\n"
        for i in range(1, 5):
            if i in plots:
                p = plots[i]
                cname = p["crop_name"]
                if now >= p["ready_timestamp"] or p["status"] == "ready":
                    desc += f"田地 `{i}`: 🌱 **{cname}** ➔ 🟢 **成熟可收成！**\n"
                else:
                    left = int(p["ready_timestamp"] - now)
                    desc += f"田地 `{i}`: 🌱 **{cname}** ➔ ⏳ 生長中 (剩餘 `{left}s`)\n"
            else:
                desc += f"田地 `{i}`: 📭 **(荒地 - 可種植)**\n"

        embed = discord.Embed(title="🌱 【農場管理】", description=desc, color=discord.Color.green())
        embed.set_footer(text="💡 使用 /種種子 與 /收成作物 來管理農田！")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="種種子", description="在指定田地種植作物")
    @app_commands.rename(plot_index="田地編號", crop_name="作物名稱")
    @app_commands.choices(crop_name=[
        app_commands.Choice(name="小麥 (30秒)", value="小麥"),
        app_commands.Choice(name="米 (45秒)", value="米"),
        app_commands.Choice(name="蔬菜 (40秒)", value="蔬菜"),
        app_commands.Choice(name="水果 (50秒)", value="水果"),
        app_commands.Choice(name="香料 (60秒)", value="香料"),
        app_commands.Choice(name="蔥 (25秒)", value="蔥")
    ])
    async def plant(self, interaction: discord.Interaction, plot_index: int, crop_name: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        if plot_index < 1 or plot_index > 4:
            await interaction.followup.send("⚠️ 田地編號必須介於 1 到 4 之間！", ephemeral=True)
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        # 檢查該田地是否已有作物
        cursor.execute("SELECT * FROM farm_plots WHERE user_id = ? AND plot_index = ?", (user_id, plot_index))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            await interaction.followup.send(f"⚠️ 第 `{plot_index}` 塊田地已經有作物正在生長了！", ephemeral=True)
            return

        ready_time = time.time() + CROP_GROWTH_TIMES[crop_name]
        cursor.execute("""
            INSERT INTO farm_plots (user_id, plot_index, crop_name, ready_timestamp, status)
            VALUES (?, ?, ?, ?, 'growing')
        """, (user_id, plot_index, crop_name, ready_time))

        conn.commit()
        cursor.close()
        conn.close()

        await interaction.followup.send(f"✅ 成功在第 `{plot_index}` 塊田地種下了 **{crop_name}**！", ephemeral=True)

    @app_commands.command(name="收成作物", description="收成所有成熟的農田作物")
    async def harvest_farm(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT plot_index, crop_name, ready_timestamp FROM farm_plots WHERE user_id = ?", (user_id,))
        plots = cursor.fetchall()

        now = time.time()
        harvested = {}

        for p in plots:
            idx, cname, ready_ts = p["plot_index"], p["crop_name"], p["ready_timestamp"]
            if now >= ready_ts:
                harvested[cname] = harvested.get(cname, 0) + 2  # 每次收成 2 個
                cursor.execute("DELETE FROM farm_plots WHERE user_id = ? AND plot_index = ?", (user_id, idx))

        if not harvested:
            cursor.close()
            conn.close()
            await interaction.followup.send("⏳ 目前沒有任何作物成熟可以收成！", ephemeral=True)
            return

        reward_text = ""
        for cname, qty in harvested.items():
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, cname))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?", (qty, user_id, cname))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)", (user_id, cname, qty))
            reward_text += f"- **{cname}** x `{qty}`\n"

        conn.commit()
        cursor.close()
        conn.close()

        await interaction.followup.send(f"🎉 **農場收成成功！** 獲得以下作物：\n{reward_text}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Farm(bot))
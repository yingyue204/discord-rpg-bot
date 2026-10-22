import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class RoleSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # 職業對應的初始數值設定
    ROLE_STATS = {
        "駭客": {"hp": 100, "atk": 25, "def": 10, "speed": 35},
        "磁暴重裝": {"hp": 180, "atk": 18, "def": 35, "speed": 15},
        "異能覺醒": {"hp": 110, "atk": 35, "def": 15, "speed": 20},
        "神射手": {"hp": 115, "atk": 30, "def": 16, "speed": 25}
    }

    @discord.ui.select(
        placeholder="請選擇你的特務職業...",
        options=[
            discord.SelectOption(label="駭客", description="專精系統超頻與極速專家"),
            discord.SelectOption(label="磁暴重裝", description="重型外骨骼防禦專家"),
            discord.SelectOption(label="異能覺醒", description="高攻擊力超自然異能者"),
            discord.SelectOption(label="神射手", description="高穿透電磁步槍遠程專家"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_role = select.values[0]
        stats = self.ROLE_STATS[selected_role]

        conn = sqlite3.connect("rpg.db")
        cursor = conn.cursor()

        # 確保玩家表格具備職業與屬性欄位
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                role TEXT,
                hp INTEGER,
                max_hp INTEGER,
                atk INTEGER,
                def INTEGER,
                speed INTEGER,
                gold INTEGER DEFAULT 100
            )
        """)

        # 檢查玩家是否已經選擇過職業
        cursor.execute("SELECT role FROM players WHERE user_id = ?", (interaction.user.id,))
        result = cursor.fetchone()

        if result and result[0]:
            current_role = result[0]
            conn.close()
            # 問題一解決方案：跳出已經綁定過的提醒提示
            await interaction.response.send_message(
                f"⚠️ 你已經綁定過職業【**{current_role}**】了！無法重複選擇。",
                ephemeral=True
            )
            return

        # 問題二解決方案：寫入玩家選擇的職業與對應數值
        cursor.execute("""
            INSERT INTO players (user_id, role, hp, max_hp, atk, def, speed, gold)
            VALUES (?, ?, ?, ?, ?, ?, ?, 100)
            ON CONFLICT(user_id) DO UPDATE SET
                role = excluded.role,
                hp = excluded.hp,
                max_hp = excluded.max_hp,
                atk = excluded.atk,
                def = excluded.def,
                speed = excluded.speed
        """, (interaction.user.id, selected_role, stats["hp"], stats["hp"], stats["atk"], stats["def"], stats["speed"]))

        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"🎉 成功選擇職業【**{selected_role}**】！\n"
            f"❤️ 血量: {stats['hp']} | ⚔️ 攻擊力: {stats['atk']} | 🛡️ 防禦力: {stats['def']} | ⚡ 速度: {stats['speed']}",
            ephemeral=True
        )

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="選擇身份", description="選擇你的角色職業身份")
    async def select_role_cmd(self, interaction: discord.Interaction):
        view = RoleSelectView()
        await interaction.response.send_message("請點選下方選單選擇你的職業身份：", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Roles(bot))
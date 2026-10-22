import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection  # 引入雲端資料庫連線模組

class RoleSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

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

        conn = get_db_connection()
        cursor = conn.cursor()

        # 確保玩家表格存在 (PostgreSQL 語法)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id BIGINT PRIMARY KEY,
                role TEXT,
                hp INTEGER,
                max_hp INTEGER,
                atk INTEGER,
                def INTEGER,
                speed INTEGER,
                gold INTEGER DEFAULT 100
            )
        """)

        # 檢查是否已選擇過職業 (使用 %s 佔位符)
        cursor.execute("SELECT role FROM players WHERE user_id = %s", (interaction.user.id,))
        result = cursor.fetchone()

        if result and result[0]:
            cursor.close()
            conn.close()
            await interaction.response.send_message(
                f"⚠️ 你已經綁定過職業【**{result[0]}**】了！無法重複選擇。",
                ephemeral=True
            )
            return

        # 1. 寫入資料庫 (使用 %s 佔位符)
        cursor.execute("""
            INSERT INTO players (user_id, role, hp, max_hp, atk, def, speed, gold)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 100)
            ON CONFLICT (user_id) DO UPDATE SET
                role = EXCLUDED.role,
                hp = EXCLUDED.hp,
                max_hp = EXCLUDED.max_hp,
                atk = EXCLUDED.atk,
                def = EXCLUDED.def,
                speed = EXCLUDED.speed
        """, (interaction.user.id, selected_role, stats["hp"], stats["hp"], stats["atk"], stats["def"], stats["speed"]))

        conn.commit()
        cursor.close()
        conn.close()

        # 2. 自動賦予 Discord 伺服器真實身分組
        guild = interaction.guild
        member = interaction.user
        role_to_give = discord.utils.get(guild.roles, name=selected_role)

        role_msg = ""
        if role_to_give:
            try:
                await member.add_roles(role_to_give)
                role_msg = f"\n✨ 已成功為你掛載 Discord 身分組：【{selected_role}】"
            except Exception as e:
                role_msg = f"\n⚠️ 身分組賦予失敗（請確認機器人權限是否高於該身分組）：{e}"
        else:
            role_msg = f"\n⚠️ 伺服器中找不到名為「{selected_role}」的身分組，請管理員建立對應身分組！"

        await interaction.response.send_message(
            f"🎉 成功選擇職業【**{selected_role}**】！\n"
            f"❤️ 血量: {stats['hp']} | ⚔️ 攻擊力: {stats['atk']} | 🛡️ 防禦力: {stats['def']} | ⚡ 速度: {stats['speed']}"
            f"{role_msg}",
            ephemeral=True
        )

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_roles")
    @commands.has_permissions(administrator=True)
    async def setup_roles_prefix(self, ctx):
        try:
            await ctx.message.delete()
        except:
            pass

        embed = discord.Embed(
            title="💻 【虛擬次元觀測站 · 特務職業指南】",
            description="歡迎來到虛擬次元！以下為各大特務職業的詳細介紹與初始屬性配置：",
            color=discord.Color.dark_embed()
        )
        embed.add_field(name="駭客", value="• 職業簡介：專精於系統超頻與軟體穿透的極速專家。\n初始屬性：❤️ 血量 100 | ⚔️ 攻擊 25 | 🛡️ 防禦 10 | ⚡ 速度 35", inline=False)
        embed.add_field(name="磁暴重裝", value="• 職業簡介：配備重型外骨骼動力裝甲與電磁防禦盾。\n初始屬性：❤️ 血量 180 | ⚔️ 攻擊 18 | 🛡️ 防禦 35 | ⚡ 速度 15", inline=False)
        embed.add_field(name="異能覺醒", value="• 職業簡介：突破人體與科技極限的超自然異能者。\n初始屬性：❤️ 血量 110 | ⚔️ 攻擊 35 (最高) | 🛡️ 防禦 15 | ⚡ 速度 20", inline=False)
        embed.add_field(name="神射手", value="• 職業簡介：配備高倍率戰術鏡與高穿透電磁步槍的遠程專家。\n初始屬性：❤️ 血量 115 | ⚔️ 攻擊 30 | 🛡️ 防禦 16 | ⚡ 速度 25", inline=False)
        embed.set_footer(text="請使用 /選擇身份 指令或點選下方選單來進行正式的職業身份綁定。")

        view = RoleSelectView()
        await ctx.send(embed=embed, view=view)

    @app_commands.command(name="選擇身份", description="選擇你的角色職業身份")
    async def select_role_cmd(self, interaction: discord.Interaction):
        view = RoleSelectView()
        await interaction.response.send_message("請點選下方選單選擇你的職業身份：", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Roles(bot))
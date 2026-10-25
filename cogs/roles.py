import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# 職業資料設定 (含初始數值與介紹)
CLASSES_DATA = {
    "駭客": {
        "description": "擅長系統干擾與遠程支援，具備高額單體輸出與輔助能力。",
        "hp": 90, "max_hp": 90, "mp": 80, "stamina": 100, "max_stamina": 100, "atk": 18, "def": 4,
        "emoji": "💻"
    },
    "磁暴重裝": {
        "description": "擁有極高的血量與防禦力，前線堅不可摧的重型坦克。",
        "hp": 150, "max_hp": 150, "mp": 30, "stamina": 100, "max_stamina": 100, "atk": 10, "def": 12,
        "emoji": "🛡️"
    },
    "異能覺醒": {
        "description": "掌控元素與精神能量，擁有龐大的魔力與毀滅性範圍傷害。",
        "hp": 80, "max_hp": 80, "mp": 120, "stamina": 100, "max_stamina": 100, "atk": 22, "def": 3,
        "emoji": "🔮"
    },
    "神射手": {
        "description": "精準的遠距離打擊者，擁有優秀的平衡輸出與高暴擊潛力。",
        "hp": 100, "max_hp": 100, "mp": 50, "stamina": 100, "max_stamina": 100, "atk": 16, "def": 6,
        "emoji": "🏹"
    }
}

class ClassSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=role_name,
                description=f"HP:{data['hp']} | MP:{data['mp']} | STA:{data['stamina']} | ATK:{data['atk']} | DEF:{data['def']}",
                emoji=data["emoji"]
            )
            for role_name, data in CLASSES_DATA.items()
        ]
        super().__init__(placeholder="選擇你的初期職業 (選擇後不可更換)...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected_role = self.values[0]
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. 檢查玩家是否已經選過職業
        cursor.execute("SELECT role FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()

        if player and player[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send(f"⚠️ 你已經綁定職業 **【{player[0]}】**，無法重複選擇或更換！", ephemeral=True)
            return

        # 2. 寫入/更新玩家職業與基礎數值（同時帶入 mp 與 max_mp）
        role_info = CLASSES_DATA[selected_role]
        cursor.execute("""
            INSERT INTO players (user_id, role, hp, max_hp, mp, max_mp, stamina, max_stamina, atk, def, gold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 30)
            ON CONFLICT(user_id) DO UPDATE SET
                role = excluded.role,
                hp = excluded.hp,
                max_hp = excluded.max_hp,
                mp = excluded.mp,
                max_mp = excluded.max_mp,
                stamina= excluded.stamina,
                max_stamina= excluded.max_stamina,
                atk = excluded.atk,
                def = excluded.def
        """, (
            user_id, selected_role, 
            role_info["hp"], role_info["max_hp"], 
            role_info["mp"], role_info["max_mp"],  # 將 mp 與 max_mp 同步設定為職業初始值
            role_info["stamina"], role_info["max_stamina"],
            role_info["atk"], role_info["def"]
        ))

        conn.commit()
        cursor.close()
        conn.close()

        # 3. 給予 Discord 身份組
        role_obj = discord.utils.get(interaction.guild.roles, name=selected_role)
        if role_obj:
            try:
                await interaction.user.add_roles(role_obj)
            except discord.Forbidden:
                pass

        embed = discord.Embed(
            title="🎉 【職業選擇成功】",
            description=f"恭喜你正式成為 **{role_info['emoji']} {selected_role}**！\n資料已綁定，祝你在冒險中一帆風順！",
            color=discord.Color.green()
        )
        embed.add_field(name="❤️ 生命值", value=f"`{role_info['hp']}/{role_info['max_hp']}`", inline=True)
        embed.add_field(name="💧 魔力值", value=f"`{role_info['mp']}/{role_info['mp']}`", inline=True)
        embed.add_field(name="⚔️ 攻擊力", value=f"`{role_info['atk']}`", inline=True)
        embed.add_field(name="🛡️ 防禦力", value=f"`{role_info['def']}`", inline=True)
        embed.add_field(name="⚡ 體力值", value=f"`{role_info['stamina']}/{role_info['max_stamina']}`", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

class ClassSelectView(discord.ui.View):
    def __init__(self, bot=None):
        super().__init__(timeout=None)
        self.add_item(ClassSelect())

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_roles", description="【管理員】發送職業介紹與選擇面板至頻道")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_roles(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚔️ 【冒險者職業選擇】",
            description="請仔細閱讀以下職業特性，並從下方下拉選單選擇你的職業。\n**⚠️ 注意：一旦選擇後即無法更改或重新選擇！**",
            color=discord.Color.gold()
        )

        for role_name, data in CLASSES_DATA.items():
            embed.add_field(
                name=f"{data['emoji']} {role_name}",
                value=f"• **描述**：{data['description']}\n"
                      f"• **基礎數值**：HP `{data['hp']}` | MP `{data['mp']}` | STA `{data['stamina']}` | ATK `{data['atk']}` | DEF `{data['def']}`",
                inline=False
            )

        await interaction.response.send_message(embed=embed, view=ClassSelectView())

    @setup_roles.error
    async def setup_roles_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ 只有管理員可以使用此指令設定職業面板！", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Roles(bot))
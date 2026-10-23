import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# 1. 定義四種職業的詳細介紹資料與專屬數值
ROLE_INFOS = {
    "駭客": {
        "title": "💻 駭客 (Hacker)",
        "desc": "擅長透過資訊戰與精密計算癱瘓敵人。擁有高靈活性與特殊戰術支援能力。",
        "stats": "❤️ 血量: 100 | ⚔️ 攻擊: 25 | 🛡️ 防禦: 10 | ⚡ 特色: 暴擊與戰術干擾",
        "hp": 100,
        "atk": 25,
        "def": 10,
        "color": discord.Color.blue()
    },
    "磁暴重裝": {
        "title": "🛡️ 磁暴重裝 (Magnetic Heavy Armor)",
        "desc": "身穿高強度合金重甲，操控磁場抵擋大量傷害。隊伍中最穩固的堅實壁壘。",
        "stats": "❤️ 血量: 180 | ⚔️ 攻擊: 18 | 🛡️ 防禦: 35 | ⚡ 特色: 超高防禦、承受反擊",
        "hp": 180,
        "atk": 18,
        "def": 35,
        "color": discord.Color.dark_embed()
    },
    "異能覺醒": {
        "title": "✨ 異能覺醒 (Awakened Esper)",
        "desc": "覺醒神祕的超自然能量，能夠釋放毀滅性的精神與能量波，對敵方造成巨額打擊。",
        "stats": "❤️ 血量: 110 | ⚔️ 攻擊: 35 | 🛡️ 防禦: 15 | ⚡ 特色: 高爆發傷害",
        "hp": 110,
        "atk": 35,
        "def": 15,
        "color": discord.Color.purple()
    },
    "神射手": {
        "title": "🎯 神射手 (Sharpshooter)",
        "desc": "百步穿楊的頂尖狙擊手，以極其敏銳的感官與致命的遠程攻擊將敵人瞬間擊潰。",
        "stats": "❤️ 血量: 100 | ⚔️ 攻擊: 30 | 🛡️ 防禦: 16 | ⚡ 特色: 穩定高額單體輸出",
        "hp": 100,
        "atk": 30,
        "def": 16,
        "color": discord.Color.green()
    }
}

# 2. 下拉選單檢視類別 (View)
class RoleSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # 永久有效，不會過期

    @discord.ui.select(
        placeholder="🔍 請選擇你想了解或加入的職業...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="駭客", description="檢視駭客職業介紹並加入", emoji="💻"),
            discord.SelectOption(label="磁暴重裝", description="檢視磁暴重裝職業介紹並加入", emoji="🛡️"),
            discord.SelectOption(label="異能覺醒", description="檢視異能覺醒職業介紹並加入", emoji="✨"),
            discord.SelectOption(label="神射手", description="檢視神射手職業介紹並加入", emoji="🎯"),
        ]
    )
    async def select_role_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        chosen_role = select.values[0]
        info = ROLE_INFOS[chosen_role]

        # 建立該職業的詳細介紹 Embed
        embed = discord.Embed(title=info["title"], description=info["desc"], color=info["color"])
        embed.add_field(name="📊 能力傾向", value=info["stats"], inline=False)
        embed.set_footer(text="點擊下方按鈕即可正式解鎖並選擇此職業！")

        # 附帶一個「確認選擇此職業」的按鈕
        view = ConfirmRoleView(chosen_role)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# 3. 確認選擇職業的按鈕
class ConfirmRoleView(discord.ui.View):
    def __init__(self, role_name: str):
        super().__init__(timeout=60)
        self.role_name = role_name

    @discord.ui.button(label="✅ 確認選擇此職業", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        guild = interaction.guild
        info = ROLE_INFOS[self.role_name]  # 👈 動態取得該職業專屬的數值 (hp, atk, def)

        # 檢查玩家是否已經選過職業
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()

        if player and player[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send(f"⚠️ 你已經選擇過職業（`{player[0]}`）了！無法重複選擇。", ephemeral=True)
            return

        # 修正：將寫死的 100, 100, 15, 8 替換為動態變數 info["hp"], info["atk"], info["def"]
        cursor.execute("""
            INSERT INTO players (user_id, role, hp, max_hp, mp, atk, def, gold)
            VALUES (?, ?, ?, ?, 50, ?, ?, 100)
            ON CONFLICT(user_id) DO UPDATE SET role = ?, hp = ?, max_hp = ?, atk = ?, def = ?
        """, (user_id, self.role_name, info["hp"], info["hp"], info["atk"], info["def"],
              self.role_name, info["hp"], info["hp"], info["atk"], info["def"]))
        
        conn.commit()
        cursor.close()
        conn.close()

        # 給予 Discord 身份組
        role_obj = discord.utils.get(guild.roles, name=self.role_name)
        if role_obj:
            try:
                await interaction.user.add_roles(role_obj)
            except discord.Forbidden:
                await interaction.followup.send("⚠️ 機器人權限不足以賦予身份組，請通知管理員檢查位階！", ephemeral=True)
                return

        await interaction.followup.send(
            f"🎉 恭喜你成功轉職成為 **{self.role_name}**！\n"
            f"初始血量：`{info['hp']}/{info['hp']}` | 攻擊力：`{info['atk']}` | 防禦力：`{info['def']}`\n"
            f"快使用 `/打怪` 開始冒險吧！", 
            ephemeral=True
        )


class RoleSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_roles", description="【管理員】發送職業介紹與選擇面板")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_roles(self, interaction: discord.Interaction):
        # 建立總覽介紹 Embed
        embed = discord.Embed(
            title="🌟 【 陣營職業介紹中心 】 🌟",
            description="歡迎來到末日世界！請在下方選單中深入了解各個職業的特性與定位，找到最適合你的戰鬥風格並完成轉職！\n\n*(提示：每個帳號僅能選擇一次職業，請謹慎決定)*",
            color=discord.Color.gold()
        )
        embed.add_field(name="💻 駭客", value="❤️ 血量: 100 | ⚔️ 攻擊: 25 | 🛡️ 防禦: 10", inline=False)
        embed.add_field(name="🛡️ 磁暴重裝", value="❤️ 血量: 180 | ⚔️ 攻擊: 18 | 🛡️ 防禦: 35", inline=False)
        embed.add_field(name="✨ 異能覺醒", value="❤️ 血量: 110 | ⚔️ 攻擊: 35 | 🛡️ 防禦: 15", inline=False)
        embed.add_field(name="🎯 神射手", value="❤️ 血量: 100 | ⚔️ 攻擊: 30 | 🛡️ 防禦: 16", inline=False)

        view = RoleSelectView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ 職業介紹面板已成功發送至此頻道！", ephemeral=True)

    @setup_roles.error
    async def setup_roles_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ 你沒有權限使用此指令！", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RoleSetup(bot))
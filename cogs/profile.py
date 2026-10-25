import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="屬性", description="查看自己的個人特務檔案與屬性數值")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 🛡️ 自動補上可能缺少的欄位，防止舊資料庫報錯
        columns_to_check = [
            ("role_name", "TEXT"),
            ("mp", "INTEGER DEFAULT 50"),
            ("max_mp", "INTEGER DEFAULT 50"),
            ("weapon_name", "TEXT"),
            ("weapon_atk", "INTEGER DEFAULT 0"),
            ("armor_name", "TEXT"),
            ("armor_def", "INTEGER DEFAULT 0")
        ]
        for col_name, col_type in columns_to_check:
            try:
                cursor.execute(f"ALTER TABLE players ADD COLUMN {col_name} {col_type};")
            except Exception:
                pass
        conn.commit()

        # 🔍 查詢玩家資料（包含 max_mp）
        cursor.execute("""
            SELECT role_name, hp, max_hp, atk, def, mp, max_mp, stamina, max_stamina, gold, 
                   weapon_name, weapon_atk, armor_name, armor_def 
            FROM players WHERE user_id = ?
        """, (interaction.user.id,))
        player = cursor.fetchone()

        if not player or not player[0]:
            cursor.close()
            conn.close()
            await interaction.followup.send("⚠️ 你尚未選擇身份！請先使用 `/setup_roles` 面板選擇職業。", ephemeral=True)
            return

        role_name, hp, max_hp, atk, player_def, mp, max_mp, stamina, max_stamina, gold, weapon_name, weapon_atk, armor_name, armor_def = player
        cursor.close()
        conn.close()

        # ⚔️ 計算總攻擊力與總防禦力（基礎數值 + 裝備加成）
        total_atk = atk + (weapon_atk or 0)
        total_def = player_def + (armor_def or 0)

        # 建立個人檔案 Embed
        embed = discord.Embed(
            title=f"📊 [{interaction.user.display_name} · 特務檔案]",
            color=discord.Color.green()
        )
        embed.add_field(name="🏷️ 當前職業", value=f"**{role_name}**", inline=False)
        embed.add_field(name="❤️ 生命值", value=f"{hp}/{max_hp}", inline=True)
        embed.add_field(name="💧 魔力值", value=f"{mp}/{max_mp}", inline=True)
        embed.add_field(name="⚡ 體力值", value=f"{stamina}/{max_stamina}", inline=True)
        embed.add_field(name="💰 金幣", value=f"{gold} G", inline=True)
        
        # 顯示總數值與詳細拆解
        embed.add_field(
            name="⚔️ 攻擊力 (ATK)", 
            value=f"總計：**`{total_atk}`**\n(基礎 `{atk}` + 武器 `+{weapon_atk or 0}`)", 
            inline=False
        )
        embed.add_field(
            name="🛡️ 防禦力 (DEF)", 
            value=f"總計：**`{total_def}`**\n(基礎 `{player_def}` + 防具 `+{armor_def or 0}`)", 
            inline=False
        )
        
        # 顯示目前穿戴的裝備
        embed.add_field(name="🗡️ 當前武器", value=f"`{weapon_name or '無'}`", inline=True)
        embed.add_field(name="🛡️ 當前防具", value=f"`{armor_name or '無'}`", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Status(bot))
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection  # 引入雲端資料庫連線模組

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="屬性", description="查看你的個人特務檔案與當前屬性")
    async def profile(self, interaction: discord.Interaction):
        conn = get_db_connection()
        cursor = conn.cursor()

        # 確保玩家表格存在 (PostgreSQL 語法)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id BIGINT PRIMARY KEY,
                role TEXT,
                hp INTEGER DEFAULT 100,
                max_hp INTEGER DEFAULT 100,
                atk INTEGER DEFAULT 25,
                def INTEGER DEFAULT 10,
                speed INTEGER DEFAULT 20,
                gold INTEGER DEFAULT 100
            )
        """)
        conn.commit()

        # 查詢玩家資料 (使用 %s 佔位符)
        cursor.execute("SELECT role, hp, max_hp, atk, def, speed, gold FROM players WHERE user_id = %s", (interaction.user.id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result or not result[0]:
            role = "未選擇"
            hp, max_hp, atk, def_val, speed, gold = 100, 100, 25, 10, 20, 100
        else:
            role, hp, max_hp, atk, def_val, speed, gold = result

        embed = discord.Embed(
            title=f"📊 [{interaction.user.name} · 特務檔案]",
            color=discord.Color.green()
        )
        embed.add_field(name="🏷️ 當前職業", value=f"**{role}**", inline=False)
        embed.add_field(name="❤️ 生命值 (HP)", value=f"{hp}/{max_hp}", inline=True)
        embed.add_field(name="⚔️ 攻擊力", value=f"{atk}", inline=True)
        embed.add_field(name="🛡️ 防禦力", value=f"{def_val}", inline=True)
        embed.add_field(name="⚡ 速度", value=f"{speed}", inline=True)
        embed.add_field(name="💰 金幣資產", value=f"{gold} G", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Profile(bot))
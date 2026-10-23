import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection, use_item_in_db, open_chest_in_db

class Bag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bag", description="查看你的隨身背包與道具")
    async def bag(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (interaction.user.id,))
            items = cursor.fetchall()
            cursor.close()
            conn.close()

            embed = discord.Embed(
                title=f"📦 [{interaction.user.display_name} · 隨身背包]",
                color=discord.Color.blue()
            )

            if not items:
                embed.description = "你的背包空空如也..."
            else:
                desc_list = []
                for item_name, qty in items:
                    if "寶箱" in item_name:
                        desc_list.append(f"🎁 **{item_name}** x `{qty}` （可使用 `/open_chest` 開啟）")
                    elif "【" in item_name:
                        desc_list.append(f"⚔️ **{item_name}** x `{qty}`")
                    else:
                        desc_list.append(f"• **{item_name}** x `{qty}`")
                embed.description = "\n".join(desc_list)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ 發生錯誤：`{e}`", ephemeral=True)

    @app_commands.command(name="open_chest", description="開啟背包中的神秘寶箱獲得裝備")
    async def open_chest(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            res = open_chest_in_db(interaction.user.id)
            if not res[0]:
                await interaction.followup.send(res[1], ephemeral=True)
                return

            success, msg, item_name, item_type, bonus, quality = res
            
            # 依品質決定 Embed 顏色
            color = discord.Color.blue()
            if "稀有" in quality:
                color = discord.Color.blue()
            elif "史詩" in quality:
                color = discord.Color.purple()
            elif "傳說" in quality:
                color = discord.Color.gold()

            embed = discord.Embed(title="🎁 【寶箱開啟成功】", description=msg, color=color)
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ 開啟寶箱時發生錯誤：`{e}`", ephemeral=True)

    @app_commands.command(name="use", description="使用背包中的消耗道具（例如：生命藥水）")
    @app_commands.describe(item_name="要使用的道具名稱")
    async def use_item(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.defer(ephemeral=True)

        try:
            success, msg = use_item_in_db(interaction.user.id, item_name)
            
            if success:
                embed = discord.Embed(title="📦 【道具使用成功】", description=msg, color=discord.Color.green())
            else:
                embed = discord.Embed(title="⚠️ 【道具使用失敗】", description=msg, color=discord.Color.orange())
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ 發生未預期的錯誤：`{e}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Bag(bot))
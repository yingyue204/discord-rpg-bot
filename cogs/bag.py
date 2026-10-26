import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="背包", description="查看你的個人背包與道具")
    async def inventory(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ?", (user_id,))
        items = cursor.fetchall()

        cursor.execute("SELECT gold, weapon_atk, armor_def FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        cursor.close()
        conn.close()

        if not player:
            await interaction.followup.send("⚠️ 請先建立角色！", ephemeral=True)
            return

        desc = f"💰 **持有金幣**：`{player['gold']} G`\n⚔️ **裝備加成**：攻擊 `+{player['weapon_atk'] or 0}` | 防禦 `+{player['armor_def'] or 0}`\n\n📦 **【背包物品】**\n"
        if items:
            for item in items:
                desc += f"- **{item['item_name']}** x `{item['quantity']}`\n"
        else:
            desc += "*(背包目前空空如也)*"

        embed = discord.Embed(title="🎒 【冒險者背包】", description=desc, color=discord.Color.purple())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="使用道具", description="使用背包中的藥水、急救包或開啟神秘寶箱")
    @app_commands.rename(item_name="道具名稱")
    async def use_item(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()

        # 檢查背包是否有此道具
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        inv = cursor.fetchone()
        if not inv or inv["quantity"] <= 0:
            cursor.close()
            conn.close()
            await interaction.followup.send(f"❌ 你的背包中沒有 **{item_name}**！", ephemeral=True)
            return

        cursor.execute("SELECT hp, max_hp, mp FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        hp, max_hp, mp = player["hp"], player["max_hp"], player["mp"]

        msg = ""
        if item_name == "生命藥水":
            new_hp = min(max_hp, hp + 30)
            cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
            msg = f"🧪 使用了 **生命藥水**，恢復了 30 點生命值（當前血量：`{new_hp}/{max_hp}`）。"
        elif item_name == "急救包":
            new_hp = min(max_hp, hp + 50)
            cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
            msg = f"🩹 使用了 **急救包**，恢復了 50 點生命值（當前血量：`{new_hp}/{max_hp}`）。"
        elif item_name == "魔力藥水":
            new_mp = mp + 20
            cursor.execute("UPDATE players SET mp = ? WHERE user_id = ?", (new_mp, user_id))
            msg = f"💧 使用了 **魔力藥水**，恢復了 20 點魔力（當前魔力：`{new_mp}`）。"
        elif item_name == "能量飲料":
            new_mp = mp + 40
            cursor.execute("UPDATE players SET mp = ? WHERE user_id = ?", (new_mp, user_id))
            msg = f"⚡ 使用了 **能量飲料**，恢復了 40 點魔力（當前魔力：`{new_mp}`）。"
        else:
            cursor.close()
            conn.close()
            await interaction.followup.send(f"⚠️ **{item_name}** 無法直接使用！", ephemeral=True)
            return

        # 消耗一個道具
        new_qty = inv["quantity"] - 1
        if new_qty <= 0:
            cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        else:
            cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))

        conn.commit()
        cursor.close()
        conn.close()

        await interaction.followup.send(f"✅ {msg}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Inventory(bot))
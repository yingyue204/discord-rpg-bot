import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

# 🐾 可領養的寵物資料
AVAILABLE_PETS = {
    "小狗": {"cost": 500, "desc": "忠誠可靠，擁有敏銳的尋寶嗅覺。"},
    "小貓": {"cost": 500, "desc": "靈巧優雅，為主人帶來幸運。"},
    "兔兔": {"cost": 400, "desc": "溫馴可愛，療癒系的生活良伴。"}
}

class PetClinic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="我的寵物", description="查看你目前領養的寵物狀態、飽足感與健康狀況")
    async def view_pet(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT pet_name, pet_type, hunger, status FROM pets WHERE user_id = ?", (user_id,))
            pets = cursor.fetchall()

            if not pets:
                await interaction.followup.send("📭 你還沒有領養任何寵物！快去使用 `/領養寵物` 帶一隻回家吧。", ephemeral=True)
                return

            desc = "🏡 **你的溫馨寵物之家**：\n\n"
            for p in pets:
                name, ptype, hunger, status = p["pet_name"], p["pet_type"], p["hunger"], p["status"]
                status_emoji = "🟢" if status == "健康" else "🔴"
                desc += f"• 🐾 **{name}** ({ptype})\n  └ 狀態：{status_emoji} **{status}** | 飽足感：`{hunger}/100`\n\n"

            embed = discord.Embed(
                title="🐾 【寵物管理中心】",
                description=desc,
                color=discord.Color.from_rgb(255, 182, 193)
            )
            embed.set_footer(text="💡 使用 /餵食寵物 或 /寵物診所 來照顧牠們！")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ 發生錯誤: `{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

    @app_commands.command(name="領養寵物", description="在寵物店領養一隻屬於你的可愛寵物")
    @app_commands.rename(pet_type="寵物種類", pet_name="寵物名字")
    @app_commands.describe(pet_type="選擇想要領養的寵物", pet_name="為你的新夥伴取個好名字吧！")
    @app_commands.choices(pet_type=[
        app_commands.Choice(name="🐶 小狗 (500 G)", value="小狗"),
        app_commands.Choice(name="🐱 小貓 (500 G)", value="小貓"),
        app_commands.Choice(name="🐰 兔兔 (400 G)", value="兔兔")
    ])
    async def adopt_pet(self, interaction: discord.Interaction, pet_type: str, pet_name: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        cost = AVAILABLE_PETS[pet_type]["cost"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 檢查金幣
            cursor.execute("SELECT gold FROM players WHERE user_id = ?", (user_id,))
            player = cursor.fetchone()
            if not player or player["gold"] < cost:
                await interaction.followup.send(f"❌ 領養 **{pet_type}** 需要 `{cost} G`，你的金幣不足！", ephemeral=True)
                return

            # 檢查該名字是否已被使用
            cursor.execute("SELECT * FROM pets WHERE user_id = ? AND pet_name = ?", (user_id, pet_name))
            if cursor.fetchone():
                await interaction.followup.send(f"⚠️ 你已經有一隻叫做 **{pet_name}** 的寵物了，請換個名字！", ephemeral=True)
                return

            # 扣款並新增寵物
            cursor.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (cost, user_id))
            cursor.execute("""
                INSERT INTO pets (user_id, pet_name, pet_type, hunger, status)
                VALUES (?, ?, ?, 100, '健康')
            """, (user_id, pet_name, pet_type))
            conn.commit()

            embed = discord.Embed(
                title="🎉 【領養成功！】",
                description=f"恭喜你成功領養了 **{pet_type}**，並為牠取名叫 **{pet_name}**！\n\n好好照顧牠、定時餵食，牠會成為你冒險路上的最佳夥伴！",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            conn.rollback()
            await interaction.followup.send(f"❌ 領養過程發生錯誤: `{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

    @app_commands.command(name="餵食寵物", description="消耗 1 個「寵物飼料」來餵食你的寵物，恢復飽足感")
    @app_commands.rename(pet_name="寵物名字")
    @app_commands.describe(pet_name="你想餵食的寵物名字")
    async def feed_pet(self, interaction: discord.Interaction, pet_name: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 1. 檢查寵物是否存在
            cursor.execute("SELECT * FROM pets WHERE user_id = ? AND pet_name = ?", (user_id, pet_name))
            pet = cursor.fetchone()
            if not pet:
                await interaction.followup.send(f"⚠️ 找不到叫做 **{pet_name}** 的寵物！", ephemeral=True)
                return

            # 2. 檢查背包有沒有「寵物飼料」
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, "寵物飼料"))
            inv = cursor.fetchone()
            if not inv or inv["quantity"] <= 0:
                await interaction.followup.send("❌ 你的背包裡沒有【寵物飼料】！請先前往 `/系統商店` 購買。", ephemeral=True)
                return

            # 3. 扣除飼料並增加飽足感
            cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, "寵物飼料"))
            
            new_hunger = min(100, pet["hunger"] + 35)
            # 如果餵食時飽足感過低，有機會把「生病」狀態治癒或保持健康
            new_status = "健康" if pet["status"] == "生病" and new_hunger > 50 else pet["status"]

            cursor.execute("UPDATE pets SET hunger = ?, status = ? WHERE user_id = ? AND pet_name = ?", 
                           (new_hunger, new_status, user_id, pet_name))
            conn.commit()

            embed = discord.Embed(
                title="🍖 【餵食成功】",
                description=f"你餵食了 **{pet_name}**！\n\n• 飽足感：`{pet['hunger']}` ➔ `{new_hunger}/100`\n• 目前狀態：**{new_status}**",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            conn.rollback()
            await interaction.followup.send(f"❌ 餵食過程發生錯誤: `{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

    @app_commands.command(name="寵物診所", description="帶生病的寵物前往診所治療，恢復健康")
    @app_commands.rename(pet_name="寵物名字")
    @app_commands.describe(pet_name="需要看診的寵物名字")
    async def pet_clinic(self, interaction: discord.Interaction, pet_name: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        cure_cost = 100  # 診察費 100 G

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 1. 檢查寵物狀態
            cursor.execute("SELECT * FROM pets WHERE user_id = ? AND pet_name = ?", (user_id, pet_name))
            pet = cursor.fetchone()
            if not pet:
                await interaction.followup.send(f"⚠️ 找不到叫做 **{pet_name}** 的寵物！", ephemeral=True)
                return

            if pet["status"] == "健康":
                await interaction.followup.send(f"💚 **{pet_name}** 目前非常健康，不需要去看醫生！", ephemeral=True)
                return

            # 2. 檢查金幣
            cursor.execute("SELECT gold FROM players WHERE user_id = ?", (user_id,))
            player = cursor.fetchone()
            if not player or player["gold"] < cure_cost:
                await interaction.followup.send(f"❌ 寵物醫療費需要 `{cure_cost} G`，你的金幣不足！", ephemeral=True)
                return

            # 3. 扣款並治癒寵物
            cursor.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (cure_cost, user_id))
            cursor.execute("UPDATE pets SET status = '健康' WHERE user_id = ? AND pet_name = ?", (user_id, pet_name))
            conn.commit()

            embed = discord.Embed(
                title="🏥 【寵物診所治療成功】",
                description=f"經過獸醫的悉心診治與注射特效藥，**{pet_name}** 已經恢復健康了！\n\n💸 支付醫療費：`-100 G`",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            conn.rollback()
            await interaction.followup.send(f"❌ 看診過程發生錯誤: `{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

async def setup(bot):
    await bot.add_cog(PetClinic(bot))
import discord
from discord.ext import commands
from discord import app_commands
from db import RECIPE_DATABASE, cook_recipe_in_db, upgrade_cooking_station_in_db, get_db_connection

# 🌟 1. 料理下拉選單元件
class RecipeSelect(discord.ui.Select):
    def __init__(self):
        options = []
        # 從 db.py 匯入完整的 21 道食譜資料庫
        for name, data in RECIPE_DATABASE.items():
            ing_str = ", ".join([f"{k}x{v}" for k, v in data["ingredients"].items()])
            desc = f"[Lv.{data['station_level']}] 需求: {ing_str}"
            if len(desc) > 100:  # Discord 規定說明文字最多 100 字元
                desc = desc[:97] + "..."
            
            options.append(discord.SelectOption(
                label=name, 
                description=desc, 
                value=name
            ))
        
        super().__init__(
            placeholder="🍳 請選擇想要烹調的美味料理...", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            recipe_name = self.values[0]
            # 呼叫資料庫執行製作邏輯
            success, msg = cook_recipe_in_db(interaction.user.id, recipe_name)
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ 製作過程發生例外錯誤：`{e}`", ephemeral=True)


# 🌟 2. 包含下拉選單與升級按鈕的介面 View
class CookView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)  # 3分鐘無操作後按鈕失效
        self.add_item(RecipeSelect())

    @discord.ui.button(label="🔨 升級料理台", style=discord.ButtonStyle.green, row=1)
    async def upgrade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            success, msg = upgrade_cooking_station_in_db(interaction.user.id)
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ 升級過程發生例外錯誤：`{e}`", ephemeral=True)


# 🌟 3. 料理 Cog 主體
class Cook(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="料理台", description="開啟互動式料理工坊，直接製作料理或升級")
    async def cooking_station(self, interaction: discord.Interaction):
        # 確保第一時間回應 defer，防止 Discord 逾時
        await interaction.response.defer(ephemeral=True)
        
        level = 1
        gold = 0
        
        # 安全讀取玩家資料
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT cooking_level, gold FROM players WHERE user_id = ?", (interaction.user.id,))
            player = cursor.fetchone()
            if player:
                level = player["cooking_level"] or 1
                gold = player["gold"] or 0
        except Exception as e:
            print(f"❌ 讀取玩家料理台資料錯誤: {e}")
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

        embed = discord.Embed(
            title="🍳 【互動式料理工坊】",
            description=f"目前料理台等級：**Lv.{level}** | 擁有金幣：`{gold} G`\n\n👇 **請從下方下拉選單中直接選擇想製作的料理，或點擊按鈕升級！**",
            color=discord.Color.orange()
        )

        view = CookView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Cook(bot))
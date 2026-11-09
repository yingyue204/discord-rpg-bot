import asyncio
import random
import traceback
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection

FISHING_SPOTS = {
    "新手河畔": {
        "description": "平靜的河岸，適合初學者練習釣魚，偶爾能釣到廢棄物。",
        "stamina": 10,
        "drops": [
            ("小魚", 50),
            ("草魚", 30),
            ("廢鐵罐", 20)
        ]
    },
    "神祕湖泊": {
        "description": "深不見底的湖泊，水質清澈，棲息著較為珍貴的魚類。",
        "stamina": 20,
        "drops": [
            ("草魚", 40),
            ("鮭魚", 35),
            ("黃金鯉魚", 15),
            ("神祕寶箱", 10)
        ]
    },
    "深海漁場": {
        "description": "波濤洶湧的深海，充滿未知與高級漁獲，對體力消耗極大！",
        "stamina": 35,
        "drops": [
            ("鮭魚", 30),
            ("黃金鯉魚", 30),
            ("深海巨魷", 25),
            ("神祕寶箱", 15)
        ]
    }
}

class IdentityVCalibrationView(discord.ui.View):
    def __init__(self, user_id, spot_name, caught_item, stamina_cost):
        super().__init__(timeout=5.0)
        self.user_id = user_id
        self.spot_name = spot_name
        self.caught_item = caught_item
        self.stamina_cost = stamina_cost
        
        self.message = None
        self.green_zones = [4, 5, 6]
        
        self.pointer_pos = 1
        self.direction = 1

    def render_bar(self):
        bar = ""
        for i in range(1, 11):
            if i == self.pointer_pos:
                bar += "📍"
            elif i in self.green_zones:
                bar += "🟩"
            else:
                bar += "⬛"
        return f"`[{bar}]`"

    @discord.ui.button(label="🎯 點擊校準！", style=discord.ButtonStyle.danger)
    async def click_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的釣竿！", ephemeral=True)
            return

        if self.is_finished():
            return

        self.stop()

        await interaction.response.defer()

        success = self.pointer_pos in self.green_zones

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            for child in self.children:
                child.disabled = True

            cursor.execute("UPDATE players SET stamina = stamina - ?, rod_durability = rod_durability - 1 WHERE user_id = ?", (self.stamina_cost, self.user_id))

            if not success:
                conn.commit()
                embed = discord.Embed(
                    title="❌ 【校準失敗·魚兒脫鉤】",
                    description=f"指針停在了錯誤的位置（格數 `{self.pointer_pos}`）！你錯過了綠色區域，魚線斷裂，魚逃跑了...\n⚠️ **魚竿耐久度 `-1`**",
                    color=discord.Color.red()
                )
                button.label = "💥 脫鉤失敗"
                button.style = discord.ButtonStyle.secondary
                await interaction.edit_original_response(embed=embed, view=self)
                return

            cursor.execute("SELECT COUNT(*) as slots FROM inventory WHERE user_id = ? AND quantity > 0", (self.user_id,))
            current_slots = cursor.fetchone()["slots"]

            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, self.caught_item))
            inv_row = cursor.fetchone()

            cursor.execute("SELECT max_bag_slots FROM players WHERE user_id = ?", (self.user_id,))
            player_row = cursor.fetchone()
            max_slots = player_row["max_bag_slots"] if player_row and "max_bag_slots" in player_row.keys() and player_row["max_bag_slots"] else 20

            if not inv_row and current_slots >= max_slots:
                conn.commit()
                embed = discord.Embed(
                    title="⚠️ 【背包空間已滿】",
                    description=f"你成功釣起了 **{self.caught_item}**，但隨身背包已滿 (`{current_slots}/{max_slots}` 格)，魚又被放回水裡了！\n💡 請先使用 `/存入倉庫` 整理背包。",
                    color=discord.Color.orange()
                )
                button.label = "🎒 背包滿"
                await interaction.edit_original_response(embed=embed, view=self)
                return

            give_qty = 1
            if inv_row:
                cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?", (give_qty, self.user_id, self.caught_item))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (self.user_id, self.caught_item))

            found_gold = random.randint(5, 15) if self.caught_item == "廢鐵罐" else 0
            if found_gold > 0:
                cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (found_gold, self.user_id))

            conn.commit()

            button.label = "✨ 校準成功！"
            button.style = discord.ButtonStyle.success

            embed = discord.Embed(
                title="🎉 【校準成功！釣魚成功】",
                description=f"你在綠色判定區精準按下了按鈕！成功從 **{self.spot_name}** 釣起了寶貝。\n\n"
                            f"🎚️ **最終指針位置**：{self.render_bar()}\n"
                            f"🎁 獲得產物：**{self.caught_item}** x `{give_qty}`\n"
                            f"🛠️ **魚竿耐久度 `-1`**",
                color=discord.Color.green()
            )
            if found_gold > 0:
                embed.add_field(name="💰 意外發現", value=f"在廢鐵罐裡找到了 **+{found_gold} G**！", inline=False)

            await interaction.edit_original_response(embed=embed, view=self)

        except Exception as e:
            traceback.print_exc()
            conn.rollback()
            try:
                await interaction.followup.send(f"❌ 發生錯誤：`{e}`", ephemeral=True)
            except:
                pass
        finally:
            cursor.close()
            conn.close()

    async def on_timeout(self):
        if not self.is_finished():
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE players SET stamina = stamina - ?, rod_durability = max(0, rod_durability - 1) WHERE user_id = ?", (self.stamina_cost, self.user_id))
                conn.commit()
            except:
                pass
            finally:
                cursor.close()
                conn.close()

            for child in self.children:
                child.disabled = True
                child.label = "⌛ 超時未按 (脫鉤)"
                child.style = discord.ButtonStyle.secondary

            embed = discord.Embed(
                title="❌ 【校準超時·魚兒逃跑】",
                description="太慢了！你猶豫不決，指針晃出界外，魚咬破魚線逃走了...\n⚠️ **魚竿耐久度 `-1`**",
                color=discord.Color.red()
            )
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except:
                    pass

class Fish(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def start_pointer_animation(self, view):
        try:
            while not view.is_finished():
                await asyncio.sleep(0.4)
                if view.is_finished():
                    break

                view.pointer_pos += view.direction
                if view.pointer_pos >= 10:
                    view.direction = -1
                elif view.pointer_pos <= 1:
                    view.direction = 1

                if view.message:
                    embed = view.message.embeds[0]
                    embed.description = f"水面傳來劇烈波動，大魚正在掙扎！\n\n" \
                                        f"🎚️ **校準進度條**：{view.render_bar()}\n" \
                                        f"⚠️ **請在指針（📍）移動到綠色區域（🟩）時按下下方按鈕！**"
                    try:
                        await view.message.edit(embed=embed, view=view)
                    except:
                        break
        except Exception:
            pass

    @app_commands.command(name="釣魚", description="前往指定的釣魚場揮竿釣魚，進行第五人格風格校準 QTE")
    @app_commands.rename(spot="釣魚地點")
    @app_commands.choices(spot=[
        app_commands.Choice(name="新手河畔 (消耗 10 體力)", value="新手河畔"),
        app_commands.Choice(name="神祕湖泊 (消耗 20 體力)", value="神祕湖泊"),
        app_commands.Choice(name="深海漁場 (消耗 35 體力)", value="深海漁場")
    ])
    @app_commands.describe(spot="你想前往的釣魚地點")
    async def fish(self, interaction: discord.Interaction, spot: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT hp, stamina, max_stamina, rod_durability FROM players WHERE user_id = ?", (user_id,))
            player = cursor.fetchone()

            if not player:
                await interaction.followup.send("⚠️ 你尚未建立角色！請先使用 `/setup_roles` 選擇職業。", ephemeral=True)
                return

            hp, stamina, max_stamina, rod_durability = player

            if rod_durability is None:
                rod_durability = 20
                cursor.execute("UPDATE players SET rod_durability = 20 WHERE user_id = ?", (user_id,))
                conn.commit()

            if hp <= 0:
                await interaction.followup.send("⚠️ 你目前處於倒地狀態，無法釣魚！請先前往診所治療。", ephemeral=True)
                return

            if rod_durability <= 0:
                embed = discord.Embed(
                    title="🎣 【魚竿已損壞】",
                    description=f"你的釣魚竿耐久度已經耗盡 (`0/20`)，無法繼續揮竿！\n\n💡 請前往商店購買新魚竿或使用修復工具。",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            spot_info = FISHING_SPOTS.get(spot, FISHING_SPOTS["新手河畔"])
            cost = spot_info["stamina"]

            if stamina < cost:
                embed = discord.Embed(
                    title="⚡ 【體力耗盡】",
                    description=f"你的體力不足以支撐這次釣魚！\n當前體力：`{stamina}/{max_stamina}` (需要 `{cost}` 點)\n\n💡 請先食用食物或透過莊園休息來恢復體力！",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            items, weights = zip(*spot_info["drops"])
            caught_item = random.choices(items, weights=weights, k=1)[0]

            embed = discord.Embed(
                title=f"🎣 【{spot}·注意校準！】",
                description=f"水面傳來劇烈波動，大魚正在掙扎！\n\n"
                            f"🎚️ **校準進度條**：等待指針開始晃動...\n"
                            f"🛠️ **當前魚竿耐久**：`{rod_durability}/20`\n"
                            f"⚠️ **請在指針（📍）移動到綠色區域（🟩）時按下下方按鈕！**",
                color=discord.Color.blue()
            )

            view = IdentityVCalibrationView(user_id, spot, caught_item, cost)
            sent_message = await interaction.followup.send(embed=embed, view=view, wait=True)
            view.message = sent_message

            # 啟動指針晃動動畫
            asyncio.create_task(self.start_pointer_animation(view))

        except Exception as e:
            traceback.print_exc()
            conn.rollback()
            await interaction.followup.send(f"❌ 釣魚過程發生錯誤：`{e}`", ephemeral=True)
        finally:
            cursor.close()
            conn.close()

async def setup(bot):
    await bot.add_cog(Fish(bot))
import discord
from discord.ext import commands
from discord import app_commands
from db import get_db_connection, RECIPE_DATABASE, COOKING_STATION_UPGRADE_COST

class RecipeSelect(discord.ui.Select):
    def __init__(self, user_id, station_level, unlocked_recipes):
        self.user_id = user_id
        options = []

        # 將 21 道食譜加入下拉選單
        for name, data in RECIPE_DATABASE.items():
            # 檢查是否可製作
            is_unlocked = (name in unlocked_recipes) or (data["station_level"] <= 1)
            is_level_enough = station_level >= data["station_level"]
            
            emoji = "🍳" if (is_unlocked and is_level_enough) else "🔒"
            desc = f"需求台階: Lv.{data['station_level']} | 產出: {data['output']}"
            
            options.append(
                discord.SelectOption(
                    label=name,
                    value=name,
                    description=desc[:100], # Discord 限制描述 100 字元內
                    emoji=emoji
                )
            )

        super().__init__(placeholder="👉 點擊此處選擇想要烹調的料理...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⚠️ 這不是你的料理台！", ephemeral=True)
            return

        recipe_name = self.values[0]
        recipe = RECIPE_DATABASE[recipe_name]

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. 檢查料理台等級
        cursor.execute("SELECT cooking_level FROM players WHERE user_id = ?", (self.user_id,))
        player_row = cursor.fetchone()
        station_level = player_row["cooking_level"] if player_row else 1

        if station_level < recipe["station_level"]:
            cursor.close()
            conn.close()
            await interaction.response.send_message(f"❌ 你的料理台等級不足！製作 **{recipe_name}** 需要 **Lv.{recipe['station_level']}** 料理台。", ephemeral=True)
            return

        # 2. 檢查背包材料是否充足
        missing_items = []
        for item_name, req_qty in recipe["ingredients"].items():
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (self.user_id, item_name))
            inv_row = cursor.fetchone()
            has_qty = inv_row["quantity"] if inv_row else 0
            if has_qty < req_qty:
                missing_items.append(f"**{item_name}** (需求: {req_qty}, 擁有: {has_qty})")

        if missing_items:
            cursor.close()
            conn.close()
            missing_str = ", ".join(missing_items)
            await interaction.response.send_
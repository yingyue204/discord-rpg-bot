import sqlite3
import time
import random

def get_db_connection():
    conn = sqlite3.connect("bot.db", timeout=20)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# 初始化資料庫與所有表格
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 建立玩家檔案表格（包含 last_mp_update 欄位）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                role TEXT,
                hp INTEGER,
                max_hp INTEGER,
                mp INTEGER,
                max_mp INTEGER,
                atk INTEGER,
                def INTEGER,
                gold INTEGER,
                weapon_name TEXT,
                weapon_atk INTEGER,
                armor_name TEXT,
                armor_def INTEGER,
                last_mp_update INTEGER DEFAULT 0
            )
        """)

        # 2. 建立背包表格
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER,
                PRIMARY KEY (user_id, item_name)
            )
        """)
        
        conn.commit()

        # 3. 防呆機制：如果舊資料庫沒有 last_mp_update 欄位，自動幫它補上
        try:
            cursor.execute("ALTER TABLE players ADD COLUMN last_mp_update INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass # 欄位已存在時會直接略過

    finally:
        cursor.close()
        conn.close()

# 🔄 自動計算並更新玩家自然回魔
def update_and_get_mp(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT mp, max_mp, last_mp_update FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        
        if not player:
            return 0, 50
            
        mp, max_mp, last_update = player[0] or 0, player[1] or 50, player[2] or 0
        now = int(time.time())
        
        if last_update == 0:
            cursor.execute("UPDATE players SET last_mp_update = ? WHERE user_id = ?", (now, user_id))
            conn.commit()
            return mp, max_mp
            
        passed_minutes = (now - last_update) // 60
        
        if passed_minutes > 0 and mp < max_mp:
            recovered_mp = passed_minutes * 5
            new_mp = min(max_mp, mp + recovered_mp)
            new_last_update = last_update + (passed_minutes * 60)
            
            cursor.execute("UPDATE players SET mp = ?, last_mp_update = ? WHERE user_id = ?", (new_mp, new_last_update, user_id))
            conn.commit()
            mp = new_mp
            
        return mp, max_mp
    finally:
        cursor.close()
        conn.close()

# ⚡ 消耗 MP 時同步更新時間戳記
def consume_mp(user_id: int, cost: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        now = int(time.time())
        cursor.execute("UPDATE players SET mp = mp - ?, last_mp_update = ? WHERE user_id = ?", (cost, now, user_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# 🎁 開啟神秘寶箱邏輯
def open_chest_in_db(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 檢查玩家背包是否有「神秘寶箱」
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = '神秘寶箱'", (user_id,))
        item = cursor.fetchone()

        if not item or item[0] <= 0:
            return False, "你的背包裡沒有 **神秘寶箱**！", None, None, None, None

        # 2. 扣除或刪除一個寶箱
        if item[0] > 1:
            cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = '神秘寶箱'", (user_id,))
        else:
            cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = '神秘寶箱'", (user_id,))

        # 3. 隨機決定品質 (白、藍、紫、金)
        quality_roll = random.random()
        if quality_roll < 0.60:
            prefix = "普通"
            quality = "⚪ 普通"
        elif quality_roll < 0.85:
            prefix = "精良"
            quality = "🔵 精良"
        elif quality_roll < 0.97:
            prefix = "史詩"
            quality = "🟣 史詩"
        else:
            prefix = "傳說級"
            quality = "🟡 傳說級"

        # 4. 隨機決定是武器還是防具，並從 EQUIPMENT_DATABASE 中選出對應名稱
        is_weapon = random.choice([True, False])

        if is_weapon:
            item_type = "weapon"
            # 根據品質隨機挑選該品質的武器基礎名稱
            if prefix == "傳說級":
                weapon_bases = ["終焉光束劍", "毀滅重型巨斧"]
            else:
                weapon_bases = ["高震動短刀", "光束劍", "電磁打擊槍", "重型巨斧"]
            
            chosen_base = random.choice(weapon_bases)
            item_name = f"【{prefix}】{chosen_base}"
        else:
            item_type = "armor"
            # 根據品質隨機挑選該品質的防具基礎名稱
            if prefix == "傳說級":
                armor_bases = ["泰坦合金重裝", "脈衝防衛力場"]
            else:
                armor_bases = ["戰術護甲", "納米防護服", "合金重盾", "外骨骼裝甲"]
                
            chosen_base = random.choice(armor_bases)
            item_name = f"【{prefix}】{chosen_base}"

        # 5. 🎯 直接從集中管理的 EQUIPMENT_DATABASE 查表取得絕對正確的 bonus 數值
        if item_name in EQUIPMENT_DATABASE:
            bonus = EQUIPMENT_DATABASE[item_name]["bonus"]
        else:
            # 防呆保底（若名稱不小心拼錯時的預設值）
            bonus = 10 

        # 6. 將開出來的裝備放入背包
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, item_name))

        conn.commit()
        
        stat_label = "攻擊力加成 (ATK)" if item_type == "weapon" else "防禦力加成 (DEF)"
        msg = f"🎉 成功開啟 **神秘寶箱**！\n獲得裝備：**{item_name}**（品質：{quality}）\n⚔️ **{stat_label}**：`+{bonus}`\n💡 輸入 `/equip item_name:{item_name}` 即可裝備！"
        
        return True, msg, item_name, item_type, bonus, quality
    finally:
        cursor.close()
        conn.close()

# 🛡️ 穿戴裝備邏輯
def equip_item_in_db(user_id: int, item_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 檢查背包是否有此裝備
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        item = cursor.fetchone()
        if not item or item[0] <= 0:
            return False, "❌ 你的背包裡沒有這個道具！"

        # 2. 判斷是武器還是防具，並計算數值
        # 依據名稱中的品質給予固定加成：普通(+8/+5)、精良(+15/+10)、史詩(+25/+18)、傳說級(+40/+30)
        if "光束劍" in item_name or "高振動短刀" in item_name or "電磁打擊槍" in item_name or "重型巨斧" in item_name:
            is_weapon = True
            if "普通" in item_name: atk_bonus = 8
            elif "精良" in item_name: atk_bonus = 15
            elif "史詩" in item_name: atk_bonus = 25
            elif "傳說級" in item_name: atk_bonus = 40
            else: atk_bonus = 5
        elif "戰術護甲" in item_name or "納米防護服" in item_name or "合金重盾" in item_name or "外骨骼裝甲" in item_name:
            is_weapon = False
            if "普通" in item_name: def_bonus = 5
            elif "精良" in item_name: def_bonus = 10
            elif "史詩" in item_name: def_bonus = 18
            elif "傳說級" in item_name: def_bonus = 30
            else: def_bonus = 3
        else:
            return False, "❌ 這個道具不是裝備，無法穿戴！"

        # 3. 處理裝備對調（若原本有裝備，需放回背包或直接覆蓋。這裡設計為：解除舊裝備回背包，裝上新裝備）
        cursor.execute("SELECT weapon_name, armor_name FROM players WHERE user_id = ?", (user_id,))
        player_gear = cursor.fetchone()
        old_weapon, old_armor = player_gear[0], player_gear[1]

        # 扣除背包中要穿戴的新裝備 1 個
        if item[0] > 1:
            cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        else:
            cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))

        if is_weapon:
            # 如果原本有裝備武器，放回背包
            if old_weapon and old_weapon != '無':
                cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, old_weapon))
                if cursor.fetchone():
                    cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, old_weapon))
                else:
                    cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, old_weapon))
            
            # 更新玩家武器
            cursor.execute("UPDATE players SET weapon_name = ?, weapon_atk = ? WHERE user_id = ?", (item_name, atk_bonus, user_id))
            conn.commit()
            return True, f"⚔️ 成功裝備武器：**{item_name}**（攻擊力 `+{atk_bonus}`）！"
        else:
            # 如果原本有裝備防具，放回背包
            if old_armor and old_armor != '無':
                cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, old_armor))
                if cursor.fetchone():
                    cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, old_armor))
                else:
                    cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, old_armor))

            # 更新玩家防具
            cursor.execute("UPDATE players SET armor_name = ?, armor_def = ? WHERE user_id = ?", (item_name, def_bonus, user_id))
            conn.commit()
            return True, f"🛡️ 成功裝備防具：**{item_name}**（防禦力 `+{def_bonus}`）！"
    finally:
        cursor.close()
        conn.close()

# 🧪 道具使用邏輯
def use_item_in_db(user_id: int, item_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO players (user_id, hp, max_hp, mp, max_mp) VALUES (?, 100, 100, 50, 50)", (user_id,))
        conn.commit()
        
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        item = cursor.fetchone()
        
        if not item or item[0] <= 0:
            return False, "你背包裡沒有這個道具！"
        
        cursor.execute("SELECT hp, max_hp, mp, max_mp FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        current_hp, max_hp, current_mp, max_mp = player[0], player[1], player[2], player[3]

        if item_name in ["生命藥水", "急救包"]:
            if current_hp >= max_hp:
                return False, "你的生命值已經全滿，不需要使用！"
                
            heal_amount = 50 if item_name == "急救包" else 30
            new_hp = min(max_hp, current_hp + heal_amount)
            actual_heal = new_hp - current_hp
            
            cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
            effect_msg = f"成功使用了 **{item_name}**！恢復了 `{actual_heal}` 點生命值（當前血量：`{new_hp}/{max_hp}`）。"
            
        elif item_name == "魔力藥水":
            if current_mp >= max_mp:
                return False, "你的魔力值已經全滿，不需要使用！"
                
            new_mp = min(max_mp, current_mp + 20)
            actual_mp = new_mp - current_mp
            cursor.execute("UPDATE players SET mp = ? WHERE user_id = ?", (new_mp, user_id))
            effect_msg = f"成功使用了 **魔力藥水**！恢復了 `{actual_mp}` 點魔力值（當前魔力：`{new_mp}/{max_mp}`）。"

        elif item_name == "能量飲料":
            if current_mp >= max_mp:
                return False, "你的魔力值已經全滿，不需要使用！"
                
            new_mp = min(max_mp, current_mp + 40)
            actual_mp = new_mp - current_mp
            cursor.execute("UPDATE players SET mp = ? WHERE user_id = ?", (new_mp, user_id))
            effect_msg = f"成功使用了 **能量飲料**！瞬間恢復了 `{actual_mp}` 點魔力值（當前魔力：`{new_mp}/{max_mp}`）。"
        else:
            return False, f"**{item_name}** 無法直接使用！如果是裝備，請使用 `/equip` 指令進行穿戴。"

        new_qty = item[0] - 1
        if new_qty > 0:
            cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))
        else:
            cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            
        conn.commit()
        return True, effect_msg
    finally:
        cursor.close()
        conn.close()

def take_damage(user_id: int, damage: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO players (user_id, hp, max_hp, mp, max_mp) VALUES (?, 100, 100, 50, 50)", (user_id,))
        conn.commit()
        
        cursor.execute("SELECT hp FROM players WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        current_hp = result[0] if result and result[0] is not None else 100
        new_hp = max(0, current_hp - damage)
        
        cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
        conn.commit()
        return new_hp, (new_hp == 0)
    finally:
        cursor.close()
        conn.close()

def reset_player_data(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# 🛒 商城購買邏輯（支援指定數量）
def buy_item_in_db(user_id: int, item_name: str, quantity: int):
    # 定義道具價格表（你可以根據你的商城設計調整價格）
    shop_prices = {
        "生命藥水": 50,
        "急救包": 120,
        "魔力藥水": 40,
        "能量飲料": 80,
        "神秘寶箱": 250
    }

    if item_name not in shop_prices:
        return False, f"❌ 商城中找不到 **{item_name}** 這個商品！"

    unit_price = shop_prices[item_name]
    total_cost = unit_price * quantity

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 檢查玩家金幣是否足夠
        cursor.execute("SELECT gold FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        if not player:
            return False, "❌ 你尚未建立角色！請先使用 `/setup_roles` 選擇職業。"
        
        current_gold = player[0] or 0
        if current_gold < total_cost:
            return False, f"❌ 金幣不足！購買 `{quantity}` 個 **{item_name}** 需要 `{total_cost} G`（你目前有 `{current_gold} G`）。"

        # 2. 扣除金幣
        cursor.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (total_cost, user_id))

        # 3. 將購買的數量加入背包
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?", (quantity, user_id, item_name))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)", (user_id, item_name, quantity))

        conn.commit()
        msg = f"🎉 成功購買 **{item_name}** x `{quantity}`！\n💰 總共花費：`{total_cost} G`（單價：`{unit_price} G`）"
        return True, msg
    finally:
        cursor.close()
        conn.close()

# 🛠️ 完整的裝備合成配方字典
# 定義合成配方表 { 合成結果道具: {"cost_gold": 費用, "materials": {材料名稱: 數量}} }
CRAFT_RECIPES = {
    # ---------------- ⚪ 普通裝備系列 (入門期) ----------------
    "【普通】高震動短刀": {
        "cost_gold": 30,
        "materials": {"鐵劍碎片": 3, "鐵礦石": 2},
        "type": "weapon",
        "bonus": 6,
        "desc": "消耗 3 個鐵劍碎片、2 個鐵礦石與 30 G 合成的普通武器。"
    },
    "【普通】光束劍": {
        "cost_gold": 50,
        "materials": {"鐵劍碎片": 5, "鐵礦石": 3},
        "type": "weapon",
        "bonus": 8,
        "desc": "消耗 5 個鐵劍碎片、3 個鐵礦石與 50 G 合成的普通武器。"
    },
    "【普通】電擊打擊槍": {
        "cost_gold": 60,
        "materials": {"鐵劍碎片": 6, "鐵礦石": 4},
        "type": "weapon",
        "bonus": 9,
        "desc": "消耗 6 個鐵劍碎片、4 個鐵礦石與 60 G 合成的普通武器。"
    },
    "【普通】重型巨斧": {
        "cost_gold": 70,
        "materials": {"鐵劍碎片": 8, "鐵礦石": 5},
        "type": "weapon",
        "bonus": 11,
        "desc": "消耗 8 個鐵劍碎片、5 個鐵礦石與 70 G 合成的普通武器。"
    },
    "【普通】戰術護甲": {
        "cost_gold": 40,
        "materials": {"鐵礦石": 3},
        "type": "armor",
        "bonus": 5,
        "desc": "消耗 3 個鐵礦石與 40 G 合成的普通防具。"
    },
    "【普通】納米防護服": {
        "cost_gold": 45,
        "materials": {"鐵礦石": 4, "生命藥水": 1},
        "type": "armor",
        "bonus": 6,
        "desc": "消耗 4 個鐵礦石、1 瓶生命藥水與 45 G 合成的防具。"
    },
    "【普通】合金重盾": {
        "cost_gold": 55,
        "materials": {"鐵礦石": 6},
        "type": "armor",
        "bonus": 8,
        "desc": "消耗 6 個鐵礦石與 55 G 合成的普通防具。"
    },
    "【普通】外骨骼裝甲": {
        "cost_gold": 70,
        "materials": {"鐵礦石": 8},
        "type": "armor",
        "bonus": 10,
        "desc": "消耗 8 個鐵礦石與 70 G 合成的普通防具。"
    },

    # ---------------- 🔵 精良裝備系列 (消耗：普通裝備 + 更多鐵料 + 低階能量晶核) ----------------
    "【精良】高震動短刀": {
        "cost_gold": 100,
        "materials": {"【普通】高震動短刀": 1, "鐵劍碎片": 12, "鐵礦石": 8, "低階能量晶核": 1},
        "type": "weapon",
        "bonus": 12,
        "desc": "消耗普通短刀、大量鐵料與低階能量晶核升級的精良武器。"
    },
    "【精良】光束劍": {
        "cost_gold": 120,
        "materials": {"【普通】光束劍": 1, "鐵劍碎片": 15, "鐵礦石": 10, "低階能量晶核": 1},
        "type": "weapon",
        "bonus": 15,
        "desc": "消耗普通光束劍、大量鐵料與低階能量晶核升級的精良武器。"
    },
    "【精良】電擊打擊槍": {
        "cost_gold": 140,
        "materials": {"【普通】電擊打擊槍": 1, "鐵劍碎片": 18, "鐵礦石": 12, "低階能量晶核": 1},
        "type": "weapon",
        "bonus": 17,
        "desc": "結合鐵料與低階能量晶核強化的精良打擊槍。"
    },
    "【精良】重型巨斧": {
        "cost_gold": 160,
        "materials": {"【普通】重型巨斧": 1, "鐵劍碎片": 22, "鐵礦石": 15, "低階能量晶核": 1},
        "type": "weapon",
        "bonus": 20,
        "desc": "注入低階能量晶核與重度鐵料的精良重型巨斧。"
    },
    "【精良】戰術護甲": {
        "cost_gold": 90,
        "materials": {"【普通】戰術護甲": 1, "鐵礦石": 10, "低階能量晶核": 1},
        "type": "armor",
        "bonus": 10,
        "desc": "使用大量鐵礦石與低階能量晶核升級的精良戰術護甲。"
    },
    "【精良】納米防護服": {
        "cost_gold": 100,
        "materials": {"【普通】納米防護服": 1, "鐵礦石": 12, "低階能量晶核": 1},
        "type": "armor",
        "bonus": 12,
        "desc": "防禦力提升的精良納米防護服。"
    },
    "【精良】合金重盾": {
        "cost_gold": 120,
        "materials": {"【普通】合金重盾": 1, "鐵礦石": 15, "低階能量晶核": 1},
        "type": "armor",
        "bonus": 14,
        "desc": "強化結構的精良合金重盾。"
    },
    "【精良】外骨骼裝甲": {
        "cost_gold": 150,
        "materials": {"【普通】外骨骼裝甲": 1, "鐵礦石": 18, "低階能量晶核": 1},
        "type": "armor",
        "bonus": 16,
        "desc": "重型強化的精良外骨骼裝甲。"
    },

    # ---------------- 🟣 史詩裝備系列 (消耗：精良裝備 + 海量鐵料 + 中階能量晶核) ----------------
    "【史詩】高震動短刀": {
        "cost_gold": 350,
        "materials": {"【精良】高震動短刀": 1, "鐵劍碎片": 30, "鐵礦石": 20, "中階能量晶核": 1},
        "type": "weapon",
        "bonus": 22,
        "desc": "消耗精良短刀、海量鐵料與中階能量晶核的史詩短刀。"
    },
    "【史詩】光束劍": {
        "cost_gold": 380,
        "materials": {"【精良】光束劍": 1, "鐵劍碎片": 35, "鐵礦石": 24, "中階能量晶核": 1},
        "type": "weapon",
        "bonus": 26,
        "desc": "高能聚焦且消耗大量鐵料的史詩級光束劍。"
    },
    "【史詩】電磁打擊槍": {
        "cost_gold": 400,
        "materials": {"【精良】電擊打擊槍": 1, "鐵劍碎片": 40, "鐵礦石": 28, "中階能量晶核": 1},
        "type": "weapon",
        "bonus": 29,
        "desc": "注入中階能量核心與重裝鐵料的史詩遠程武器。"
    },
    "【史詩】重型巨斧": {
        "cost_gold": 450,
        "materials": {"【精良】重型巨斧": 1, "鐵劍碎片": 48, "鐵礦石": 32, "中階能量晶核": 1},
        "type": "weapon",
        "bonus": 34,
        "desc": "沉重且附帶中階能量震盪與海量鐵料的史詩巨斧。"
    },
    "【史詩】戰術護甲": {
        "cost_gold": 300,
        "materials": {"【精良】戰術護甲": 1, "鐵礦石": 25, "中階能量晶核": 1},
        "type": "armor",
        "bonus": 18,
        "desc": "具備中階能量防禦場與重裝鐵礦的史詩護甲。"
    },
    "【史詩】納米防護服": {
        "cost_gold": 330,
        "materials": {"【精良】納米防護服": 1, "鐵礦石": 28, "中階能量晶核": 1},
        "type": "armor",
        "bonus": 20,
        "desc": "微型奈米防禦升級的史詩防護服。"
    },
    "【史詩】合金重盾": {
        "cost_gold": 370,
        "materials": {"【精良】合金重盾": 1, "鐵礦石": 32, "中階能量晶核": 1},
        "type": "armor",
        "bonus": 24,
        "desc": "中階能量屏障加固的史詩重盾。"
    },
    "【史詩】外骨骼裝甲": {
        "cost_gold": 420,
        "materials": {"【精良】外骨骼裝甲": 1, "鐵礦石": 36, "中階能量晶核": 1},
        "type": "armor",
        "bonus": 28,
        "desc": "全覆蓋中階動力的史詩外骨骼。"
    },

    # ---------------- 🟡 傳說級裝備系列 (消耗：史詩裝備 + 極量鐵料 + 高階能量晶核) ----------------
    "【傳說級】終焉短刀": {
        "cost_gold": 1000,
        "materials": {"【史詩】高震動短刀": 1, "鐵劍碎片": 70, "鐵礦石": 45, "高階能量晶核": 1},
        "type": "weapon",
        "bonus": 40,
        "desc": "消耗史詩短刀、極量鐵料與高階能量晶核的傳說短刀。"
    },
    "【傳說級】終焉光束劍": {
        "cost_gold": 1100,
        "materials": {"【史詩】光束劍": 1, "鐵劍碎片": 80, "鐵礦石": 50, "高階能量晶核": 1},
        "type": "weapon",
        "bonus": 42,
        "desc": "切割一切的傳說級終焉光束劍。"
    },
    "【傳說級】毀滅電磁槍": {
        "cost_gold": 1200,
        "materials": {"【史詩】電磁打擊槍": 1, "鐵劍碎片": 90, "鐵礦石": 55, "高階能量晶核": 1},
        "type": "weapon",
        "bonus": 45,
        "desc": "貫穿戰場的傳說級電磁神兵。"
    },
    "【傳說級】毀滅重型巨斧": {
        "cost_gold": 1300,
        "materials": {"【史詩】重型巨斧": 1, "鐵劍碎片": 100, "鐵礦石": 60, "高階能量晶核": 1},
        "type": "weapon",
        "bonus": 50,
        "desc": "擁有神話級破壞力的傳說巨斧。"
    },
    "【傳說級】泰坦戰術護甲": {
        "cost_gold": 900,
        "materials": {"【史詩】戰術護甲": 1, "鐵礦石": 50, "高階能量晶核": 1},
        "type": "armor",
        "bonus": 30,
        "desc": "泰坦級防禦力的傳說戰術護甲。"
    },
    "【傳說級】脈衝防衛力場": {
        "cost_gold": 1000,
        "materials": {"【史詩】納米防護服": 1, "鐵礦石": 55, "高階能量晶核": 1},
        "type": "armor",
        "bonus": 33,
        "desc": "展開自動脈衝防禦的傳說力場服。"
    },
    "【傳說級】絕對防禦重盾": {
        "cost_gold": 1100,
        "materials": {"【史詩】合金重盾": 1, "鐵礦石": 60, "高階能量晶核": 1},
        "type": "armor",
        "bonus": 37,
        "desc": "號稱永不破裂的傳說重盾。"
    },
    "【傳說級】泰坦合金重裝": {
        "cost_gold": 1300,
        "materials": {"【史詩】外骨骼裝甲": 1, "鐵礦石": 70, "高階能量晶核": 1},
        "type": "armor",
        "bonus": 42,
        "desc": "終極防禦型態的傳說級泰坦重裝。"
    },

    # ---------------- 📦 消耗品與其他 ----------------
    "急救包": {
        "cost_gold": 50,
        "materials": {"生命藥水": 2},
        "type": "item",
        "desc": "消耗 2 瓶生命藥水與 50 G 濃縮合成的高效急救包。"
    },
    "中階能量晶核": {
        "cost_gold": 100,
        "materials": {"低階能量晶核": 3},
        "type": "item",
        "desc": "消耗 3 顆低階能量晶核與 100 G合成的中階能量晶核"
    },
    "高階能量晶核": {
        "cost_gold": 300,
        "materials": {"中階能量晶核": 3},
        "type": "item",
        "desc": "消耗 3 顆中階能量晶核與 300 G合成的高階能量晶核"
    }
}

def craft_item_in_db(user_id: int, target_item: str):
    if target_item not in CRAFT_RECIPES:
        return False, "❌ 查無此合成配方！"
    
    recipe = CRAFT_RECIPES[target_item]
    cost_gold = recipe["cost_gold"]
    required_materials = recipe["materials"]

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 檢查玩家金幣是否足夠
        cursor.execute("SELECT gold FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        if not player:
            return False, "❌ 找不到你的角色資料！"
        
        player_gold = player[0]
        if player_gold < cost_gold:
            return False, f"❌ 金幣不足！合成需要 `{cost_gold} G`，你目前只有 `{player_gold} G`。"

        # 2. 檢查所有材料數量是否足夠
        for mat_name, req_qty in required_materials.items():
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, mat_name))
            inv_row = cursor.fetchone()
            inv_qty = inv_row[0] if inv_row else 0
            if inv_qty < req_qty:
                return False, f"❌ 材料不足！缺少 **{mat_name}**（需要 `{req_qty}` 個，當前持有 `{inv_qty}` 個）。"

        # 3. 扣除金幣
        cursor.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (cost_gold, user_id))

        # 4. 扣除所有消耗的材料（若數量歸零則直接刪除該筆記錄）
        for mat_name, req_qty in required_materials.items():
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, mat_name))
            inv_qty = cursor.fetchone()[0]
            new_qty = inv_qty - req_qty
            if new_qty > 0:
                cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, user_id, mat_name))
            else:
                cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, mat_name))

        # 5. 將合成好的裝備放入背包
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, target_item))
        target_row = cursor.fetchone()
        if target_row:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, target_item))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, target_item))

        conn.commit()
        return True, f"🎉 成功合成 **{target_item}**！\n消耗金幣：`{cost_gold} G`\n裝備已自動放入你的背包中。"
        
    finally:
        cursor.close()
        conn.close()
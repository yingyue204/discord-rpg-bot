import sqlite3
import random

def get_db_connection():
    return sqlite3.connect("database.db")

# 初始化資料庫與自動補齊缺少的欄位
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. 確保 players 表格存在
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY
        )
    """)
    
    # 2. 自動檢查並補齊 players 表格欄位（包含穿戴中的裝備）
    columns_to_add = {
        "role": "TEXT",
        "hp": "INTEGER DEFAULT 100",
        "max_hp": "INTEGER DEFAULT 100",
        "mp": "INTEGER DEFAULT 50",
        "atk": "INTEGER DEFAULT 10",
        "def": "INTEGER DEFAULT 5",
        "gold": "INTEGER DEFAULT 0",
        "weapon_name": "TEXT DEFAULT '無'",
        "weapon_atk": "INTEGER DEFAULT 0",
        "armor_name": "TEXT DEFAULT '無'",
        "armor_def": "INTEGER DEFAULT 0"
    }
    
    cursor.execute("PRAGMA table_info(players)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE players ADD COLUMN {col_name} {col_type}")
            
    # 3. 確保 inventory（背包）表格存在
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_name TEXT,
            quantity INTEGER,
            PRIMARY KEY (user_id, item_name)
        )
    """)
    
    conn.commit()
    conn.close()

# 啟動時執行初始化
init_db()

# 開啟寶箱邏輯
def open_chest_in_db(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 檢查背包是否有寶箱
    cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = '神秘寶箱'", (user_id,))
    item = cursor.fetchone()

    if not item or item[0] <= 0:
        cursor.close()
        conn.close()
        return False, "你的背包裡沒有 **神秘寶箱**！"

    # 扣除 1 個寶箱
    if item[0] > 1:
        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = '神秘寶箱'", (user_id,))
    else:
        cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = '神秘寶箱'", (user_id,))

    # 抽籤品質機率：普通 60% | 稀有 25% | 史詩 12% | 傳說 3%
    quality_roll = random.random()
    if quality_roll < 0.60:
        quality, prefix, multiplier = "⚪ 普通", "普通", 1.0
    elif quality_roll < 0.85:
        quality, prefix, multiplier = "🔵 稀有", "精良", 1.8
    elif quality_roll < 0.97:
        quality, prefix, multiplier = "🟣 史詩", "史詩", 2.8
    else:
        quality, prefix, multiplier = "🟡 傳說", "傳說級", 4.5

    # 隨機決定開出武器還是防具
    is_weapon = random.choice([True, False])

    if is_weapon:
        weapon_base = random.choice(["光束劍", "高振動短刀", "電磁打擊槍", "重型巨斧"])
        item_name = f"【{prefix}】{weapon_base}"
        bonus_atk = int(random.randint(5, 12) * multiplier)

        # 寫入背包
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, item_name))

        conn.commit()
        cursor.close()
        conn.close()

        msg = (
            f"🎉 成功開啟 **神秘寶箱**！\n"
            f"獲得武器：**{item_name}**（品質：{quality}）\n"
            f"⚔️ **攻擊力加成**：`+{bonus_atk}`"
        )
        return True, msg, item_name, "weapon", bonus_atk, quality
    else:
        armor_base = random.choice(["戰術護甲", "納米防護服", "合金重盾", "外骨骼裝甲"])
        item_name = f"【{prefix}】{armor_base}"
        bonus_def = int(random.randint(3, 8) * multiplier)

        # 寫入背包
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, item_name))

        conn.commit()
        cursor.close()
        conn.close()

        msg = (
            f"🎉 成功開啟 **神秘寶箱**！\n"
            f"獲得防具：**{item_name}**（品質：{quality}）\n"
            f"🛡️ **防禦力加成**：`+{bonus_def}`"
        )
        return True, msg, item_name, "armor", bonus_def, quality

def use_item_in_db(user_id: int, item_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("INSERT OR IGNORE INTO players (user_id, hp, max_hp, mp) VALUES (?, 100, 100, 50)", (user_id,))
    conn.commit()
    
    # 檢查背包道具數量
    cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    item = cursor.fetchone()
    
    if not item or item[0] <= 0:
        cursor.close()
        conn.close()
        return False, "你背包裡沒有這個道具！"
    
    # 取當前血量
    cursor.execute("SELECT hp, max_hp FROM players WHERE user_id = ?", (user_id,))
    player = cursor.fetchone()
    current_hp, max_hp = player[0], player[1]

    # 判斷道具效果
    if item_name in ["生命藥水", "急救包"]:
        if current_hp >= max_hp:
            cursor.close()
            conn.close()
            return False, "你的生命值已經全滿，不需要使用！"
            
        heal_amount = 50 if item_name == "急救包" else 30
        new_hp = min(max_hp, current_hp + heal_amount)
        actual_heal = new_hp - current_hp
        
        cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
        effect_msg = f"成功使用了 **{item_name}**！恢復了 `{actual_heal}` 點生命值（當前血量：`{new_hp}/{max_hp}`）。"
        
    elif item_name == "魔力藥水":
        cursor.execute("UPDATE players SET mp = mp + 30 WHERE user_id = ?", (user_id,))
        effect_msg = "成功使用了 **魔力藥水**！恢復了 `30` 點魔力值。"
    else:
        cursor.close()
        conn.close()
        return False, f"**{item_name}** 無法直接使用！請確認是否為可消耗道具。"

    # 扣減或刪除背包道具數量
    new_qty = item[0] - 1
    if new_qty > 0:
        cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))
    else:
        cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))
        
    conn.commit()
    cursor.close()
    conn.close()
    return True, effect_msg

def take_damage(user_id: int, damage: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO players (user_id, hp, max_hp, mp) VALUES (?, 100, 100, 50)", (user_id,))
    conn.commit()
    
    cursor.execute("SELECT hp FROM players WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    current_hp = result[0] if result and result[0] is not None else 100
    new_hp = max(0, current_hp - damage)
    
    cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return new_hp, (new_hp == 0)

def reset_player_data(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
import sqlite3

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
    
    # 2. 自動檢查並補齊 players 表格可能缺少的欄位（防止舊資料庫報錯）
    columns_to_add = {
        "role": "TEXT",
        "hp": "INTEGER DEFAULT 100",
        "max_hp": "INTEGER DEFAULT 100",
        "mp": "INTEGER DEFAULT 50",
        "atk": "INTEGER DEFAULT 10",
        "def": "INTEGER DEFAULT 5",
        "gold": "INTEGER DEFAULT 0"
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

def use_item_in_db(user_id: int, item_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("INSERT OR IGNORE INTO players (user_id, hp, max_hp, mp) VALUES (?, 100, 100, 50)", (user_id,))
    conn.commit()
    
    # 取得當前血量與血量上限
    cursor.execute("SELECT hp, max_hp FROM players WHERE user_id = ?", (user_id,))
    player = cursor.fetchone()
    current_hp = player[0] if player and player[0] is not None else 100
    max_hp = player[1] if player and player[1] is not None else 100

    # 檢查背包道具數量
    cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    item = cursor.fetchone()
    
    if not item or item[0] <= 0:
        cursor.close()
        conn.close()
        return False, "你背包裡沒有這個道具！"
    
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
        return False, f"**{item_name}** 無法直接使用！"

    # 扣減或刪除背包道具數量
    new_qty = item[0] - 1
    if new_qty > 0:
        cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))
    else:
        # 修正：刪除時只需要 user_id 和 item_name 兩個參數
        cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        
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
    
    is_fainted = (new_hp == 0)
    return new_hp, is_fainted
    
# 清除指定玩家的所有遊戲記錄與背包
def reset_player_data(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
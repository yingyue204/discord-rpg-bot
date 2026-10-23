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
    
    cursor.execute("INSERT OR IGNORE INTO players (user_id, hp, mp) VALUES (?, 100, 50)", (user_id,))
    conn.commit()
    
    cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    item = cursor.fetchone()
    
    if not item or item[0] <= 0:
        conn.close()
        return False, "你背包裡沒有這個道具！"
    
    if item_name == "生命藥水":
        cursor.execute("UPDATE players SET hp = hp + 50 WHERE user_id = ?", (user_id,))
        effect_msg = "恢復了 50 點生命值！"
    elif item_name == "魔力藥水":
        cursor.execute("UPDATE players SET mp = mp + 30 WHERE user_id = ?", (user_id,))
        effect_msg = "恢復了 30 點魔力值！"
    else:
        effect_msg = "使用成功，但似乎沒有發生特別的事情。"

    new_qty = item[0] - 1
    if new_qty > 0:
        cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))
    else:
        cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))
        
    conn.commit()
    conn.close()
    return True, effect_msg

def take_damage(user_id: int, damage: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 確保玩家資料一定存在
    cursor.execute("INSERT OR IGNORE INTO players (user_id, hp, mp) VALUES (?, 100, 50)", (user_id,))
    conn.commit()
    
    cursor.execute("SELECT hp FROM players WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    current_hp = result[0] if result[0] is not None else 100
    new_hp = max(0, current_hp - damage)
    
    cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
    conn.commit()
    conn.close()
    
    is_fainted = (new_hp == 0)
    return new_hp, is_fainted
    
    # 清除指定玩家的所有遊戲記錄與背包
def reset_player_data(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 刪除 players 表格中的資料
    cursor.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
    # 刪除 inventory 背包表格中的所有道具
    cursor.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
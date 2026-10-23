import sqlite3
import os

def get_db_connection():
    # 優先使用 Render 的 Persistent Disk 路徑 (/var/data)
    # 如果是在本機開發，則自動退回使用同目錄下的 database.db
    if os.path.exists('/var/data'):
        db_path = '/var/data/database.db'
    else:
        db_path = 'database.db'
        
    conn = sqlite3.connect(db_path)
    return conn
    
import sqlite3

def use_item_in_db(user_id: int, item_name: str):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # 1. 檢查玩家是否擁有該道具且數量大於 0
    cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    item = cursor.fetchone()
    
    if not item or item[0] <= 0:
        conn.close()
        return False, "你背包裡沒有這個道具！"
    
    # 2. 根據道具名稱執行對應的效果（例如：生命藥水恢復 50 血量）
    if item_name == "生命藥水":
        # 假設 players 資料表有 hp 欄位
        cursor.execute("UPDATE players SET hp = hp + 50 WHERE user_id = ?", (user_id,))
        effect_msg = "恢復了 50 點生命值！"
    elif item_name == "魔力藥水":
        cursor.execute("UPDATE players SET mp = mp + 30 WHERE user_id = ?", (user_id,))
        effect_msg = "恢復了 30 點魔力值！"
    else:
        effect_msg = "使用成功，但似乎沒有發生特別的事情。"

    # 3. 扣除道具數量（若數量為 1 則直接從背包刪除，或數量減 1）
    new_qty = item[0] - 1
    if new_qty > 0:
        cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))
    else:
        cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        
    conn.commit()
    conn.close()
    return True, effect_msg
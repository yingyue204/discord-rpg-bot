import sqlite3

def get_db_connection():
    # 統一使用同目錄下的 database.db
    return sqlite3.connect("database.db")

def use_item_in_db(user_id: int, item_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. 檢查玩家是否擁有該道具且數量大於 0
    cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
    item = cursor.fetchone()
    
    if not item or item[0] <= 0:
        conn.close()
        return False, "你背包裡沒有這個道具！"
    
    # 2. 根據道具名稱執行對應的效果
    if item_name == "生命藥水":
        cursor.execute("UPDATE players SET hp = hp + 50 WHERE user_id = ?", (user_id,))
        effect_msg = "恢復了 50 點生命值！"
    elif item_name == "魔力藥水":
        cursor.execute("UPDATE players SET mp = mp + 30 WHERE user_id = ?", (user_id,))
        effect_msg = "恢復了 30 點魔力值！"
    else:
        effect_msg = "使用成功，但似乎沒有發生特別的事情。"

    # 3. 扣除道具數量
    new_qty = item[0] - 1
    if new_qty > 0:
        cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))
    else:
        cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        
    conn.commit()
    conn.close()
    return True, effect_msg

def take_damage(user_id: int, damage: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. 取得目前血量
    cursor.execute("SELECT hp FROM players WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None, "找不到你的角色資料！"
        
    current_hp = result[0]
    new_hp = max(0, current_hp - damage)
    
    # 2. 更新血量
    cursor.execute("UPDATE players SET hp = ? WHERE user_id = ?", (new_hp, user_id))
    conn.commit()
    conn.close()
    
    is_fainted = (new_hp == 0)
    return new_hp, is_fainted
import sqlite3
import random
import time

# 取得資料庫連線（開啟 WAL 模式與 20 秒 timeout，防止 database is locked 錯誤）
def get_db_connection():
    conn = sqlite3.connect("database.db", timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# 初始化資料庫表格與補齊結構
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 玩家主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY
            )
        """)
        
        # 2. 自動檢查與補齊欄位
        columns_to_add = {
            "role": "TEXT",
            "hp": "INTEGER DEFAULT 100",
            "max_hp": "INTEGER DEFAULT 100",
            "mp": "INTEGER DEFAULT 50",
            "max_mp": "INTEGER DEFAULT 50",
            "atk": "INTEGER DEFAULT 10",
            "def": "INTEGER DEFAULT 5",
            "gold": "INTEGER DEFAULT 0",
            "weapon_name": "TEXT DEFAULT '無'",
            "weapon_atk": "INTEGER DEFAULT 0",
            "armor_name": "TEXT DEFAULT '無'",
            "armor_def": "INTEGER DEFAULT 0",
            "last_mp_update": "INTEGER DEFAULT 0"
        }
        
        cursor.execute("PRAGMA table_info(players)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                cursor.execute(f"ALTER TABLE players ADD COLUMN {col_name} {col_type}")
                
        # 3. 背包資料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER,
                PRIMARY KEY (user_id, item_name)
            )
        """)
        
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# 執行初始化
init_db()

# 🔄 自動計算並更新玩家自然回魔 (每分鐘恢復 5 MP)
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
            recovered_mp = passed_minutes * 5  # 每分鐘 +5 MP
            new_mp = min(max_mp, mp + recovered_mp)
            new_last_update = last_update + (passed_minutes * 60)
            
            cursor.execute("UPDATE players SET mp = ?, last_mp_update = ? WHERE user_id = ?", (new_mp, new_last_update, user_id))
            conn.commit()
            mp = new_mp
            
        return mp, max_mp
    finally:
        cursor.close()
        conn.close()

# ⚡ 扣除指定 MP
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
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = '神秘寶箱'", (user_id,))
        item = cursor.fetchone()

        if not item or item[0] <= 0:
            return False, "你的背包裡沒有 **神秘寶箱**！"

        # 扣除 1 個寶箱
        if item[0] > 1:
            cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = '神秘寶箱'", (user_id,))
        else:
            cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = '神秘寶箱'", (user_id,))

        # 機率抽取品質
        quality_roll = random.random()
        if quality_roll < 0.60:
            quality, prefix, multiplier = "⚪ 普通", "普通", 1.0
        elif quality_roll < 0.85:
            quality, prefix, multiplier = "🔵 稀有", "精良", 1.8
        elif quality_roll < 0.97:
            quality, prefix, multiplier = "🟣 史詩", "史詩", 2.8
        else:
            quality, prefix, multiplier = "🟡 傳說", "傳說級", 4.5

        is_weapon = random.choice([True, False])

        if is_weapon:
            weapon_base = random.choice(["光束劍", "高振動短刀", "電磁打擊槍", "重型巨斧"])
            item_name = f"【{prefix}】{weapon_base}"
            bonus_atk = int(random.randint(5, 12) * multiplier)

            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, item_name))

            conn.commit()
            msg = f"🎉 成功開啟 **神秘寶箱**！\n獲得武器：**{item_name}**（品質：{quality}）\n⚔️ **攻擊力加成**：`+{bonus_atk}`"
            return True, msg, item_name, "weapon", bonus_atk, quality
        else:
            armor_base = random.choice(["戰術護甲", "納米防護服", "合金重盾", "外骨骼裝甲"])
            item_name = f"【{prefix}】{armor_base}"
            bonus_def = int(random.randint(3, 8) * multiplier)

            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, item_name))

            conn.commit()
            msg = f"🎉 成功開啟 **神秘寶箱**！\n獲得防具：**{item_name}**（品質：{quality}）\n🛡️ **防禦力加成**：`+{bonus_def}`"
            return True, msg, item_name, "armor", bonus_def, quality
    finally:
        cursor.close()
        conn.close()

# 🧪 道具使用邏輯（支援生命藥水、急救包、魔力藥水、能量飲料）
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
            return False, f"**{item_name}** 無法直接使用！請確認是否為可消耗道具。"

        new_qty = item[0] - 1
        if new_qty > 0:
            cursor.execute("UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))
        else:
            cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (new_qty, user_id, item_name))
            
        conn.commit()
        return True, effect_msg
    finally:
        cursor.close()
        conn.close()

# 💥 扣血計算
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

# 🧹 管理員重置玩家資料
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
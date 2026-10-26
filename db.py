import sqlite3
import time
import random
from contextlib import contextmanager

@contextmanager
def get_db():
    conn = sqlite3.connect("game.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()  # 成功時自動提交
    except Exception as e:
        conn.rollback()  # 發生錯誤時自動回滾
        raise e
    finally:
        cursor.close()
        conn.close()   # 🔒 不管有沒有報錯，這裡絕對會自動關閉連線！

# ⚔️ 戰鬥勝利的資料庫結算處理
def process_battle_victory_in_db(user_id: int, gold_reward: int, exp_reward: int, dropped_item: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 增加金幣
        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (gold_reward, user_id))
        
        # 2. 增加經驗值並處理升級（假設你有寫 gain_player_exp 函數）
        # 這裡可以直接調用我們之前寫好的升級邏輯
        # success_exp, exp_msg = gain_player_exp(user_id, exp_amount=exp_reward)
        
        # 3. 如果有掉落物，加入背包
        reward_text = f"💰 獲得金幣：`+{gold_reward} G`"
        if dropped_item:
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, dropped_item))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, dropped_item))
            else:
                cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, dropped_item))
            reward_text += f"\n🎁 獲得戰利品：**{dropped_item}** x `1`"

        conn.commit()
        return reward_text
    finally:
        cursor.close()
        conn.close()

def get_player_status(user_id):
    """取得玩家完整的屬性狀態"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT role_name, level, exp, hp, max_hp, mp, max_mp, stamina, max_stamina, atk, def, gold, weapon_name, weapon_atk, armor_name, armor_def 
            FROM players 
            WHERE user_id = ?
        """, (user_id,))
        player = cursor.fetchone()
        return player
    except Exception as e:
        print(f"❌ 查詢玩家屬性錯誤: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. 玩家資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            role_name TEXT,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            hp INTEGER,
            max_hp INTEGER,
            mp INTEGER,
            max_mp INTEGER,
            stamina INTEGER,
            max_stamina INTEGER,
            atk INTEGER,
            def INTEGER,
            gold INTEGER DEFAULT 100,
            weapon_name TEXT,
            weapon_atk INTEGER DEFAULT 0,
            armor_name TEXT,
            armor_def INTEGER DEFAULT 0
        )
    """)
    
    # 🛡️ 自動補上可能缺少的欄位（防止舊資料庫報錯）
    cursor.execute("PRAGMA table_info(players)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "level" not in columns:
        cursor.execute("ALTER TABLE players ADD COLUMN level INTEGER DEFAULT 1")
    if "exp" not in columns:
        cursor.execute("ALTER TABLE players ADD COLUMN exp INTEGER DEFAULT 0")

    # (其他表格與初始化邏輯...)
    conn.commit()
    cursor.close()
    conn.close()

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

# 📦 寶箱抽獎專用裝備資料庫（已移除材料與消耗，並平衡 bonus 數值）
EQUIPMENT_DATABASE = {
    # ---------------- ⚪ 普通裝備系列 (Normal) ----------------
    "【普通】高震動短刀": {"type": "weapon", "bonus": 8},
    "【普通】光束劍": {"type": "weapon", "bonus": 10},
    "【普通】電擊打擊槍": {"type": "weapon", "bonus": 12},
    "【普通】重型巨斧": {"type": "weapon", "bonus": 14},
    "【普通】戰術護甲": {"type": "armor", "bonus": 6},
    "【普通】納米防護服": {"type": "armor", "bonus": 8},
    "【普通】合金重盾": {"type": "armor", "bonus": 10},
    "【普通】外骨骼裝甲": {"type": "armor", "bonus": 12},

    # ---------------- 🔵 精良裝備系列 (Rare) ----------------
    "【精良】高震動短刀": {"type": "weapon", "bonus": 18},
    "【精良】光束劍": {"type": "weapon", "bonus": 21},
    "【精良】電擊打擊槍": {"type": "weapon", "bonus": 24},
    "【精良】重型巨斧": {"type": "weapon", "bonus": 27},
    "【精良】戰術護甲": {"type": "armor", "bonus": 14},
    "【精良】納米防護服": {"type": "armor", "bonus": 16},
    "【精良】合金重盾": {"type": "armor", "bonus": 19},
    "【精良】外骨骼裝甲": {"type": "armor", "bonus": 22},

    # ---------------- 🟣 史詩裝備系列 (Epic) ----------------
    "【史詩】高震動短刀": {"type": "weapon", "bonus": 35},
    "【史詩】光束劍": {"type": "weapon", "bonus": 38},
    "【史詩】電磁打擊槍": {"type": "weapon", "bonus": 42},
    "【史詩】重型巨斧": {"type": "weapon", "bonus": 46},
    "【史詩】戰術護甲": {"type": "armor", "bonus": 28},
    "【史詩】納米防護服": {"type": "armor", "bonus": 31},
    "【史詩】合金重盾": {"type": "armor", "bonus": 34},
    "【史詩】外骨骼裝甲": {"type": "armor", "bonus": 38},

    # ---------------- 🟡 傳說級裝備系列 (Legendary) ----------------
    "【傳說級】終焉短刀": {"type": "weapon", "bonus": 60},
    "【傳說級】終焉光束劍": {"type": "weapon", "bonus": 65},
    "【傳說級】毀滅電磁槍": {"type": "weapon", "bonus": 70},
    "【傳說級】毀滅重型巨斧": {"type": "weapon", "bonus": 75},
    "【傳說級】泰坦戰術護甲": {"type": "armor", "bonus": 48},
    "【傳說級】脈衝防衛力場": {"type": "armor", "bonus": 52},
    "【傳說級】絕對防禦重盾": {"type": "armor", "bonus": 56},
    "【傳說級】泰坦合金重裝": {"type": "armor", "bonus": 60}
}

# 🎁 開啟神秘寶箱邏輯（已適配最新裝備庫名稱）
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

        # 3. 隨機決定品質
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

        # 4. 隨機決定是武器還是防具，並對應新資料庫命名
        is_weapon = random.choice([True, False])

        if is_weapon:
            item_type = "weapon"
            if prefix == "傳說級":
                weapon_bases = ["終焉短刀", "終焉光束劍", "毀滅電磁槍", "毀滅重型巨斧"]
            else:
                weapon_bases = ["高震動短刀", "光束劍", "電擊打擊槍", "重型巨斧"]
            
            chosen_base = random.choice(weapon_bases)
            
            # 名稱對應修正（史詩的電磁打擊槍）
            if prefix == "史詩" and chosen_base == "電擊打擊槍":
                chosen_base = "電磁打擊槍"
                
            item_name = f"【{prefix}】{chosen_base}"
        else:
            item_type = "armor"
            if prefix == "傳說級":
                armor_bases = ["泰坦戰術護甲", "脈衝防衛力場", "絕對防禦重盾", "泰坦合金重裝"]
            else:
                armor_bases = ["戰術護甲", "納米防護服", "合金重盾", "外骨骼裝甲"]
                
            chosen_base = random.choice(armor_bases)
            item_name = f"【{prefix}】{chosen_base}"

        # 5. 從 EQUIPMENT_DATABASE 查表取得 bonus 數值
        if item_name in EQUIPMENT_DATABASE:
            bonus = EQUIPMENT_DATABASE[item_name]["bonus"]
        else:
            bonus = 10  # 防呆保底

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
        if "光束劍" in item_name or "高振動短刀" in item_name or "電擊打擊槍" in item_name or "重型巨斧" in item_name:
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

import sqlite3
import os

# 鎖死絕對路徑，確保所有模組讀寫的是同一個檔案
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "game.db")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. 建立基礎 players 表格（包含 level 與 exp）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            role_name TEXT,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            hp INTEGER,
            max_hp INTEGER,
            mp INTEGER,
            max_mp INTEGER,
            stamina INTEGER,
            max_stamina INTEGER,
            atk INTEGER,
            def INTEGER,
            gold INTEGER DEFAULT 100,
            weapon_name TEXT,
            weapon_atk INTEGER DEFAULT 0,
            armor_name TEXT,
            armor_def INTEGER DEFAULT 0
        )
    """)
    
    # 2. 強制檢查並補上可能遺失的欄位（針對已經存在的舊資料庫）
    try:
        cursor.execute("ALTER TABLE players ADD COLUMN level INTEGER DEFAULT 1")
    except Exception:
        pass  # 如果欄位已經存在，會自動略過錯誤
        
    try:
        cursor.execute("ALTER TABLE players ADD COLUMN exp INTEGER DEFAULT 0")
    except Exception:
        pass  # 如果欄位已經存在，會自動略過錯誤

    
    # 2. 背包資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            quantity INTEGER
        )
    """)

    # 3. 玩家市場資料表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_listings (
            listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            item_name TEXT,
            price INTEGER,
            quantity INTEGER
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"✨ [資料庫重置] 絕對路徑初始化完成: {DB_PATH}")

# 確保每次載入都會執行
init_db()

# --- 市場查詢與交易函數 ---
def get_active_sellers(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT seller_id 
        FROM market_listings 
        WHERE seller_id != ? AND quantity > 0
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [(row[0], f"特務 #{row[0]}") for row in rows]

def get_listings_by_seller(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, item_name, price, quantity 
        FROM market_listings 
        WHERE seller_id = ? AND quantity > 0
    """, (seller_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items

def buy_market_item(buyer_id, listing_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT seller_id, item_name, price, quantity FROM market_listings WHERE listing_id = ?", (listing_id,))
        listing = cursor.fetchone()
        if not listing:
            return False, "❌ 該商品已經不存在！"
            
        seller_id, item_name, price, qty = listing
        if buyer_id == seller_id:
            return False, "❌ 不能購買自己的商品！"
            
        cursor.execute("SELECT gold FROM players WHERE user_id = ?", (buyer_id,))
        buyer = cursor.fetchone()
        if not buyer or buyer[0] < price:
            return False, f"❌ 金幣不足（需要 {price} G）！"
            
        cursor.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (price, buyer_id))
        cursor.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (price, seller_id))
        
        if qty > 1:
            cursor.execute("UPDATE market_listings SET quantity = quantity - 1 WHERE listing_id = ?", (listing_id,))
        else:
            cursor.execute("DELETE FROM market_listings WHERE listing_id = ?", (listing_id,))
            
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (buyer_id, item_name))
        inv = cursor.fetchone()
        if inv:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (buyer_id, item_name))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (buyer_id, item_name))
            
        conn.commit()
        return True, f"✅ 成功購買 **{item_name}**！花費 `{price} G`。"
    except Exception as e:
        conn.rollback()
        return False, f"❌ 交易錯誤：`{e}`"
    finally:
        cursor.close()
        conn.close()

def list_market_item(user_id, item_name, price, quantity):
    """將玩家背包的道具上架至市場"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. 檢查玩家背包是否有足夠的該道具
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        inv = cursor.fetchone()
        
        if not inv or inv[0] < quantity:
            return False, f"❌ 你的背包中沒有足夠的 **{item_name}**（現有數量：`{inv[0] if inv else 0}`）！"
            
        if price <= 0 or quantity <= 0:
            return False, "❌ 價格與數量必須大於 0！"

        # 2. 扣除或刪除背包中的道具
        if inv[0] == quantity:
            cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        else:
            cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?", (quantity, user_id, item_name))

        # 3. 寫入市場上架資料表
        cursor.execute("""
            INSERT INTO market_listings (seller_id, item_name, price, quantity)
            VALUES (?, ?, ?, ?)
        """, (user_id, item_name, price, quantity))

        conn.commit()
        return True, f"✅ 成功上架 **{item_name}** x `{quantity}`！單價：`{price} G`。"
    except Exception as e:
        conn.rollback()
        return False, f"❌ 上架發生錯誤：`{e}`"
    finally:
        cursor.close()
        conn.close()


# 📈 增加玩家經驗值與處理升級邏輯
def gain_player_exp(user_id: int, exp_amount: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 取得玩家當前等級與經驗值
        cursor.execute("SELECT level, exp FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        if not player:
            return False, "找不到玩家資料"
        
        level, current_exp = player
        current_exp += exp_amount
        
        # 升級所需經驗值公式（例如：當前等級 * 100）
        next_level_exp = level * 100
        level_up_msg = ""
        
        # 檢查是否升級（支援連續升級）
        while current_exp >= next_level_exp:
            current_exp -= next_level_exp
            level += 1
            next_level_exp = level * 100
            
            # 升級時順便提升屬性（可依你的需求調整數值）
            cursor.execute("""
                UPDATE players 
                SET level = ?, exp = ?, max_hp = max_hp + 20, hp = max_hp + 20, atk = atk + 3 
                WHERE user_id = ?
            """, (level, current_exp, user_id))
            level_up_msg += f"\n🎉 **等級提升！** 恭喜升到 **Lv.{level}**（生命上限與攻擊力提升！）"
        
        # 若沒有升級，僅更新經驗值
        if not level_up_msg:
            cursor.execute("UPDATE players SET exp = ? WHERE user_id = ?", (current_exp, user_id))
            
        conn.commit()
        return True, f"獲得經驗值 `+{exp_amount} EXP`{level_up_msg}"
    finally:
        cursor.close()
        conn.close()

import sqlite3

import sqlite3
import time

def get_db_connection(db_name="game.db"):
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== 🛒 商城道具與定價表 ====================
SHOP_ITEMS = {
    # 🧪 1. 藥水與補給品類
    "生命藥水": {"price": 30, "type": "consumable", "description": "基礎治療道具，使用後恢復 30 點生命值。"},
    "急救包": {"price": 60, "type": "consumable", "description": "高效急救醫療包，使用後恢復 50 點生命值。"},
    "魔力藥水": {"price": 40, "type": "consumable", "description": "補充精神力的藥劑，使用後恢復 20 點 MP。"},
    "能量飲料": {"price": 75, "type": "consumable", "description": "高科技提神飲料，使用後瞬間恢復 40 點 MP。"},

    # 🎁 2. 特殊道具與寶箱類
    "神秘寶箱": {"price": 200, "type": "special", "description": "內含各品質武器與防具的神秘寶箱。"},

    # 🌾 3. 農場作物／種子類
    "小麥": {"price": 20, "type": "material", "description": "基礎烘焙與麵食原料。"},
    "米": {"price": 25, "type": "material", "description": "香甜白米，製作壽司與飯類必備。"},
    "蔬菜": {"price": 30, "type": "material", "description": "新鮮蔬菜，烹飪配料。"},
    "水果": {"price": 35, "type": "material", "description": "多汁水果，用於甜點與氣泡水。"},
    "香料": {"price": 40, "type": "material", "description": "去腥提味的關鍵調味料。"},
    "蔥": {"price": 25, "type": "material", "description": "香氣十足的青蔥。"},
    "鮮魚": {"price": 50, "type": "material", "description": "新鮮漁獲。"},

    # 🥩 4. 基礎肉品類
    "生肉": {"price": 45, "type": "material", "description": "多種肉類料理的基礎原料。"},

    # 🔨 5. 料理台升級專用素材
    "鐵塊": {"price": 200, "type": "upgrade", "description": "料理台升級至 Lv.2 的必要素材。"},
    "魔導金屬": {"price": 1000, "type": "upgrade", "description": "料理台升級至 Lv.3 的必要素材。"},

    # 🏡 6. 牧場動物
    "乳牛": {"price": 300, "type": "animal", "description": "產出「牛奶」。"},
    "肉牛": {"price": 400, "type": "animal", "description": "產出「高級肉塊」。"},
    "豬": {"price": 250, "type": "animal", "description": "產出「五花肉」。"},
    "雞": {"price": 150, "type": "animal", "description": "產出「雞蛋」。"}
}

# 簡化版價格對應字典（相容舊程式）
shop_prices = {name: data["price"] for name, data in SHOP_ITEMS.items()}


# ==================== 🍳 料理食譜與升級資料庫 ====================
RECIPE_DATABASE = {
    # --- 1等料理台 ---
    "義大利麵": {"station_level": 1, "ingredients": {"小麥": 2, "生肉": 1, "蔬菜": 1}, "output": "【料理】義大利麵", "description": "恢復 40 點生命與 20 點魔力。"},
    "麵包": {"station_level": 1, "ingredients": {"小麥": 3}, "output": "【料理】麵包", "description": "恢復 25 點生命。"},
    "香煎魚": {"station_level": 1, "ingredients": {"鮮魚": 1, "香料": 1}, "output": "【料理】香煎魚", "description": "恢復 35 點生命。"},
    "壽司": {"station_level": 1, "ingredients": {"米": 2, "鮮魚": 1}, "output": "【料理】壽司", "description": "恢復 30 點生命與 15 點魔力。"},
    "什錦飯": {"station_level": 1, "ingredients": {"米": 2, "生肉": 1, "蔬菜": 2}, "output": "【料理】什錦飯", "description": "恢復 50 點生命。"},
    "熱狗麵包": {"station_level": 1, "ingredients": {"小麥": 2, "生肉": 1}, "output": "【料理】熱狗麵包", "description": "恢復 30 點生命。"},
    "紅燒肉": {"station_level": 1, "ingredients": {"五花肉": 2, "香料": 1}, "output": "【料理】紅燒肉", "description": "恢復 60 點生命。"},
    "包子": {"station_level": 1, "ingredients": {"小麥": 2, "生肉": 1}, "output": "【料理】包子", "description": "恢復 35 點生命。"},
    "麵疙瘩": {"station_level": 1, "ingredients": {"小麥": 3, "蔬菜": 1}, "output": "【料理】麵疙瘩", "description": "恢復 30 點生命。"},
    "蔥油餅": {"station_level": 1, "ingredients": {"小麥": 3, "蔥": 2}, "output": "【料理】蔥油餅", "description": "恢復 30 點生命。"},
    "咖哩飯": {"station_level": 1, "ingredients": {"米": 2, "蔬菜": 2, "生肉": 1}, "output": "【料理】咖哩飯", "description": "恢復 55 點生命與 20 點魔力。"},

    # --- 2等料理台 ---
    "千層蛋糕": {"station_level": 2, "ingredients": {"小麥": 3, "雞蛋": 2, "牛奶": 2}, "output": "【料理】千層蛋糕", "description": "恢復 60 點魔力。"},
    "香檳氣泡水": {"station_level": 2, "ingredients": {"水果": 3}, "output": "【料理】香檳氣泡水", "description": "恢復 40 點魔力。"},
    "泡芙": {"station_level": 2, "ingredients": {"小麥": 2, "雞蛋": 2, "牛奶": 1}, "output": "【料理】泡芙", "description": "恢復 45 點魔力。"},
    "燉飯": {"station_level": 2, "ingredients": {"米": 3, "生肉": 1, "蔬菜": 2}, "output": "【料理】燉飯", "description": "恢復 70 點生命。"},
    "舒芙蕾": {"station_level": 2, "ingredients": {"雞蛋": 3, "牛奶": 2}, "output": "【料理】舒芙蕾", "description": "恢復 50 點魔力。"},
    "披薩": {"station_level": 2, "ingredients": {"小麥": 3, "生肉": 2, "蔬菜": 1}, "output": "【料理】披薩", "description": "恢復 80 點生命。"},
    "白醬意麵": {"station_level": 2, "ingredients": {"小麥": 2, "牛奶": 2, "生肉": 1}, "output": "【料理】白醬意麵", "description": "恢復 65 點生命與 30 點魔力。"},
    "東坡肉": {"station_level": 2, "ingredients": {"五花肉": 3, "香料": 2}, "output": "【料理】東坡肉", "description": "恢復 90 點生命。"},

    # --- 3等料理台 ---
    "紅酒燉牛肉": {"station_level": 3, "ingredients": {"高級肉塊": 2, "蔬菜": 3, "香料": 1}, "output": "【料理】紅酒燉牛肉", "description": "恢復 120 點生命與 50 點魔力！"},
    "牛肉麵": {"station_level": 3, "ingredients": {"小麥": 2, "高級肉塊": 2, "蔬菜": 1}, "output": "【料理】牛肉麵", "description": "恢復 100 點生命與 40 點魔力。"}
}

COOKING_STATION_UPGRADE_COST = {
    2: {"gold": 1000, "item": "鐵塊", "qty": 5},
    3: {"gold": 5000, "item": "魔導金屬", "qty": 3}
}


# ==================== 🛠️ 資料庫初始化函數 ====================
def init_db(db_name="game.db"):
    conn = get_db_connection(db_name)
    cursor = conn.cursor()

    # 1. 玩家主表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            role_name TEXT,
            hp INTEGER,
            max_hp INTEGER,
            mp INTEGER DEFAULT 50,
            atk INTEGER,
            def INTEGER,
            weapon_atk INTEGER DEFAULT 0,
            armor_def INTEGER DEFAULT 0,
            gold INTEGER DEFAULT 100,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            cooking_level INTEGER DEFAULT 1
        )
    """)

    # 2. 玩家背包表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_name TEXT,
            quantity INTEGER,
            PRIMARY KEY (user_id, item_name)
        )
    """)

    # 3. 農場土地表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farm_plots (
            user_id INTEGER,
            plot_index INTEGER,
            crop_name TEXT,
            ready_timestamp REAL,
            status TEXT DEFAULT 'empty',
            PRIMARY KEY (user_id, plot_index)
        )
    """)

    # 4. 玩家已解鎖食譜表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_recipes (
            user_id INTEGER,
            recipe_name TEXT,
            PRIMARY KEY (user_id, recipe_name)
        )
    """)

    # 5. 牧場動物表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ranch_animals (
            user_id INTEGER,
            animal_index INTEGER,
            animal_type TEXT,
            feed_timestamp REAL,
            status TEXT DEFAULT 'ready',
            PRIMARY KEY (user_id, animal_index)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


# ==================== 🛒 商城購買邏輯 ====================
def buy_item_in_db(user_id: int, item_name: str, quantity: int):
    if quantity <= 0:
        return False, "❌ 購買數量必須大於 0！"
    if item_name not in shop_prices:
        return False, f"❌ 商城中找不到 **{item_name}** 這個商品！"

    unit_price = shop_prices[item_name]
    total_cost = unit_price * quantity

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT gold FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        if not player:
            return False, "❌ 你尚未建立角色！請先使用 `/setup_roles` 選擇職業。"
        
        current_gold = player["gold"] or 0
        if current_gold < total_cost:
            return False, f"❌ 金幣不足！購買 `{quantity}` 個 **{item_name}** 需要 `{total_cost} G`（目前有 `{current_gold} G`）。"

        cursor.execute("UPDATE players SET gold = gold - ? WHERE user_id = ?", (total_cost, user_id))

        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?", (quantity, user_id, item_name))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)", (user_id, item_name, quantity))

        conn.commit()
        return True, f"🎉 成功購買 **{item_name}** x `{quantity}`！\n💰 總共花費：`{total_cost} G`"
    except Exception as e:
        conn.rollback()
        return False, f"❌ 購買發生錯誤：`{e}`"
    finally:
        cursor.close()
        conn.close()


# ==================== 🌾 農場系統相關函數 ====================
def get_player_farm(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM farm_plots WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] == 0:
            for i in range(1, 4):
                cursor.execute("INSERT INTO farm_plots (user_id, plot_index, status) VALUES (?, ?, 'empty')", (user_id, i))
            conn.commit()
            
        cursor.execute("SELECT plot_index, crop_name, ready_timestamp, status FROM farm_plots WHERE user_id = ? ORDER BY plot_index", (user_id,))
        plots = cursor.fetchall()
        return plots
    finally:
        cursor.close()
        conn.close()

def plant_crop(user_id, plot_index, crop_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT status FROM farm_plots WHERE user_id = ? AND plot_index = ?", (user_id, plot_index))
        plot = cursor.fetchone()
        if not plot:
            return False, "❌ 找不到這塊農田！"
        if plot[0] != 'empty':
            return False, "❌ 這塊農田已經有作物正在生長或已成熟了！"
            
        seed_name = f"{crop_name}種子"
        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, seed_name))
        seed = cursor.fetchone()
        if not seed or seed[0] < 1:
            return False, f"❌ 你的背包中沒有 **{seed_name}**！"
            
        cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, seed_name))
            
        ready_time = time.time() + 60 
        cursor.execute("""
            UPDATE farm_plots 
            SET crop_name = ?, ready_timestamp = ?, status = 'growing' 
            WHERE user_id = ? AND plot_index = ?
        """, (crop_name, ready_time, user_id, plot_index))
        
        conn.commit()
        return True, f"🌱 成功在 **第 {plot_index} 號田** 種下了 **{crop_name}**！"
    except Exception as e:
        conn.rollback()
        return False, f"❌ 種植錯誤：`{e}`"
    finally:
        cursor.close()
        conn.close()

def harvest_crop(user_id, plot_index):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT crop_name, ready_timestamp, status FROM farm_plots WHERE user_id = ? AND plot_index = ?", (user_id, plot_index))
        plot = cursor.fetchone()
        if not plot:
            return False, "❌ 找不到這塊農田！"
            
        crop_name, ready_timestamp, status = plot
        if status == 'empty':
            return False, "❌ 這塊田什麼都沒有種！"
            
        if status == 'growing':
            remaining = int(ready_timestamp - time.time())
            if remaining > 0:
                return False, f"⏳ 作物還沒成熟！還要等待 `{remaining}` 秒。"

        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, crop_name))
        inv = cursor.fetchone()
        if inv:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, crop_name))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, crop_name))
            
        cursor.execute("""
            UPDATE farm_plots 
            SET crop_name = NULL, ready_timestamp = NULL, status = 'empty' 
            WHERE user_id = ? AND plot_index = ?
        """, (user_id, plot_index))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, f"🌾 成功收成 **{crop_name}**！"
    except Exception as e:
        try:
            conn.rollback()
            cursor.close()
            conn.close()
        except:
            pass
        return False, f"❌ 收成錯誤：`{e}`"


# ==================== 🍳 料理製作與升級邏輯 ====================
def cook_recipe_in_db(user_id: int, recipe_name: str):
    if recipe_name not in RECIPE_DATABASE:
        return False, f"❌ 找不到食譜 **{recipe_name}**！"
    
    recipe = RECIPE_DATABASE[recipe_name]
    required_level = recipe["station_level"]
    ingredients = recipe["ingredients"]
    output_item = recipe["output"]

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT cooking_level FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        if not player:
            return False, "❌ 你尚未建立角色！請先使用 `/setup_roles` 選擇職業。"
        
        current_level = player["cooking_level"] or 1
        if current_level < required_level:
            return False, f"❌ 料理台等級不足！製作 **{recipe_name}** 需要 Lv.{required_level}。"

        for ing_name, req_qty in ingredients.items():
            cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, ing_name))
            inv = cursor.fetchone()
            current_qty = inv["quantity"] if inv else 0
            if current_qty < req_qty:
                return False, f"❌ 素材不足！缺少 **{ing_name}**（需要 `{req_qty}` 個）。"

        for ing_name, req_qty in ingredients.items():
            cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?", (req_qty, user_id, ing_name))

        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, output_item))
        out_inv = cursor.fetchone()
        if out_inv:
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE user_id = ? AND item_name = ?", (user_id, output_item))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, 1)", (user_id, output_item))

        conn.commit()
        return True, f"🍳 成功烹調出 **{output_item}**！"
    except Exception as e:
        conn.rollback()
        return False, f"❌ 烹飪發生錯誤：`{e}`"
    finally:
        cursor.close()
        conn.close()

def upgrade_cooking_station_in_db(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT cooking_level, gold FROM players WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        if not player:
            return False, "❌ 你尚未建立角色！"
        
        current_level = player["cooking_level"] or 1
        next_level = current_level + 1

        if next_level not in COOKING_STATION_UPGRADE_COST:
            return False, "❌ 你的料理台已經達到最高等級（Lv.3）！"

        cost_info = COOKING_STATION_UPGRADE_COST[next_level]
        req_gold = cost_info["gold"]
        req_item = cost_info["item"]
        req_qty = cost_info["qty"]

        current_gold = player["gold"] or 0
        if current_gold < req_gold:
            return False, f"❌ 金幣不足！升級需要 `{req_gold} G`。"

        cursor.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, req_item))
        inv = cursor.fetchone()
        current_item_qty = inv["quantity"] if inv else 0
        if current_item_qty < req_qty:
            return False, f"❌ 升級素材不足！需要 **{req_item}** `{req_qty}` 個。"

        cursor.execute("UPDATE players SET gold = gold - ?, cooking_level = cooking_level + 1 WHERE user_id = ?", (req_gold, user_id))
        cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?", (req_qty, user_id, req_item))

        conn.commit()
        return True, f"🎉 料理台成功升級至 **Lv.{next_level}**！"
    except Exception as e:
        conn.rollback()
        return False, f"❌ 升級發生錯誤：`{e}`"
    finally:
        cursor.close()
        conn.close()
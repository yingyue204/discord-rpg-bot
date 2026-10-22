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
import sqlite3

def get_db_connection():
    # 連線到本地的 database.db 檔案
    conn = sqlite3.connect('database.db')
    return conn
import os
import psycopg2

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("找不到 DATABASE_URL 環境變數，請確認 Render Environment 設定！")
    
    # 自動補上 sslmode=require 確保加密連線，並設定 10 秒連線逾時避免卡死
    if "sslmode" not in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{separator}sslmode=require"
        
    return psycopg2.connect(db_url, prepare_threshold=0, connect_timeout=10)
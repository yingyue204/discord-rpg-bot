import os
import psycopg2

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("找不到 DATABASE_URL 環境變數，請確認 Render Environment 設定！")
    
    # 關鍵：加入 prepare_threshold=0 避免 Supabase 交易集區器卡死
    return psycopg2.connect(db_url, prepare_threshold=0)
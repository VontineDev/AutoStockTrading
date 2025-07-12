import os
import sqlite3
import logging
from typing import Optional, Any
import pandas as pd
from src.utils.dataframe_utils import standardize_dataframe

DB_PATH = os.getenv("DB_PATH", "data/trading.db")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/database.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def get_connection(db_path: str = DB_PATH) -> Optional[sqlite3.Connection]:
    """
    SQLite DB 연결 반환
    """
    try:
        conn = sqlite3.connect(db_path)
        logging.info(f"DB 연결 성공: {db_path}")
        return conn
    except sqlite3.Error as e:
        logging.error(f"DB 연결 실패: {e}")
        return None

def init_db(conn: sqlite3.Connection) -> None:
    """
    users 테이블 등 기본 테이블 생성
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
        logging.info("테이블 생성 완료")
    except sqlite3.Error as e:
        logging.error(f"테이블 생성 실패: {e}")

class DatabaseManager:
def __init__(self, db_path: str):
        self.db_path = db_path

def initialize_schema(self, schema_path: str):
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(schema_sql)

def execute(self, query: str, params: Optional[tuple] = None):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(query, params or ())
            conn.commit()

def fetchall(self, query: str, params: Optional[tuple] = None) -> list[Any]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(query, params or ())
            return cur.fetchall()

def fetchdf(self, query: str, params: Optional[tuple] = None):
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)
            
            # symbol 컬럼이 없으면 추가 (쿼리에 symbol이 포함되어야 함)
            if 'symbol' not in df.columns and params and len(params) > 0:
                # 쿼리의 첫 번째 파라미터가 symbol이라고 가정
                df['symbol'] = params[0] 
            
            df = standardize_dataframe(df)
            return df

if __name__ == "__main__":
    conn = get_connection()
    if conn:
        init_db(conn)
        conn.close() 
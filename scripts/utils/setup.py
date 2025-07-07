#!/usr/bin/env python3
"""
프로젝트 초기 설정 스크립트
- 가상환경 확인
- 필수 디렉토리 생성
- 데이터베이스 초기화
- 환경 설정 파일 검증
"""

import os
import sys
import sqlite3
from pathlib import Path
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_virtual_env():
    """가상환경 활성화 여부 체크"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        logger.info("✅ 가상환경이 활성화되어 있습니다.")
        logger.info(f"Python 경로: {sys.executable}")
        return True
    else:
        logger.error("❌ 가상환경이 활성화되어 있지 않습니다!")
        logger.error("가상환경을 활성화한 후 다시 실행하세요.")
        return False

def create_directories():
    """필수 디렉토리 생성"""
    directories = [
        'data/historical',
        'data/logs',
        'logs',
        'streamlit_app/pages',
        'streamlit_app/static'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 디렉토리 생성: {directory}")

def initialize_database():
    """SQLite 데이터베이스 초기화"""
    db_path = Path('data/trading.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 주식 데이터 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_data (
                symbol TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (symbol, date)
            )
        ''')
        
        # 기술적 지표 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indicators (
                symbol TEXT,
                date TEXT,
                rsi REAL,
                macd REAL,
                macd_signal REAL,
                macd_histogram REAL,
                bb_upper REAL,
                bb_middle REAL,
                bb_lower REAL,
                atr REAL,
                PRIMARY KEY (symbol, date)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("💾 데이터베이스 초기화 완료")
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")

def check_env_file():
    """환경 설정 파일 검증"""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists():
        if env_example.exists():
            logger.warning("⚠️ .env 파일이 없습니다. .env.example을 참조하여 생성하세요.")
        else:
            # .env.example 파일 생성
            with open('.env.example', 'w', encoding='utf-8') as f:
                f.write('''# 키움증권 API 설정
KIWOOM_API_KEY=your_api_key_here
KIWOOM_SECRET_KEY=your_secret_key_here

# 데이터베이스 설정
DB_PATH=data/trading.db

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE=logs/main.log

# 백테스팅 설정
DEFAULT_COMMISSION=0.00015
DEFAULT_TAX=0.0025
''')
            logger.info("📄 .env.example 파일 생성")
    else:
        logger.info("✅ .env 파일 확인됨")

def main():
    """메인 실행 함수"""
    logger.info("🚀 프로젝트 초기 설정 시작")
    
    # 1. 가상환경 체크
    if not check_virtual_env():
        sys.exit(1)
    
    # 2. 디렉토리 생성
    create_directories()
    
    # 3. 데이터베이스 초기화
    initialize_database()
    
    # 4. 환경 설정 파일 검증
    check_env_file()
    
    logger.info("🎉 프로젝트 초기 설정 완료!")
    logger.info("다음 단계:")
    logger.info("1. .env 파일에 API 키 설정")
    logger.info("2. pip install -r requirements.txt")
    logger.info("3. python scripts/data_update.py")

if __name__ == "__main__":
    main() 
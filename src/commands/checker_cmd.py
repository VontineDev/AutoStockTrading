import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def check_dependencies():
    """필수 패키지 설치 확인"""
    required_packages = [
        ("talib", "TA-Lib"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("streamlit", "streamlit"),
        ("plotly", "plotly"),
        ("sqlite3", "sqlite3 (내장)"),
    ]
    missing_packages = []
    for package, display_name in required_packages:
        try:
            if package == "sqlite3":
                import sqlite3
            else:
                __import__(package)
            logger.info(f"✅ {display_name}")
        except ImportError:
            missing_packages.append(display_name)
            logger.error(f"❌ {display_name} - 설치되지 않음")
    if missing_packages:
        logger.error(f"누락된 패키지: {', '.join(missing_packages)}")
        logger.info("다음 명령어로 설치하세요:")
        logger.info("pip install -r requirements.txt")
        return False
    logger.info("✅ 모든 필수 패키지가 설치되어 있습니다.")
    return True

def run_check_data(args=None):
    """간단한 데이터 상태 확인"""
    try:
        from src.data.updater import StockDataUpdater
        import sqlite3
        import pandas as pd

        updater = StockDataUpdater()

        if not Path(updater.db_path).exists():
            logger.error("❌ 데이터베이스가 없습니다.")
            logger.info("다음 명령어로 데이터를 먼저 수집하세요:")
            logger.info("python src/main.py update-data --period 6m")
            return

        logger.info("🔍 데이터 상태 확인 중...")
        
        # 기본 데이터베이스 정보 확인
        with sqlite3.connect(updater.db_path) as conn:
            # 종목 수 확인
            symbols_count = pd.read_sql_query("SELECT COUNT(*) as count FROM stock_info", conn).iloc[0]['count']
            logger.info(f"📊 등록된 종목 수: {symbols_count:,}개")
            
            # 데이터 보유 종목 수 확인
            data_symbols_count = pd.read_sql_query("SELECT COUNT(DISTINCT symbol) as count FROM stock_ohlcv", conn).iloc[0]['count']
            logger.info(f"📈 데이터 보유 종목 수: {data_symbols_count:,}개")
            
            # 최신 데이터 날짜 확인
            if data_symbols_count > 0:
                latest_date = pd.read_sql_query("SELECT MAX(date) as latest FROM stock_ohlcv", conn).iloc[0]['latest']
                logger.info(f"📅 최신 데이터 날짜: {latest_date}")
                
                # 총 데이터 포인트 수
                total_data_points = pd.read_sql_query("SELECT COUNT(*) as count FROM stock_ohlcv", conn).iloc[0]['count']
                logger.info(f"💾 총 데이터 포인트: {total_data_points:,}개")

        logger.info(f"\n" + "=" * 50)
        logger.info("💡 데이터 업데이트 권장사항:")
        logger.info("=" * 50)

        if data_symbols_count == 0:
            logger.info("⚠️  데이터가 없습니다.")
            logger.info("   데이터를 수집하세요:")
            logger.info("   python src/main.py update-data --period 1y")
        elif data_symbols_count < 10:
            logger.info("⚠️  데이터 보유 종목이 부족합니다.")
            logger.info("   더 많은 종목 데이터 수집을 권장합니다:")
            logger.info("   python src/main.py update-data --period 6m")
        elif data_symbols_count < 100:
            logger.info("✅ 소규모 백테스팅에 적합합니다.")
            logger.info("   추가 종목 수집으로 더 정확한 분석이 가능합니다:")
            logger.info("   python src/main.py update-data --period 1y")
        else:
            logger.info("🎉 대규모 백테스팅에 최적화된 상태입니다!")
            logger.info("   병렬 백테스팅으로 효율적인 분석을 진행하세요:")
            logger.info("   python src/main.py backtest --parallel --workers 8")

    except Exception as e:
        logger.error(f"데이터 상태 확인 실패: {e}")
        logger.info("다음 명령어로 데이터를 먼저 수집하세요:")
        logger.info("python src/main.py update-data --period 6m")
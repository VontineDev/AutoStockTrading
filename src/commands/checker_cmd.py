import logging
from pathlib import Path
from src.utils.display_utils import display_data_summary

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

def run_check_data(args):
    """종합 데이터 상태 확인 (check_data_status.py 기능 통합)"""
    try:
        from scripts.data_update import StockDataUpdater

        updater = StockDataUpdater()

        if not Path(updater.db_path).exists():
            logger.error("❌ 데이터베이스가 없습니다.")
            logger.info("다음 명령어로 데이터를 먼저 수집하세요:")
            logger.info("python src/main.py update-data --top-kospi 50 --period 6m")
            return

        logger.info("🔍 데이터 상태 종합 분석 중...")
        display_data_summary(updater, include_backtest_analysis=True)

        comprehensive_status = updater.get_comprehensive_status(
            include_backtest_analysis=True
        )
        basic = comprehensive_status.get("basic_summary", {})
        backtest = comprehensive_status.get("backtest_analysis", {})
        valid_count = backtest.get("valid_symbols_count", 0)
        total_count = basic.get("symbols_count", 0)

        logger.info(f"\n" + "=" * 50)
        logger.info("💡 권장사항")
        logger.info("=" * 50)

        if valid_count == 0:
            logger.info("⚠️  백테스팅 가능한 종목이 없습니다.")
            logger.info("   데이터를 더 수집하거나 기간을 늘려보세요:")
            logger.info("   python src/main.py update-data --top-kospi 100 --period 1y")
        elif valid_count < 10:
            logger.info("⚠️  백테스팅 가능한 종목이 부족합니다.")
            logger.info("   더 많은 종목 데이터 수집을 권장합니다:")
            logger.info("   python src/main.py update-data --top-kospi 50 --period 6m")
        elif valid_count < 50:
            logger.info("✅ 소규모 백테스팅에 적합합니다.")
            logger.info("   추가 종목 수집으로 더 정확한 분석이 가능합니다:")
            logger.info("   python src/main.py update-data --top-kospi 100 --period 1y")
        else:
            logger.info("🎉 대규모 백테스팅에 최적화된 상태입니다!")
            logger.info("   병렬 백테스팅으로 효율적인 분석을 진행하세요:")
            logger.info(
                "   python src/main.py backtest --all-kospi --parallel --workers 8"
            )

        test_symbols = backtest.get("test_symbols_string", "")
        if test_symbols:
            logger.info(f"\n🚀 바로 시작할 수 있는 명령어:")
            logger.info(
                f"   python src/main.py backtest --symbols {' '.join(backtest.get('test_symbols', [])[:5])}"
            )

    except Exception as e:
        logger.error(f"데이터 상태 확인 실패: {e}")
        logger.info("기본 상태 확인을 시도하세요:")
        logger.info("python src/main.py update-data --summary")
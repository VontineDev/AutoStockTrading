import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def parse_date(date_str: str) -> str:
    """날짜 문자열을 YYYYMMDD 형식으로 변환"""
    if not date_str:
        return None
    if len(date_str) == 8 and date_str.isdigit():
        return date_str
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y%m%d")
    except ValueError:
        raise ValueError(f"잘못된 날짜 형식: {date_str}. YYYY-MM-DD 또는 YYYYMMDD 형식을 사용하세요.")

def calculate_date_range(args) -> tuple:
    """인자를 기반으로 시작/종료 날짜 계산"""
    end_date = datetime.now()
    if hasattr(args, "end_date") and args.end_date:
        end_date_str = parse_date(args.end_date)
        end_date = datetime.strptime(end_date_str, "%Y%m%d")

    if hasattr(args, "start_date") and args.start_date:
        start_date_str = parse_date(args.start_date)
        start_date = datetime.strptime(start_date_str, "%Y%m%d")
    elif hasattr(args, "days") and args.days:
        start_date = end_date - timedelta(days=args.days)
    else:
        period = getattr(args, "period", "1y")
        period_days = {"1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365, "2y": 730}
        days = period_days.get(period, 365)
        start_date = end_date - timedelta(days=days)

    return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")

def run_data_update(args):
    """데이터 업데이트 실행"""
    try:
        from src.data.updater import StockDataUpdater

        updater = StockDataUpdater()

        if args.api_status:
            _show_api_status(updater)
            return

        if args.summary:
            _show_data_summary(updater, getattr(args, "backtest_analysis", False))
            return

        # 날짜 계산
        today = datetime.now().strftime("%Y%m%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

        if args.yesterday_only:
            logger.info(f"=== 전날 데이터 업데이트 모드: {yesterday} ===")
            if args.symbols:
                # 특정 종목 리스트에 대한 전날 업데이트
                for symbol in args.symbols:
                    updater.update_specific_stock_data(symbol, yesterday, yesterday)
            else:
                # 전체 시장 전날 업데이트
                updater.update_daily_market_data(yesterday)
            logger.info(f"전날({yesterday}) 데이터 업데이트 요청 완료.")
            return

        start_date, end_date = calculate_date_range(args)

        if args.symbols:
            # 특정 종목 리스트 기간 데이터 업데이트
            logger.info(f"=== 특정 종목 기간 데이터 업데이트 모드: {start_date} ~ {end_date} ===")
            for symbol in args.symbols:
                updater.update_specific_stock_data(symbol, start_date, end_date)
        elif getattr(args, "all_kospi", False):
            # KOSPI 전체 종목 기간 데이터 업데이트
            logger.info(f"=== KOSPI 전체 종목 기간 데이터 업데이트 모드: {start_date} ~ {end_date} ===")
            # updater.get_all_tickers()는 현재 모든 시장의 티커를 반환하므로, KOSPI만 필터링
            all_tickers = updater.get_all_tickers()
            kospi_tickers = [t for t in all_tickers if t.startswith('0')] # KOSPI 티커는 보통 '0'으로 시작한다고 가정
            for symbol in kospi_tickers:
                updater.update_specific_stock_data(symbol, start_date, end_date)
        elif getattr(args, "top_kospi", 0) > 0:
            # KOSPI 상위 N개 종목 기간 데이터 업데이트
            top_kospi_tickers = updater.get_kospi_top_symbols(args.top_kospi)
            logger.info(f"=== KOSPI 상위 {args.top_kospi}개 종목 기간 데이터 업데이트 모드 ({len(top_kospi_tickers)}개): {start_date} ~ {end_date} ===")
            for symbol in top_kospi_tickers:
                updater.update_specific_stock_data(symbol, start_date, end_date)
        else:
            # 전체 종목 기간 데이터 업데이트 (기본 동작)
            logger.info(f"=== 전체 종목 기간 데이터 업데이트 모드: {start_date} ~ {end_date} ===")
            updater.update_all_historical_data(start_date, end_date)

        logger.info("데이터 업데이트 요청 완료.")

    except Exception as e:
        logger.error(f"데이터 업데이트 실패: {e}")
        logger.info(f"오류: {e}")

def _show_api_status(updater):
    """API 사용량 현황 표시"""
    status = updater.get_api_usage_status()
    logger.info("\n=== API 사용량 현황 ===")
    if status:
        for key, value in status.items():
            logger.info(f"{key}: {value}")
    else:
        logger.info("API 사용량 현황 정보를 가져올 수 없습니다.")

def _show_data_summary(updater, include_backtest):
    """데이터 요약 정보 표시"""
    logger.info("\n=== 데이터 요약 정보 ===")
    logger.info("데이터 요약 정보는 아직 구현되지 않았습니다. (updater.py에 관련 메서드 구현 필요)")

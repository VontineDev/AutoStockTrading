import logging
from typing import Dict, Any
from scripts.data_update import StockDataUpdater

logger = logging.getLogger(__name__)

def display_data_summary(updater: StockDataUpdater, include_backtest_analysis: bool = False):
    """
    데이터베이스 현황 및 백테스팅 적합성 분석 결과를 출력합니다.
    """
    if include_backtest_analysis:
        comprehensive_status = updater.get_comprehensive_status(include_backtest_analysis=True)
        
        # 기본 요약
        basic = comprehensive_status.get('basic_summary', {})
        logger.info("\n=== 📊 데이터베이스 기본 현황 ===")
        logger.info(f"종목 수: {basic.get('symbols_count', 0):,}개")
        logger.info(f"데이터 기간: {basic.get('date_range', ('N/A', 'N/A'))[0]} ~ {basic.get('date_range', ('N/A', 'N/A'))[1]}")
        logger.info(f"총 데이터: {basic.get('total_records', 0):,}건")
        logger.info(f"DB 경로: {basic.get('db_path', 'N/A')}")
        
        # 백테스팅 분석
        backtest = comprehensive_status.get('backtest_analysis', {})
        if backtest:
            logger.info(f"\n=== 🚀 백테스팅 적합성 분석 ===")
            logger.info(f"분석 기간: {backtest.get('analysis_period', 'N/A')}")
            logger.info(f"최소 데이터 요구: {backtest.get('min_data_days', 0)}일")
            logger.info(f"백테스팅 가능 종목: {backtest.get('valid_symbols_count', 0):,}개 ({backtest.get('valid_percentage', 0)}%)")
            
            # 상위 종목 표시
            top_symbols = backtest.get('top_symbols', [])
            if top_symbols:
                logger.info(f"\n📈 데이터가 가장 충실한 상위 {len(top_symbols)}개 종목:")
                for i, symbol_info in enumerate(top_symbols[:10], 1):
                    symbol = symbol_info['symbol']
                    days = symbol_info['days']
                    start_date = symbol_info['start_date']
                    end_date = symbol_info['end_date']
                    logger.info(f"  {i:2d}. {symbol}: {days}일 ({start_date} ~ {end_date})")
                
                if len(top_symbols) > 10:
                    logger.info(f"     ... 외 {len(top_symbols) - 10}개 종목")
            
            # 테스트 추천 종목
            test_symbols = backtest.get('test_symbols_string', '')
            if test_symbols:
                logger.info(f"\n🎯 백테스팅 테스트 추천 종목 (상위 10개):")
                logger.info(f"   {test_symbols}")
        
        # API 상태
        api_status = comprehensive_status.get('api_status', {})
        if api_status:
            logger.info(f"\n=== 🔌 API 사용 현황 ===")
            logger.info(f"세션 호출: {api_status.get('api_calls', 0)}회")
            logger.info(f"세션 시간: {api_status.get('session_duration', 'N/A')}")
            logger.info(f"분당 호출: {api_status.get('calls_per_minute', 0):.1f}회")
            
    else:
        # 기존 간단한 요약
        summary = updater.get_data_summary()
        logger.info("\n=== 데이터베이스 현황 ===")
        logger.info(f"종목 수: {summary.get('symbols_count', 0):,}개")
        logger.info(f"데이터 기간: {summary.get('date_range', ('N/A', 'N/A'))[0]} ~ {summary.get('date_range', ('N/A', 'N/A'))[1]}")
        logger.info(f"총 데이터: {summary.get('total_records', 0):,}건")

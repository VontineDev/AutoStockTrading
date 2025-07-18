import logging
from datetime import datetime, timedelta
from typing import Optional
import time

logger = logging.getLogger(__name__)

def parse_date(date_str: str) -> Optional[str]:
    """날짜 문자열을 YYYYMMDD 형식으로 변환합니다."""
    if not date_str:
        return None
    if len(date_str) == 8 and date_str.isdigit():
        return date_str
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d")
    except ValueError:
        raise ValueError(f"잘못된 날짜 형식: {date_str}. YYYY-MM-DD 또는 YYYYMMDD 형식을 사용하세요.")

def calculate_date_range(args) -> tuple:
    """CLI 인자를 기반으로 데이터 조회 시작일과 종료일을 계산합니다."""
    end_date = datetime.now()
    if hasattr(args, "end_date") and args.end_date:
        parsed_end_date = parse_date(args.end_date)
        if parsed_end_date:
            end_date = datetime.strptime(parsed_end_date, "%Y%m%d")

    if hasattr(args, "start_date") and args.start_date:
        parsed_start_date = parse_date(args.start_date)
        if parsed_start_date:
            start_date = datetime.strptime(parsed_start_date, "%Y%m%d")
        else:
            start_date = end_date - timedelta(days=365)
    elif hasattr(args, "period") and args.period:
        # period 옵션 처리
        period_days = {
            "1w": 7,
            "1m": 30,
            "3m": 90,
            "6m": 180,
            "1y": 365,
            "2y": 730
        }
        days = period_days.get(args.period, 365)
        start_date = end_date - timedelta(days=days)
    elif hasattr(args, "days") and args.days:
        start_date = end_date - timedelta(days=args.days)
    else:
        # 기본값: 1년
        start_date = end_date - timedelta(days=365)

    return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")

def run_data_update(args):
    """데이터 업데이트 명령 실행"""
    from src.data.updater import StockDataUpdater, OptimizedDataUpdateConfig
    
    try:
        # 병렬 처리 설정 확인
        enable_parallel = getattr(args, 'parallel', False)
        max_workers = getattr(args, 'max_workers', 4)
        batch_size = getattr(args, 'batch_size', 30)
        enable_cache = getattr(args, 'enable_cache', True)
        api_delay = getattr(args, 'api_delay', 0.3)
        incremental = getattr(args, 'incremental', True)
        
        if enable_parallel:
            logger.info(f"=== 병렬 처리 모드 활성화 ===")
            logger.info(f"설정: 워커 {max_workers}개, 배치크기 {batch_size}, 캐싱 {'활성화' if enable_cache else '비활성화'}")
            
            # 최적화 설정 생성
            optimization_config = OptimizedDataUpdateConfig(
                max_workers=max_workers,
                enable_cache=enable_cache,
                batch_size=batch_size,
                api_delay=api_delay,
                incremental_update=incremental,
                adaptive_batch_size=True,  # 메모리 사용량에 따라 배치 크기 자동 조정
                check_latest_data=True,    # 최신 데이터 확인
            )
            
            updater = StockDataUpdater(optimization_config=optimization_config)
        else:
            logger.info("=== 순차 처리 모드 ===")
            updater = StockDataUpdater()

        # 종목 정보 업데이트
        if hasattr(args, 'update_symbols') and args.update_symbols:
            logger.info("=== 전체 종목 정보 업데이트 ===")
            updater.update_all_symbol_info_with_krx()
            logger.info("=== 전체 종목 정보 업데이트 완료 ===")
            return

        # 시가총액 데이터 업데이트
        if hasattr(args, 'market_cap') and args.market_cap:
            logger.info("=== 시가총액 데이터 업데이트 ===")
            updater.update_market_cap_data()
            logger.info("=== 시가총액 데이터 업데이트 완료 ===")
            return

        # 어제 데이터만 업데이트 (Ultra-Fast)
        if hasattr(args, 'yesterday_only') and args.yesterday_only:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            logger.info(f"=== 어제 데이터 업데이트: {yesterday} ===")
            updater.update_daily_market_data(yesterday)
            logger.info("=== 어제 데이터 업데이트 완료 ===")
            return

        # 특정일 전체 시장 데이터 업데이트
        if hasattr(args, 'daily_market') and args.daily_market:
            target_date = args.daily_market
            if target_date.lower() == 'today':
                target_date = datetime.now().strftime("%Y%m%d")
            elif target_date.lower() == 'yesterday':
                target_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            else:
                parsed_date = parse_date(target_date)
                if not parsed_date:
                    logger.error(f"잘못된 날짜 형식: {target_date}")
                    return
                target_date = parsed_date
            
            logger.info(f"=== 특정일 전체 시장 데이터 업데이트: {target_date} ===")
            updater.update_daily_market_data(target_date)
            logger.info("=== 특정일 전체 시장 데이터 업데이트 완료 ===")
            return

        start_date, end_date = calculate_date_range(args)

        # 특정 종목 데이터 업데이트
        if args.symbols:
            logger.info(f"=== 특정 종목 데이터 업데이트: {start_date} ~ {end_date} ===")
            
            # 병렬 처리 임계값 확인 (3개 이상일 때 병렬 처리 사용)
            use_parallel = enable_parallel and len(args.symbols) >= 3
            
            if use_parallel:
                logger.info(f"병렬 처리로 {len(args.symbols)}개 종목 업데이트")
                
                # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
                start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
                end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
                
                results = updater.update_multiple_symbols_parallel(
                    symbols=args.symbols,
                    start_date=start_date_formatted,
                    end_date=end_date_formatted,
                    force_update=getattr(args, 'force', False),
                    max_workers=max_workers
                )
                
                # 결과 요약 출력
                success_count = sum(1 for success in results["results"].values() if success)
                logger.info(f"병렬 처리 완료: {success_count}/{len(args.symbols)} 성공")
                logger.info(f"총 소요 시간: {results['total_time']:.2f}초")
                
                # 캐싱 통계 출력
                if "cache_stats" in results:
                    cache_stats = results["cache_stats"]
                    logger.info(f"캐시 효과 - 건너뛴 종목: {cache_stats.get('skipped_symbols', 0)}")
                    logger.info(f"증분 업데이트: {cache_stats.get('incremental_updates', 0)}")
                    logger.info(f"전체 업데이트: {cache_stats.get('full_updates', 0)}")
                
                # 배치 처리 통계 출력
                if "batch_stats" in results:
                    batch_stats = results["batch_stats"]
                    avg_speed = batch_stats.get("avg_symbols_per_second", 0)
                    logger.info(f"처리 속도: {avg_speed:.2f} 종목/초")
                
            else:
                # 순차 처리 사용
                logger.info(f"순차 처리로 {len(args.symbols)}개 종목 업데이트")
                for symbol in args.symbols:
                    updater.update_specific_stock_data(symbol, start_date, end_date)
        
        # 전체 시장 데이터 업데이트
        else:
            logger.info(f"=== 전체 시장 데이터 업데이트: {start_date} ~ {end_date} ===")
            
            if enable_parallel:
                # 병렬 처리로 전체 종목 업데이트
                logger.info("병렬 처리로 전체 종목 업데이트")
                
                # 데이터베이스에서 전체 종목 조회
                import sqlite3
                import pandas as pd
                
                with sqlite3.connect(updater.db_path) as conn:
                    df = pd.read_sql_query("SELECT symbol FROM stock_info", conn)
                    all_symbols = df['symbol'].tolist()
                
                if all_symbols:
                    logger.info(f"전체 {len(all_symbols)}개 종목 병렬 처리 시작")
                    
                    # 날짜 형식 변환
                    start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
                    end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
                    
                    # 진행률 콜백 함수 정의
                    def progress_callback(progress, completed, total, start_time):
                        elapsed = time.time() - start_time
                        eta = (elapsed / progress * (1 - progress)) if progress > 0 else 0
                        logger.info(f"진행률: {progress:.1%} ({completed}/{total}) - 경과: {elapsed:.1f}초, 남은시간: {eta:.1f}초")
                    
                    # 최적화 설정에 진행률 콜백 추가
                    if enable_parallel:
                        updater.optimization_config.progress_callback = progress_callback
                    
                    results = updater.update_multiple_symbols_parallel(
                        symbols=all_symbols,
                        start_date=start_date_formatted,
                        end_date=end_date_formatted,
                        force_update=getattr(args, 'force', False),
                        max_workers=max_workers
                    )
                    
                    # 최종 결과 요약
                    success_count = sum(1 for success in results["results"].values() if success)
                    total_time = results['total_time']
                    avg_speed = success_count / total_time if total_time > 0 else 0
                    
                    logger.info("=== 전체 종목 병렬 처리 완료 ===")
                    logger.info(f"성공: {success_count}/{len(all_symbols)} ({success_count/len(all_symbols)*100:.1f}%)")
                    logger.info(f"총 소요 시간: {total_time:.2f}초")
                    logger.info(f"평균 처리 속도: {avg_speed:.2f} 종목/초")
                    
                    # 최적화 통계 출력
                    if hasattr(updater, 'get_optimization_stats'):
                        stats = updater.get_optimization_stats()
                        logger.info("=== 최적화 효과 ===")
                        cache_stats = stats.get('cache_stats', {})
                        logger.info(f"캐시 건너뛴 종목: {cache_stats.get('skipped_symbols', 0)}")
                        logger.info(f"증분 업데이트: {cache_stats.get('incremental_updates', 0)}")
                        logger.info(f"전체 업데이트: {cache_stats.get('full_updates', 0)}")
                        
                        batch_stats = stats.get('batch_stats', {})
                        logger.info(f"총 배치 수: {batch_stats.get('total_batches', 0)}")
                        logger.info(f"API 호출 수: {batch_stats.get('api_calls', 0)}")
                else:
                    logger.warning("데이터베이스에 종목 정보가 없습니다. 먼저 --update-symbols를 실행하세요.")
            else:
                # 기존 순차 처리 방식
                updater.update_all_historical_data(start_date, end_date)

        logger.info("데이터 업데이트 작업 완료.")

    except Exception as e:
        logger.error(f"데이터 업데이트 중 오류 발생: {e}", exc_info=True)
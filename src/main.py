#!/usr/bin/env python3
"""
TA-Lib 스윙 트레이딩 자동매매 시스템 메인 진입점

pykrx + TA-Lib 기반의 100만원 규모 스윙 트레이딩 시스템
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
import yaml
from dotenv import load_dotenv
import pandas as pd

# 프로젝트 루트 디렉토리를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 로깅 설정 (print() 대신 사용)
logger = logging.getLogger(__name__)

# 환경변수 로드
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"환경변수 로드 완료: {env_path}")
else:
    logger.warning(f"환경변수 파일 없음: {env_path}")

def setup_logging(config: dict):
    """로깅 설정"""
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 로그 디렉토리 생성
    log_dir = PROJECT_ROOT / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # 로깅 설정
    handlers = [
        logging.StreamHandler(sys.stdout)
    ]
    
    if log_config.get('file_logging', {}).get('enabled', True):
        log_file = log_dir / 'main.log'
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True
    )
    
    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('plotly').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def load_config() -> dict:
    """설정 파일 로드"""
    config_path = PROJECT_ROOT / 'config.yaml'
    
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"설정 파일 로드 실패: {e}")
    
    # 기본 설정 반환
    return {
        'project': {
            'name': 'TA-Lib 스윙 트레이딩',
            'version': '1.0.0'
        },
        'logging': {
            'level': 'INFO'
        }
    }

def setup_environment():
    """환경 설정"""
    try:
        from dotenv import load_dotenv
        env_path = PROJECT_ROOT / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"환경변수 로드 완료: {env_path}")
        else:
            logger.warning("환경변수 파일(.env)이 없습니다. 기본 설정을 사용합니다.")
    except ImportError:
        logger.warning("python-dotenv가 설치되지 않았습니다. 환경변수 로드를 건너뜁니다.")

def check_dependencies():
    """필수 패키지 설치 확인"""
    required_packages = [
        ('talib', 'TA-Lib'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('pykrx', 'pykrx'),
        ('streamlit', 'streamlit'),
        ('plotly', 'plotly'),
        ('sqlite3', 'sqlite3 (내장)')
    ]
    
    missing_packages = []
    
    for package, display_name in required_packages:
        try:
            if package == 'sqlite3':
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

def parse_date(date_str: str) -> str:
    """날짜 문자열을 YYYYMMDD 형식으로 변환"""
    if not date_str:
        return None
    
    # 이미 YYYYMMDD 형식인 경우
    if len(date_str) == 8 and date_str.isdigit():
        return date_str
    
    # YYYY-MM-DD 형식인 경우
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%Y%m%d')
    except ValueError:
        raise ValueError(f"잘못된 날짜 형식: {date_str}. YYYY-MM-DD 또는 YYYYMMDD 형식을 사용하세요.")

def calculate_date_range(args) -> tuple:
    """인자를 기반으로 시작/종료 날짜 계산"""
    end_date = datetime.now()
    
    # 종료 날짜 설정
    if hasattr(args, 'end_date') and args.end_date:
        end_date_str = parse_date(args.end_date)
        end_date = datetime.strptime(end_date_str, '%Y%m%d')
    
    # 시작 날짜 계산 우선순위: start_date > days > period
    if hasattr(args, 'start_date') and args.start_date:
        # 직접 시작 날짜 지정
        start_date_str = parse_date(args.start_date)
        start_date = datetime.strptime(start_date_str, '%Y%m%d')
    elif hasattr(args, 'days') and args.days:
        # 현재부터 N일 전
        start_date = end_date - timedelta(days=args.days)
    else:
        # 기본 기간 설정
        period = getattr(args, 'period', '1y')
        period_days = {
            '1w': 7,
            '1m': 30,
            '3m': 90,
            '6m': 180,
            '1y': 365,  # 기본값
            '2y': 730
        }
        days = period_days.get(period, 365)
        start_date = end_date - timedelta(days=days)
    
    return start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d')

def run_data_update(args):
    """데이터 업데이트 실행"""
    try:
        from scripts.data_update import StockDataUpdater
        
        updater = StockDataUpdater()
        
        # API 사용량 현황만 표시
        if args.api_status:
            status = updater.get_api_usage_status()
            logger.info("\n=== API 사용량 현황 ===")
            for key, value in status.items():
                logger.info(f"{key}: {value}")
            return
        
        # 데이터베이스 현황만 표시
        if hasattr(args, 'summary') and args.summary:
            summary = updater.get_data_summary()
            logger.info("\n=== 데이터베이스 현황 ===")
            logger.info(f"종목 수: {summary.get('symbols_count', 0):,}개")
            logger.info(f"데이터 기간: {summary.get('date_range', ('N/A', 'N/A'))[0]} ~ {summary.get('date_range', ('N/A', 'N/A'))[1]}")
            logger.info(f"총 데이터: {summary.get('total_records', 0):,}건")
            return
        
        # 전날 데이터만 업데이트
        if hasattr(args, 'yesterday_only') and args.yesterday_only:
            logger.info("=== 전날 데이터 업데이트 모드 ===")
            
            if args.top_kospi and args.top_kospi > 0:
                # 코스피 상위 종목
                results = updater.update_yesterday_data(use_kospi_top=True, top_limit=args.top_kospi)
            elif args.symbols:
                # 지정된 종목들
                results = updater.update_yesterday_data(symbols=args.symbols)
            else:
                # 기존 등록된 모든 종목
                results = updater.update_yesterday_data()
            
            # 결과 요약 출력
            logger.info(f"\n전날({results['date']}) 데이터 업데이트 완료:")
            logger.info(f"- 성공: {results['success_count']}/{results['total_symbols']} 종목")
            logger.info(f"- 신규 데이터: {results['new_data_count']}건")
            logger.info(f"- 중복 건너뜀: {results['duplicate_count']}건")
            
            if results['failed_symbols']:
                logger.info(f"- 실패 종목: {', '.join(results['failed_symbols'])}")
            
            return
        
        # 종목 선택
        if args.top_kospi and args.top_kospi > 0:
            # 코스피 상위 종목
            symbols = updater.get_kospi_top_symbols(args.top_kospi)
            logger.info(f"코스피 상위 {len(symbols)}개 종목 데이터 수집")
        elif args.symbols:
            symbols = args.symbols
            logger.info(f"지정 종목 {len(symbols)}개 데이터 수집")
        else:
            # 기본값: 코스피 상위 30개
            symbols = updater.get_kospi_top_symbols(30)
            logger.info("기본값: 코스피 상위 30개 종목 데이터 수집")
        
        # 날짜 범위 계산
        try:
            start_date, end_date = calculate_date_range(args)
            
            # 기간 계산 및 표시
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            days_diff = (end_dt - start_dt).days
            
            logger.info(f"\n=== 데이터 수집 범위 ===")
            logger.info(f"수집 기간: {start_date} ~ {end_date} ({days_diff}일)")
            logger.info(f"대상 종목: {len(symbols)}개")
            
            # 날짜 설정 방식 표시
            if hasattr(args, 'start_date') and args.start_date:
                logger.info(f"날짜 설정: 직접 지정 ({args.start_date} ~ {getattr(args, 'end_date', '오늘')})")
            elif hasattr(args, 'days') and args.days:
                logger.info(f"날짜 설정: 최근 {args.days}일")
            else:
                period = getattr(args, 'period', '1y')
                period_names = {'1w': '1주', '1m': '1개월', '3m': '3개월', '6m': '6개월', '1y': '1년', '2y': '2년'}
                logger.info(f"날짜 설정: 기본 기간 ({period_names.get(period, period)})")
                
        except ValueError as e:
            logger.error(f"날짜 설정 오류: {e}")
            return
        
        # 예상 소요 시간 안내
        if hasattr(args, 'yesterday_only') and not args.yesterday_only:
            if len(symbols) > 10 and days_diff > 30:
                estimated_time = len(symbols) * 2  # 종목당 약 2분 예상
                logger.info(f"예상 소요 시간: 약 {estimated_time}분")
                logger.info("전날 데이터만 필요한 경우 --yesterday-only 옵션을 사용하세요 (Ultra-Fast, 4-5초 완료)")
        
        # 데이터 수집 실행 (병렬/순차 처리 선택)
        if hasattr(updater, 'update_multiple_symbols'):
            # 병렬 처리 여부 결정
            if getattr(args, 'parallel', False):
                workers = getattr(args, 'workers', 5)
                logger.info(f"\n🚀 병렬 처리 모드 활성화 (워커: {workers}개)")
                if hasattr(updater, 'update_multiple_symbols_parallel'):
                    results = updater.update_multiple_symbols_parallel(
                        symbols, start_date, end_date, 
                        force_update=getattr(args, 'force', False),
                        max_workers=workers
                    )
                else:
                    logger.error("❌ 병렬 처리가 지원되지 않습니다. 순차 처리로 전환됩니다.")
                    results = updater.update_multiple_symbols(symbols, start_date, end_date, 
                                                            force_update=getattr(args, 'force', False))
            else:
                # 순차 처리 (기본)
                logger.info(f"\n🐌 순차 처리 모드 (기본)")
                results = updater.update_multiple_symbols(symbols, start_date, end_date, 
                                                        force_update=getattr(args, 'force', False))
            
            # 결과 요약
            success_count = sum(1 for success in results.values() if success)
            logger.info(f"\n=== 데이터 수집 완료 ===")
            logger.info(f"성공: {success_count}/{len(symbols)} 종목")
            
            # 실패한 종목 표시
            failed_symbols = [symbol for symbol, success in results.items() if not success]
            if failed_symbols:
                logger.info(f"실패: {', '.join(failed_symbols)}")
        else:
            # 기존 방식: 개별 종목 업데이트
            for i, symbol in enumerate(symbols, 1):
                logger.info(f"[{i}/{len(symbols)}] {symbol} 처리 중...")
                try:
                    updater.update_symbol(symbol, start_date, end_date, 
                                        force_update=getattr(args, 'force', False))
                    logger.info(f"  ✅ 완료")
                except Exception as e:
                    logger.error(f"  ❌ 실패: {e}")
        
        # API 사용량 현황
        status = updater.get_api_usage_status()
        logger.info(f"\nAPI 사용량: {status.get('total_calls', 0)}회 호출")
        
    except Exception as e:
        logger.error(f"데이터 업데이트 실패: {e}")
        logger.info(f"오류: {e}")

def run_backtest(args):
    """백테스팅 실행 (병렬 처리 지원)"""
    try:
        from src.strategies.macd_strategy import MACDStrategy
        from src.strategies.rsi_strategy import RSIStrategy
        from src.strategies.bollinger_band_strategy import BollingerBandStrategy
        from src.strategies.moving_average_strategy import MovingAverageStrategy
        from src.trading.backtest import BacktestEngine, BacktestConfig
        import pandas as pd
        import sqlite3
        import time
        from datetime import datetime, timedelta
        from pathlib import Path
        import json
        
        logger.info("🚀 백테스팅 시작...")
        
        # 데이터베이스 확인
        db_path = PROJECT_ROOT / 'data' / 'trading.db'
        if not db_path.exists():
            logger.error("❌ 데이터베이스가 없습니다. 먼저 데이터를 업데이트하세요.")
            logger.info("python src/main.py update-data --top-kospi 962 --period 2y --parallel")
            return
        
        # 종목 선택 로직
        symbols = []
        if args.all_kospi:
            logger.info("📊 코스피 전체 종목 백테스팅 모드")
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT symbol FROM stock_data ORDER BY symbol")
                symbols = [row[0] for row in cursor.fetchall()]
            logger.info(f"코스피 전체 {len(symbols)}개 종목 대상")
        elif args.top_kospi:
            logger.info(f"📊 코스피 상위 {args.top_kospi}개 종목 백테스팅")
            # 코스피 상위 종목 가져오기 (pykrx 사용)
            try:
                from scripts.data_update import StockDataUpdater
                updater = StockDataUpdater()
                symbols = updater.get_kospi_top_symbols(args.top_kospi)
            except:
                # 대체 방법: 데이터베이스에서 데이터가 많은 종목 순으로
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT symbol, COUNT(*) as count 
                        FROM stock_data 
                        GROUP BY symbol 
                        ORDER BY count DESC 
                        LIMIT ?
                    """, (args.top_kospi,))
                    symbols = [row[0] for row in cursor.fetchall()]
        elif args.symbols:
            symbols = args.symbols
            logger.info(f"📊 지정 종목 {len(symbols)}개 백테스팅")
        else:
            symbols = ['005930']  # 기본: 삼성전자
            logger.info("📊 기본값: 삼성전자 백테스팅")
        
        # 백테스팅 기간 설정
        end_date = datetime.now()
        if hasattr(args, 'end_date') and args.end_date:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        
        start_date = end_date - timedelta(days=args.days)
        if hasattr(args, 'start_date') and args.start_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        
        logger.info(f"📅 백테스팅 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} ({args.days}일)")
        
        # 데이터 로드
        logger.info("📚 데이터 로딩 중...")
        data = {}
        failed_symbols = []
        
        with sqlite3.connect(db_path) as conn:
            for symbol in symbols:
                query = """
                SELECT date, open, high, low, close, volume
                FROM stock_data 
                WHERE symbol = ? AND DATE(date) >= ? AND DATE(date) <= ?
                ORDER BY date
                """
                
                try:
                    df = pd.read_sql_query(query, conn, params=(
                        symbol, 
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d')
                    ))
                    
                    if not df.empty and len(df) >= 20:  # 최소 20일 데이터로 완화
                        # 날짜 형식 통일 (시간 정보 제거)
                        df['date'] = pd.to_datetime(df['date'].str.split(' ').str[0], format='mixed', errors='coerce')  # 날짜만 추출
                        df.set_index('date', inplace=True)
                        data[symbol] = df
                        logger.info(f"✅ {symbol}: {len(df)}건 로드")
                    else:
                        failed_symbols.append(symbol)
                        logger.info(f"❌ {symbol}: 데이터 부족 ({len(df) if not df.empty else 0}건)")
                        
                except Exception as e:
                    failed_symbols.append(symbol)
                    logger.error(f"❌ {symbol}: 로드 실패 ({e})")
                    continue
        
        if not data:
            logger.error("❌ 백테스팅할 데이터가 없습니다.")
            return
        
        if failed_symbols:
            logger.warning(f"⚠️  데이터 부족으로 제외된 종목: {len(failed_symbols)}개")
        
        logger.info(f"✅ 데이터 로드 완료: {len(data)}개 종목")
        
        # 전략 설정
        strategy_name = getattr(args, 'strategy', 'macd').lower()
        strategies = {
            'macd': MACDStrategy,
            'rsi': RSIStrategy,
            'bollinger': BollingerBandStrategy,
            'ma': MovingAverageStrategy
        }
        
        strategies_to_test = []
        if strategy_name == 'all':
            strategies_to_test = list(strategies.items())
            logger.info("🎯 모든 전략 백테스팅")
        else:
            if strategy_name not in strategies:
                logger.error(f"❌ 알 수 없는 전략: {strategy_name}")
                logger.info(f"사용 가능한 전략: {', '.join(strategies.keys())}, all")
                return
            strategies_to_test = [(strategy_name, strategies[strategy_name])]
            logger.info(f"🎯 전략: {strategy_name}")
        
        # 🤖 종목 수에 따른 최적 엔진 자동 선택
        num_symbols = len(data)
        force_parallel = getattr(args, 'parallel', False)
        force_optimized = getattr(args, 'optimized', False)
        
        # 엔진 선택 로직
        if force_optimized:
            engine_type = 'optimized'
            logger.info(f"🎯 사용자 지정: OptimizedBacktestEngine (캐싱 + 병렬 + 배치)")
        elif force_parallel:
            engine_type = 'parallel'
            logger.info(f"🎯 사용자 지정: ParallelBacktestEngine (병렬 처리)")
        elif num_symbols >= 100:
            engine_type = 'optimized'
            logger.info(f"🚀 자동 선택: OptimizedBacktestEngine (대규모 {num_symbols}개 종목)")
            logger.info("   └─ 이유: 캐싱 + 메모리 최적화 + 병렬 처리로 최고 성능")
        elif num_symbols >= 10:
            engine_type = 'parallel'
            logger.info(f"⚡ 자동 선택: ParallelBacktestEngine (중규모 {num_symbols}개 종목)")
            logger.info("   └─ 이유: 병렬 처리로 최적 성능/안정성 균형")
        else:
            engine_type = 'sequential'
            logger.info(f"🐌 자동 선택: BacktestEngine (소규모 {num_symbols}개 종목)")
            logger.info("   └─ 이유: 순차 처리로 디버깅 및 상세 분석 최적화")
        
        # 성능 예측 정보 출력
        if num_symbols > 1:
            if engine_type == 'optimized':
                estimated_time = max(30, num_symbols * 0.15)  # 대규모에서 캐싱 효과
                logger.info(f"   ⏱️  예상 소요 시간: {estimated_time:.0f}초 (캐시 히트 시 90% 단축)")
            elif engine_type == 'parallel':
                estimated_time = max(10, num_symbols * 0.25)  # 병렬 처리 효과
                logger.info(f"   ⏱️  예상 소요 시간: {estimated_time:.0f}초 (순차 대비 {min(args.workers, 8)}배 빠름)")
            else:
                estimated_time = num_symbols * 2  # 순차 처리
                logger.info(f"   ⏱️  예상 소요 시간: {estimated_time:.0f}초 (상세 분석 포함)")
        
        # 선택된 엔진으로 백테스팅 실행
        all_results = {}
        total_start_time = time.time()
        
        if engine_type == 'optimized':
            # OptimizedBacktestEngine 사용
            logger.info(f"\n🚀 최적화 엔진 시작 (워커: {args.workers}개, 캐시: 활성화)")
            logger.info("   📊 내부적으로 병렬 처리와 캐싱을 통합 운영합니다")
            
            from src.trading.optimized_backtest import OptimizedBacktestEngine, OptimizedBacktestConfig
            
            optimized_config = OptimizedBacktestConfig(
                max_workers=args.workers,
                chunk_size=args.chunk_size,
                enable_cache=True,
                cache_max_age_hours=24,
                batch_size=args.chunk_size,
                max_memory_usage_mb=1024,
                initial_capital=1000000
            )
            
            optimized_engine = OptimizedBacktestEngine(optimized_config)
            
            for strategy_name, strategy_class in strategies_to_test:
                logger.info(f"\n🔄 {strategy_name} 전략 최적화 백테스팅 실행...")
                strategy_start_time = time.time()
                
                optimized_results = optimized_engine.run_optimized_backtest(
                    strategy_class=strategy_class,
                    symbols=list(data.keys()),
                    strategy_params={},
                    days=args.days
                )
                
                strategy_elapsed = time.time() - strategy_start_time
                logger.info(f"✅ {strategy_name} 완료: {strategy_elapsed:.1f}초")
                
                # 최적화 성능 정보 출력
                opt_stats = optimized_results.get('optimization_stats', {})
                cache_efficiency = opt_stats.get('cache_efficiency', 0)
                memory_efficiency = opt_stats.get('memory_efficiency', 0)
                if cache_efficiency > 0 or memory_efficiency > 0:
                    logger.info(f"   └─ 캐시 효율성: {cache_efficiency:.1%}, 메모리 효율성: {memory_efficiency:.1%}")
                
                all_results[strategy_name] = optimized_results
                
        elif engine_type == 'parallel':
            # ParallelBacktestEngine 사용
            logger.info(f"\n⚡ 병렬 엔진 시작 (워커: {args.workers}개, 청크: {args.chunk_size}개)")
            
            from src.trading.parallel_backtest import ParallelBacktestEngine, ParallelBacktestConfig
            
            parallel_config = ParallelBacktestConfig(
                max_workers=args.workers,
                chunk_size=args.chunk_size,
                timeout=600  # 10분 타임아웃
            )
            
            parallel_engine = ParallelBacktestEngine(parallel_config)
            
            for strategy_name, strategy_class in strategies_to_test:
                logger.info(f"\n🔄 {strategy_name} 전략 병렬 백테스팅 실행...")
                strategy_start_time = time.time()
                
                parallel_results = parallel_engine.run_parallel_backtest(
                    strategy_class=strategy_class,
                    symbols_data=data,
                    strategy_params={},
                    backtest_config={'initial_capital': 1000000}
                )
                
                strategy_elapsed = time.time() - strategy_start_time
                success_count = parallel_results['performance_stats']['successful_backtests']
                success_rate = success_count / num_symbols * 100
                processing_speed = num_symbols / strategy_elapsed
                
                logger.info(f"✅ {strategy_name} 완료: {strategy_elapsed:.1f}초")
                logger.info(f"   └─ 성공률: {success_rate:.1f}% ({success_count}/{num_symbols}) | 처리 속도: {processing_speed:.1f} 종목/초")
                
                all_results[strategy_name] = parallel_results
                
        else:  # sequential
            # BacktestEngine 사용 (순차 처리)
            logger.info("\n🐌 순차 엔진 시작 (디버깅 최적화)")
            
            config = BacktestConfig(initial_capital=1000000)
            engine = BacktestEngine(config)
            
            for strategy_name, strategy_class in strategies_to_test:
                logger.info(f"\n🔄 {strategy_name} 전략 순차 백테스팅 실행...")
                strategy_start_time = time.time()
                
                strategy = strategy_class()
                results = engine.run_backtest(strategy, data, 
                                            start_date.strftime('%Y-%m-%d'), 
                                            end_date.strftime('%Y-%m-%d'))
                
                strategy_elapsed = time.time() - strategy_start_time
                total_trades = results.get('total_trades', 0)
                total_return = results.get('total_return', 0)
                
                logger.info(f"✅ {strategy_name} 완료: {strategy_elapsed:.1f}초")
                logger.info(f"   └─ 총 거래: {total_trades}회, 수익률: {total_return:.2%}")
                
                all_results[strategy_name] = {'results': {f'portfolio': results}}
        
        # 전체 실행 시간 계산
        total_elapsed = time.time() - total_start_time
        logger.info(f"\n🏁 전체 백테스팅 완료: {total_elapsed:.1f}초")
        
        # 성능 평가 출력
        if num_symbols > 1:
            overall_speed = num_symbols * len(strategies_to_test) / total_elapsed
            logger.info(f"   📈 전체 처리 속도: {overall_speed:.1f} 종목×전략/초")
            
            if engine_type == 'parallel':
                efficiency = min(args.workers, num_symbols) / (total_elapsed / (num_symbols * len(strategies_to_test) * 2))
                logger.info(f"   ⚡ 병렬 처리 효율성: {efficiency:.1f}배 (순차 처리 대비)")
            elif engine_type == 'optimized':
                logger.info(f"   🚀 최적화 엔진 선택으로 대규모 처리 성공")
        
        # 결과 출력 및 저장
        logger.info("\n" + "="*60)
        logger.info("📊 백테스팅 결과 요약")
        logger.info("="*60)
        
        for strategy_name, strategy_results in all_results.items():
            logger.info(f"\n🎯 [{strategy_name.upper()} 전략]")
            
            if 'results' in strategy_results:
                results_data = strategy_results['results']
                
                # 성과 통계 계산
                if results_data:
                    # 첫 번째 종목의 결과 구조 확인
                    sample_result = next(iter(results_data.values()))
                    
                    if isinstance(sample_result, dict):
                        total_returns = [r.get('total_return', 0) for r in results_data.values() if isinstance(r, dict)]
                        sharpe_ratios = [r.get('sharpe_ratio', 0) for r in results_data.values() if isinstance(r, dict)]
                        max_drawdowns = [r.get('max_drawdown', 0) for r in results_data.values() if isinstance(r, dict)]
                        win_rates = [r.get('win_rate', 0) for r in results_data.values() if isinstance(r, dict)]
                        total_trades = [r.get('total_trades', 0) for r in results_data.values() if isinstance(r, dict)]
                        
                        if total_returns:
                            logger.info(f"  평균 수익률: {sum(total_returns)/len(total_returns):.2%}")
                            logger.info(f"  평균 샤프 비율: {sum(sharpe_ratios)/len(sharpe_ratios):.3f}")
                            logger.info(f"  평균 최대 낙폭: {sum(max_drawdowns)/len(max_drawdowns):.2%}")
                            logger.info(f"  평균 승률: {sum(win_rates)/len(win_rates):.2%}")
                            logger.info(f"  총 거래 수: {sum(total_trades):,}회")
                            logger.info(f"  처리 종목 수: {len(results_data)}개")
        
        # 결과 저장
        if getattr(args, 'save_results', False):
            output_dir = Path(args.output_dir)
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # JSON 저장
            json_file = output_dir / f'backtest_results_{timestamp}.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"\n💾 결과 저장됨: {json_file}")
        
        logger.info("\n✅ 백테스팅 완료!")
        
    except Exception as e:
        import traceback
        logger.error(f"❌ 백테스팅 실패: {e}")
        logger.error(traceback.format_exc())
        logger.error(f"백테스팅 실패: {e}")

def run_streamlit():
    """Streamlit 웹 앱 실행"""
    try:
        import streamlit.web.cli as stcli
        import sys
        
        # Streamlit 앱 파일 경로
        app_file = PROJECT_ROOT / 'streamlit_app' / 'app.py'
        
        if not app_file.exists():
            logger.error(f"Streamlit 앱 파일이 없습니다: {app_file}")
            logger.info("streamlit_app/app.py를 생성해주세요.")
            return
        
        logger.info("Streamlit 웹 앱을 시작합니다...")
        logger.info("브라우저에서 http://localhost:8501 을 열어주세요.")
        
        # Streamlit 실행
        sys.argv = ["streamlit", "run", str(app_file)]
        stcli.main()
        
    except Exception as e:
        logger.error(f"Streamlit 실행 실패: {e}")
        logger.info("Streamlit이 설치되지 않았을 수 있습니다. 'pip install streamlit'로 설치해주세요.")

def run_optimization(args):
    """매개변수 최적화 실행"""
    try:
        from src.ui.optimization import ParameterOptimizer
        from src.strategies.macd_strategy import MACDStrategy
        import pandas as pd
        import sqlite3
        
        logger.info("매개변수 최적화 시작...")
        
        # 데이터 로드 (백테스트와 동일)
        db_path = PROJECT_ROOT / 'data' / 'trading.db'
        if not db_path.exists():
            logger.error("데이터베이스가 없습니다. 먼저 데이터를 업데이트하세요.")
            return
        
        symbols = args.symbols or ['005930']
        data = {}
        
        with sqlite3.connect(db_path) as conn:
            for symbol in symbols:
                query = """
                SELECT date, open, high, low, close, volume
                FROM stock_data 
                WHERE symbol = ?
                ORDER BY date
                """
                df = pd.read_sql_query(query, conn, params=(symbol,))
                
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
                    df.set_index('date', inplace=True)
                    data[symbol] = df
        
        if not data:
            logger.error("최적화할 데이터가 없습니다.")
            return
        
        # 매개변수 범위 설정
        param_ranges = {
            'fast_period': [8, 10, 12, 14, 16],
            'slow_period': [21, 24, 26, 28, 30],
            'signal_period': [7, 8, 9, 10, 11]
        }
        
        # 최적화 실행
        optimizer = ParameterOptimizer()
        results = optimizer.run_grid_search(
            strategy_class=MACDStrategy,
            data=data,
            param_ranges=param_ranges,
            metric='sharpe_ratio',
            max_combinations=50
        )
        
        # 결과 출력
        logger.info("\n=== 최적화 결과 ===")
        logger.info(f"최적 매개변수: {results['best_parameters']}")
        logger.info(f"최고 성과: {results['best_score']:.4f}")
        logger.info(f"테스트 조합: {results['total_combinations']}개")
        
    except Exception as e:
        logger.error(f"최적화 실패: {e}")

def main():
    """메인 함수"""
    # 설정 로드
    config = load_config()
    
    # 환경 설정
    setup_environment()
    
    # 로깅 설정
    setup_logging(config)
    
    logger.info(f"=== {config['project']['name']} v{config['project']['version']} ===")
    
    # 인자 파서 설정
    parser = argparse.ArgumentParser(
        description='TA-Lib 스윙 트레이딩 자동매매 시스템',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python src/main.py check-deps           # 패키지 설치 확인
  
  # 데이터 업데이트 (기본: 1년 데이터)
  python src/main.py update-data          # 코스피 상위 30종목 1년 데이터 업데이트
  python src/main.py update-data --top-kospi 50  # 코스피 상위 50종목 1년 데이터
  python src/main.py update-data --symbols 005930 000660  # 특정 종목 1년 데이터
  
  # 날짜 범위 지정
  python src/main.py update-data --days 180    # 최근 180일 데이터
  python src/main.py update-data --period 6m   # 최근 6개월 데이터
  python src/main.py update-data --period 2y   # 최근 2년 데이터
  python src/main.py update-data --start-date 2024-01-01 --end-date 2024-06-30  # 특정 기간
  python src/main.py update-data --start-date 20240101  # 2024년 1월 1일부터 오늘까지
  
  # 빠른 업데이트 (Ultra-Fast)
  python src/main.py update-data --yesterday-only  # 전날 데이터만 (4-5초 완료)
  python src/main.py update-data -y --top-kospi 30  # 코스피 상위 30종목 전날 데이터
  
  # 상태 확인
  python src/main.py update-data --summary     # 데이터베이스 현황 확인
  python src/main.py update-data --api-status  # API 사용량 확인
  
  # 백테스팅 (기본)
  python src/main.py backtest                  # 삼성전자 180일 백테스팅 (MACD 전략)
  python src/main.py backtest --symbols 005930 000660  # 특정 종목 백테스팅
  python src/main.py backtest --strategy rsi   # RSI 전략으로 백테스팅
  python src/main.py backtest --start-date 2024-01-01 --end-date 2024-06-30  # 기간 지정
  
  # 대규모 백테스팅 (병렬 처리)
  python src/main.py backtest --top-kospi 10 --parallel  # 코스피 상위 10종목 병렬 백테스팅
  python src/main.py backtest --all-kospi --parallel --workers 8  # 코스피 전체 병렬 백테스팅
  python src/main.py backtest --strategy all --top-kospi 50 --parallel  # 모든 전략 테스트
  
  # 결과 저장
  python src/main.py backtest --all-kospi --parallel --save-results  # 결과 JSON 저장
  
  # 매개변수 최적화 및 웹 인터페이스
  python src/main.py optimize                 # 매개변수 최적화
  python src/main.py web                      # 웹 인터페이스 실행
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # 패키지 확인 명령어
    subparsers.add_parser('check-deps', help='필수 패키지 설치 확인')
    
    # 데이터 업데이트 명령어
    update_parser = subparsers.add_parser('update-data', help='주식 데이터 업데이트')
    update_parser.add_argument('--symbols', nargs='+', help='업데이트할 종목 코드들')
    update_parser.add_argument('--top-kospi', type=int, default=30, dest='top_kospi', help='코스피 상위 N개 종목 (기본: 30)')
    update_parser.add_argument('--force', action='store_true', help='강제 업데이트')
    update_parser.add_argument('--summary', action='store_true', help='데이터베이스 현황 보기')
    update_parser.add_argument('--api-status', action='store_true', dest='api_status', help='API 사용량 현황 보기')
    update_parser.add_argument('--yesterday-only', '-y', action='store_true', dest='yesterday_only', help='전날 데이터만 업데이트 (효율적)')
    
    # 날짜 범위 옵션 추가
    date_group = update_parser.add_argument_group('날짜 범위 설정')
    date_group.add_argument('--days', type=int, help='현재부터 N일 전까지 데이터 수집 (예: 180)')
    date_group.add_argument('--start-date', help='시작 날짜 (YYYY-MM-DD 또는 YYYYMMDD 형식)')
    date_group.add_argument('--end-date', help='종료 날짜 (YYYY-MM-DD 또는 YYYYMMDD 형식, 기본: 오늘)')
    date_group.add_argument('--period', choices=['1w', '1m', '3m', '6m', '1y', '2y'], default='1y', 
                           help='기본 수집 기간 (기본: 1y=1년)')
    
    # 병렬 처리 옵션 추가
    parallel_group = update_parser.add_argument_group('병렬 처리 설정')
    parallel_group.add_argument('--parallel', '-p', action='store_true', help='병렬 처리로 데이터 수집 (빠른 속도)')
    parallel_group.add_argument('--workers', type=int, default=5, help='병렬 처리 워커 수 (기본: 5)')
    
    # 백테스팅 명령어
    backtest_parser = subparsers.add_parser('backtest', help='백테스팅 실행')
    backtest_parser.add_argument('--symbols', nargs='+', help='백테스팅할 종목 코드들')
    backtest_parser.add_argument('--top-kospi', type=int, help='코스피 상위 N개 종목 백테스팅')
    backtest_parser.add_argument('--all-kospi', action='store_true', help='코스피 전체 종목 백테스팅 (962개)')
    backtest_parser.add_argument('--start-date', dest='start_date', help='백테스팅 시작날짜 (YYYY-MM-DD)')
    backtest_parser.add_argument('--end-date', dest='end_date', help='백테스팅 종료날짜 (YYYY-MM-DD)')
    backtest_parser.add_argument('--days', type=int, default=180, help='백테스팅 기간 (일수, 기본: 180일)')
    backtest_parser.add_argument('--strategy', choices=['macd', 'rsi', 'bollinger', 'ma', 'all'], 
                                default='macd', help='사용할 전략 (기본: macd, all: 모든 전략)')
    
    # 백테스팅 병렬 처리 옵션
    backtest_parallel_group = backtest_parser.add_argument_group('엔진 선택 및 성능 설정')
    backtest_parallel_group.add_argument('--parallel', '-p', action='store_true', help='병렬 처리 엔진 강제 사용 (중규모 최적)')
    backtest_parallel_group.add_argument('--optimized', '-o', action='store_true', help='최적화 엔진 강제 사용 (대규모 최적, 캐싱)')
    backtest_parallel_group.add_argument('--workers', type=int, default=4, help='병렬 처리 워커 수 (기본: 4)')
    backtest_parallel_group.add_argument('--chunk-size', type=int, default=20, help='청크당 종목 수 (기본: 20)')
    
    # 자동 엔진 선택 안내
    engine_help = backtest_parser.add_argument_group('자동 엔진 선택 (옵션 미지정 시)')
    engine_help.description = """
    🤖 종목 수에 따른 자동 엔진 선택:
    • 1-9개 종목: BacktestEngine (순차 처리, 디버깅 최적)
    • 10-99개 종목: ParallelBacktestEngine (병렬 처리, 성능/안정성 균형)  
    • 100개+ 종목: OptimizedBacktestEngine (캐싱+병렬+배치, 최고 성능)
    """
    
    # 백테스팅 결과 저장 옵션
    backtest_output_group = backtest_parser.add_argument_group('결과 저장')
    backtest_output_group.add_argument('--save-results', action='store_true', help='결과를 CSV/JSON으로 저장')
    backtest_output_group.add_argument('--output-dir', default='backtest_results', help='결과 저장 디렉토리 (기본: backtest_results)')
    
    # 최적화 명령어
    optimize_parser = subparsers.add_parser('optimize', help='매개변수 최적화')
    optimize_parser.add_argument('--symbols', nargs='+', help='최적화할 종목 코드들')
    
    # 웹 인터페이스 명령어
    subparsers.add_parser('web', help='Streamlit 웹 인터페이스 실행')
    
    # 인자 파싱
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 명령어 실행
    try:
        if args.command == 'check-deps':
            if check_dependencies():
                logger.info("\n시스템이 정상적으로 설정되었습니다!")
            else:
                sys.exit(1)
                
        elif args.command == 'update-data':
            run_data_update(args)
            
        elif args.command == 'backtest':
            run_backtest(args)
            
        elif args.command == 'optimize':
            run_optimization(args)
            
        elif args.command == 'web':
            run_streamlit()
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
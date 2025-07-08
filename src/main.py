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
import json
import numpy as np

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
            # 백테스팅 분석 포함 여부 확인
            include_backtest = getattr(args, 'backtest_analysis', False)
            
            if include_backtest:
                # 종합 상태 분석
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
            return
        
        # 전날 데이터만 업데이트
        if hasattr(args, 'yesterday_only') and args.yesterday_only:
            logger.info("=== 전날 데이터 업데이트 모드 ===")
            
            if hasattr(args, 'all_kospi') and args.all_kospi:
                # 코스피 전체 종목
                all_symbols = updater.get_kospi_symbols()
                results = updater.update_yesterday_data(symbols=all_symbols)
                logger.info(f"코스피 전체 {len(all_symbols)}개 종목 전날 데이터 업데이트")
            elif args.top_kospi and args.top_kospi > 0:
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
        if hasattr(args, 'all_kospi') and args.all_kospi:
            # 코스피 전체 종목
            symbols = updater.get_kospi_symbols()
            logger.info(f"코스피 전체 {len(symbols)}개 종목 데이터 수집")
        elif args.top_kospi and args.top_kospi > 0:
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
        
        # 결과 저장 (기본 저장, --no-save-results로 비활성화 가능)
        if not getattr(args, 'no_save_results', False):
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
        from src.strategies.macd_strategy import MACDStrategy
        from src.trading.parameter_optimizer import ParameterOptimizer
        import sqlite3
        
        logger.info("🔧 매개변수 최적화 시작...")
        
        # 데이터베이스에서 데이터 로드
        db_path = PROJECT_ROOT / 'data' / 'trading.db'
        
        if not db_path.exists():
            logger.error("❌ 데이터베이스가 없습니다. 먼저 데이터를 업데이트하세요.")
            return
        
        symbols = args.symbols if args.symbols else ['005930']  # 기본: 삼성전자
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

def run_check_data(args):
    """종합 데이터 상태 확인 (check_data_status.py 기능 통합)"""
    try:
        from scripts.data_update import StockDataUpdater
        
        updater = StockDataUpdater()
        
        # 데이터베이스 존재 여부 확인
        if not Path(updater.db_path).exists():
            logger.error("❌ 데이터베이스가 없습니다.")
            logger.info("다음 명령어로 데이터를 먼저 수집하세요:")
            logger.info("python src/main.py update-data --top-kospi 50 --period 6m")
            return
        
        logger.info("🔍 데이터 상태 종합 분석 중...")
        
        # 분석 매개변수 설정
        days_back = getattr(args, 'days_back', 60)
        min_days = getattr(args, 'min_days', 30)
        top_limit = getattr(args, 'top_limit', 20)
        
        # 종합 상태 분석 실행
        comprehensive_status = updater.get_comprehensive_status(include_backtest_analysis=True)
        
        # 기본 현황
        basic = comprehensive_status.get('basic_summary', {})
        logger.info("\n" + "="*50)
        logger.info("📊 데이터베이스 기본 현황")
        logger.info("="*50)
        logger.info(f"총 종목 수: {basic.get('symbols_count', 0):,}개")
        logger.info(f"데이터 기간: {basic.get('date_range', ('N/A', 'N/A'))[0]} ~ {basic.get('date_range', ('N/A', 'N/A'))[1]}")
        logger.info(f"총 데이터: {basic.get('total_records', 0):,}건")
        logger.info(f"DB 파일: {basic.get('db_path', 'N/A')}")
        
        # 최근 업데이트 정보
        recent_updates = basic.get('recent_updates', [])
        if recent_updates:
            logger.info(f"\n📅 최근 업데이트 종목 (상위 5개):")
            for symbol, last_date in recent_updates:
                logger.info(f"  • {symbol}: {last_date}")
        
        # 백테스팅 분석
        backtest = comprehensive_status.get('backtest_analysis', {})
        if backtest:
            logger.info(f"\n" + "="*50)
            logger.info("🚀 백테스팅 적합성 분석")
            logger.info("="*50)
            logger.info(f"분석 기간: {backtest.get('analysis_period', 'N/A')}")
            logger.info(f"최소 데이터 요구: {backtest.get('min_data_days', 0)}일 이상")
            logger.info(f"백테스팅 가능 종목: {backtest.get('valid_symbols_count', 0):,}개")
            logger.info(f"적합성 비율: {backtest.get('valid_percentage', 0)}% ({backtest.get('valid_symbols_count', 0)}/{basic.get('symbols_count', 0)})")
            
            # 상위 종목 상세 표시
            top_symbols = backtest.get('top_symbols', [])
            if top_symbols:
                logger.info(f"\n📈 데이터가 가장 충실한 상위 {len(top_symbols)}개 종목:")
                for i, symbol_info in enumerate(top_symbols, 1):
                    symbol = symbol_info['symbol']
                    days = symbol_info['days']
                    start_date = symbol_info['start_date']
                    end_date = symbol_info['end_date']
                    logger.info(f"  {i:2d}. {symbol}: {days:3d}일 ({start_date} ~ {end_date})")
            
            # 테스트 추천 종목
            test_symbols = backtest.get('test_symbols_string', '')
            if test_symbols:
                logger.info(f"\n🎯 백테스팅 테스트 추천 종목 (상위 10개):")
                logger.info(f"   {test_symbols}")
                logger.info("\n💡 사용 방법:")
                logger.info(f"   python src/main.py backtest --symbols {' '.join(backtest.get('test_symbols', [])[:3])}")
                logger.info(f"   python src/main.py backtest --top-kospi 10 --strategy all")
        
        # API 사용 현황
        api_status = comprehensive_status.get('api_status', {})
        if api_status and api_status.get('api_calls', 0) > 0:
            logger.info(f"\n" + "="*50)
            logger.info("🔌 현재 세션 API 사용 현황")
            logger.info("="*50)
            logger.info(f"API 호출: {api_status.get('api_calls', 0)}회")
            logger.info(f"세션 시간: {api_status.get('session_duration', 'N/A')}")
            logger.info(f"분당 호출율: {api_status.get('calls_per_minute', 0):.1f}회/분")
            logger.info(f"참고: {api_status.get('notes', 'N/A')}")
        
        # 추가 권장사항
        valid_count = backtest.get('valid_symbols_count', 0)
        total_count = basic.get('symbols_count', 0)
        
        logger.info(f"\n" + "="*50)
        logger.info("💡 권장사항")
        logger.info("="*50)
        
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
            logger.info("   python src/main.py backtest --all-kospi --parallel --workers 8")
        
        # 마지막 실행 명령어 제안
        if test_symbols:
            logger.info(f"\n🚀 바로 시작할 수 있는 명령어:")
            logger.info(f"   python src/main.py backtest --symbols {' '.join(backtest.get('test_symbols', [])[:5])}")
        
    except Exception as e:
        logger.error(f"데이터 상태 확인 실패: {e}")
        logger.info("기본 상태 확인을 시도하세요:")
        logger.info("python src/main.py update-data --summary")

def load_backtest_results(file_path: str) -> dict:
    """백테스팅 결과 파일 로드"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"결과 파일 로드 실패: {e}")
        return {}

def analyze_backtest_results_data(results: dict) -> pd.DataFrame:
    """결과 분석 및 DataFrame 변환"""
    all_results = []
    
    for strategy, strategy_data in results.items():
        if 'results' not in strategy_data:
            continue
            
        for symbol, data in strategy_data['results'].items():
            if not data.get('success', False):
                continue
                
            # 거래가 있는 경우만 포함 (0거래는 제외)
            if data.get('total_trades', 0) == 0:
                continue
                
            result_row = {
                'strategy': strategy.upper(),
                'symbol': symbol,
                'total_return': data.get('total_return', 0) * 100,  # 백분율로 변환
                'sharpe_ratio': data.get('sharpe_ratio', 0),
                'max_drawdown': data.get('max_drawdown', 0) * 100,  # 백분율로 변환
                'win_rate': data.get('win_rate', 0) * 100,  # 백분율로 변환
                'total_trades': data.get('total_trades', 0),
                'data_points': data.get('data_points', 0)
            }
            all_results.append(result_row)
    
    if not all_results:
        logger.warning("분석할 결과가 없습니다.")
        return pd.DataFrame()
    
    df = pd.DataFrame(all_results)
    return df

def create_sorted_analysis(df: pd.DataFrame, output_dir: str):
    """정렬된 분석 결과 생성"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 수익률 기준 상위 종목
    logger.info("📈 수익률 기준 상위 종목 분석...")
    top_returns = df.nlargest(50, 'total_return')
    returns_file = output_path / f"top_returns_{timestamp}.csv"
    top_returns.to_csv(returns_file, index=False, encoding='utf-8-sig')
    
    # 2. 승률 기준 상위 종목
    logger.info("🎯 승률 기준 상위 종목 분석...")
    top_winrates = df.nlargest(50, 'win_rate')
    winrates_file = output_path / f"top_winrates_{timestamp}.csv"
    top_winrates.to_csv(winrates_file, index=False, encoding='utf-8-sig')
    
    # 3. 샤프 비율 기준 상위 종목
    logger.info("⚖️ 샤프 비율 기준 상위 종목 분석...")
    top_sharpe = df.nlargest(50, 'sharpe_ratio')
    sharpe_file = output_path / f"top_sharpe_{timestamp}.csv"
    top_sharpe.to_csv(sharpe_file, index=False, encoding='utf-8-sig')
    
    # 4. 종합 점수 기준 (수익률 + 승률 + 샤프비율)
    logger.info("🏆 종합 점수 기준 상위 종목 분석...")
    df['composite_score'] = (
        df['total_return'].fillna(0) * 0.4 +  # 수익률 40%
        df['win_rate'].fillna(0) * 0.3 +      # 승률 30%
        df['sharpe_ratio'].fillna(0) * 30 * 0.3  # 샤프비율 30% (스케일 조정)
    )
    top_composite = df.nlargest(50, 'composite_score')
    composite_file = output_path / f"top_composite_{timestamp}.csv"
    top_composite.to_csv(composite_file, index=False, encoding='utf-8-sig')
    
    # 5. 전략별 통계
    logger.info("📊 전략별 통계 분석...")
    strategy_stats = df.groupby('strategy').agg({
        'total_return': ['mean', 'median', 'std', 'max', 'min'],
        'win_rate': ['mean', 'median', 'std', 'max', 'min'],
        'sharpe_ratio': ['mean', 'median', 'std', 'max', 'min'],
        'total_trades': ['sum', 'mean'],
        'symbol': 'count'
    }).round(4)
    
    strategy_stats.columns = ['_'.join(col).strip() for col in strategy_stats.columns]
    strategy_file = output_path / f"strategy_stats_{timestamp}.csv"
    strategy_stats.to_csv(strategy_file, encoding='utf-8-sig')
    
    # 6. 상세 분석 보고서 생성
    logger.info("📋 상세 분석 보고서 생성...")
    create_detailed_report(df, top_returns, top_winrates, top_sharpe, top_composite, 
                          strategy_stats, output_path, timestamp)
    
    return {
        'top_returns': returns_file,
        'top_winrates': winrates_file, 
        'top_sharpe': sharpe_file,
        'top_composite': composite_file,
        'strategy_stats': strategy_file
    }

def create_detailed_report(df, top_returns, top_winrates, top_sharpe, top_composite, 
                          strategy_stats, output_path, timestamp):
    """상세 분석 보고서 생성"""
    report_file = output_path / f"detailed_report_{timestamp}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 백테스팅 결과 상세 분석 보고서\n\n")
        f.write(f"**생성 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**분석 대상**: {len(df)}개 종목×전략 조합 (거래 발생 건만)\n\n")
        
        # 전체 통계
        f.write("## 📊 전체 통계 요약\n\n")
        f.write(f"- **평균 수익률**: {df['total_return'].mean():.2f}%\n")
        f.write(f"- **평균 승률**: {df['win_rate'].mean():.2f}%\n") 
        f.write(f"- **평균 샤프 비율**: {df['sharpe_ratio'].mean():.3f}\n")
        f.write(f"- **총 거래 수**: {df['total_trades'].sum():,}회\n")
        f.write(f"- **수익률 > 0%**: {len(df[df['total_return'] > 0])}개 ({len(df[df['total_return'] > 0])/len(df)*100:.1f}%)\n")
        f.write(f"- **승률 > 50%**: {len(df[df['win_rate'] > 50])}개 ({len(df[df['win_rate'] > 50])/len(df)*100:.1f}%)\n\n")
        
        # 수익률 TOP 10
        f.write("## 🥇 수익률 TOP 10\n\n")
        f.write("| 순위 | 전략 | 종목 | 수익률 | 승률 | 샤프비율 | 거래수 |\n")
        f.write("|------|------|------|--------|------|----------|--------|\n")
        for i, row in top_returns.head(10).iterrows():
            f.write(f"| {len(top_returns) - list(top_returns.index).index(i)} | {row['strategy']} | {row['symbol']} | "
                   f"{row['total_return']:.2f}% | {row['win_rate']:.1f}% | {row['sharpe_ratio']:.3f} | {row['total_trades']} |\n")
        f.write("\n")
        
        # 승률 TOP 10  
        f.write("## 🎯 승률 TOP 10\n\n")
        f.write("| 순위 | 전략 | 종목 | 승률 | 수익률 | 샤프비율 | 거래수 |\n")
        f.write("|------|------|------|------|--------|----------|--------|\n")
        for i, row in top_winrates.head(10).iterrows():
            f.write(f"| {len(top_winrates) - list(top_winrates.index).index(i)} | {row['strategy']} | {row['symbol']} | "
                   f"{row['win_rate']:.1f}% | {row['total_return']:.2f}% | {row['sharpe_ratio']:.3f} | {row['total_trades']} |\n")
        f.write("\n")
        
        # 샤프 비율 TOP 10
        f.write("## ⚖️ 샤프 비율 TOP 10\n\n")
        f.write("| 순위 | 전략 | 종목 | 샤프비율 | 수익률 | 승률 | 거래수 |\n")
        f.write("|------|------|------|----------|--------|------|--------|\n")
        for i, row in top_sharpe.head(10).iterrows():
            f.write(f"| {len(top_sharpe) - list(top_sharpe.index).index(i)} | {row['strategy']} | {row['symbol']} | "
                   f"{row['sharpe_ratio']:.3f} | {row['total_return']:.2f}% | {row['win_rate']:.1f}% | {row['total_trades']} |\n")
        f.write("\n")
        
        # 종합 점수 TOP 10
        f.write("## 🏆 종합 점수 TOP 10\n\n")
        f.write("| 순위 | 전략 | 종목 | 종합점수 | 수익률 | 승률 | 샤프비율 | 거래수 |\n")
        f.write("|------|------|------|----------|--------|------|----------|--------|\n")
        for i, row in top_composite.head(10).iterrows():
            f.write(f"| {len(top_composite) - list(top_composite.index).index(i)} | {row['strategy']} | {row['symbol']} | "
                   f"{row['composite_score']:.2f} | {row['total_return']:.2f}% | {row['win_rate']:.1f}% | "
                   f"{row['sharpe_ratio']:.3f} | {row['total_trades']} |\n")
        f.write("\n")
        
        # 전략별 성과
        f.write("## 📈 전략별 성과 비교\n\n")
        f.write("| 전략 | 평균 수익률 | 평균 승률 | 평균 샤프비율 | 총 거래수 | 종목수 |\n")
        f.write("|------|-------------|-----------|---------------|----------|--------|\n")
        for strategy in strategy_stats.index:
            f.write(f"| {strategy} | {strategy_stats.loc[strategy, 'total_return_mean']:.2f}% | "
                   f"{strategy_stats.loc[strategy, 'win_rate_mean']:.1f}% | "
                   f"{strategy_stats.loc[strategy, 'sharpe_ratio_mean']:.3f} | "
                   f"{strategy_stats.loc[strategy, 'total_trades_sum']:.0f} | "
                   f"{strategy_stats.loc[strategy, 'symbol_count']:.0f} |\n")
        f.write("\n")
        
        # 추천 종목
        f.write("## 💡 투자 추천 종목\n\n")
        recommended = top_composite.head(5)
        f.write("**종합 점수 기준 상위 5개 종목 (수익률, 승률, 샤프비율 종합 고려)**\n\n")
        for i, row in recommended.iterrows():
            f.write(f"### {row['symbol']} ({row['strategy']} 전략)\n")
            f.write(f"- **수익률**: {row['total_return']:.2f}%\n")
            f.write(f"- **승률**: {row['win_rate']:.1f}%\n")
            f.write(f"- **샤프 비율**: {row['sharpe_ratio']:.3f}\n")
            f.write(f"- **거래 수**: {row['total_trades']}회\n")
            f.write(f"- **종합 점수**: {row['composite_score']:.2f}\n\n")

def run_analyze_results(args):
    """백테스팅 결과 분석 실행"""
    logger.info("🔍 백테스팅 결과 분석 시작...")
    
    # 자동 검색 옵션 처리
    if args.auto_find or not Path(args.input).exists():
        backtest_dir = PROJECT_ROOT / 'backtest_results'
        if not backtest_dir.exists():
            logger.error(f"백테스팅 결과 디렉토리가 없습니다: {backtest_dir}")
            return
            
        json_files = list(backtest_dir.glob('backtest_results_*.json'))
        if not json_files:
            logger.error("백테스팅 결과 파일(JSON)을 찾을 수 없습니다.")
            logger.info("먼저 백테스팅을 실행하세요:")
            logger.info("python src/main.py backtest --symbols 005930")
            return
            
        latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
        input_file = latest_file
        logger.info(f"📁 최신 백테스팅 결과 파일 사용: {latest_file}")
    else:
        input_file = Path(args.input)
        if not input_file.exists():
            logger.error(f"입력 파일을 찾을 수 없습니다: {input_file}")
            return
    
    # 결과 로드
    results = load_backtest_results(str(input_file))
    if not results:
        logger.error("결과 파일을 로드할 수 없습니다.")
        return
    
    # 분석
    df = analyze_backtest_results_data(results)
    if df.empty:
        logger.error("분석할 데이터가 없습니다.")
        return
    
    logger.info(f"📊 총 {len(df)}개 종목×전략 조합 분석 중...")
    
    # 정렬된 분석 결과 생성
    output_files = create_sorted_analysis(df, args.output)
    
    logger.info("\n" + "="*60)
    logger.info("✅ 분석 완료!")
    logger.info("="*60)
    logger.info("📁 생성된 파일:")
    for name, path in output_files.items():
        logger.info(f"   • {name}: {path}")
    
    # 간단한 요약 출력
    logger.info("\n📊 분석 요약:")
    logger.info(f"   • 전체 결과: {len(df)}개")
    logger.info(f"   • 수익률 > 0%: {len(df[df['total_return'] > 0])}개 ({len(df[df['total_return'] > 0])/len(df)*100:.1f}%)")
    logger.info(f"   • 승률 > 50%: {len(df[df['win_rate'] > 50])}개 ({len(df[df['win_rate'] > 50])/len(df)*100:.1f}%)")
    logger.info(f"   • 최고 수익률: {df['total_return'].max():.2f}%")
    logger.info(f"   • 최고 승률: {df['win_rate'].max():.1f}%")
    
    # TOP 5 추천 종목 출력
    if 'composite_score' in df.columns:
        top_5 = df.nlargest(5, 'composite_score')
        logger.info("\n💡 TOP 5 추천 종목 (종합 점수 기준):")
        for i, (_, row) in enumerate(top_5.iterrows(), 1):
            logger.info(f"   {i}. {row['symbol']} ({row['strategy']}) - "
                       f"수익률: {row['total_return']:.2f}%, "
                       f"승률: {row['win_rate']:.1f}%, "
                       f"샤프: {row['sharpe_ratio']:.3f}")

def show_available_commands():
    """사용 가능한 명령어 목록 표시"""
    commands = {
        'check-deps': '필수 패키지 설치 확인',
        'check-data': '종합 데이터 상태 확인 (백테스팅 적합성 분석)',
        'update-data': '주식 데이터 업데이트',
        'backtest': '백테스팅 실행',
        'optimize': '매개변수 최적화',
        'web': 'Streamlit 웹 인터페이스 실행',
        'analyze-results': '백테스팅 결과 분석 및 리포트 생성'
    }
    
    logger.info("\n📋 사용 가능한 명령어:")
    for cmd, desc in commands.items():
        logger.info(f"  • {cmd:<15} - {desc}")
    
    logger.info("\n💡 자세한 사용법:")
    logger.info("  python src/main.py <명령어> --help")
    logger.info("  python src/main.py --help              # 전체 도움말")

def show_command_help(command: str):
    """특정 명령어의 상세 도움말 표시"""
    command_examples = {
        'check-deps': [
            "python src/main.py check-deps"
        ],
        'check-data': [
            "python src/main.py check-data",
            "python src/main.py check-data --days-back 90 --min-days 45",
            "python src/main.py check-data --top-limit 30"
        ],
        'update-data': [
            "python src/main.py update-data",
            "python src/main.py update-data --symbols 005930 000660",
            "python src/main.py update-data --top-kospi 50",
            "python src/main.py update-data --all-kospi",
            "python src/main.py update-data --all-kospi --parallel --workers 8",
            "python src/main.py update-data --days 180",
            "python src/main.py update-data --period 6m",
            "python src/main.py update-data --start-date 2024-01-01",
            "python src/main.py update-data --yesterday-only",
            "python src/main.py update-data --all-kospi --yesterday-only",
            "python src/main.py update-data --summary",
            "python src/main.py update-data --api-status"
        ],
        'backtest': [
            "python src/main.py backtest",
            "python src/main.py backtest --symbols 005930 000660",
            "python src/main.py backtest --top-kospi 10",
            "python src/main.py backtest --all-kospi",
            "python src/main.py backtest --strategy rsi",
            "python src/main.py backtest --days 365",
            "python src/main.py backtest --start-date 2024-01-01 --end-date 2024-06-30",
            "python src/main.py backtest --parallel --workers 8",
            "python src/main.py backtest --optimized --chunk-size 50"
        ],
        'optimize': [
            "python src/main.py optimize",
            "python src/main.py optimize --symbols 005930"
        ],
        'web': [
            "python src/main.py web"
        ],
        'analyze-results': [
            "python src/main.py analyze-results",
            "python src/main.py analyze-results --auto-find",
            "python src/main.py analyze-results --input results.json",
            "python src/main.py analyze-results --output my_analysis"
        ]
    }
    
    if command in command_examples:
        logger.info(f"\n🔧 '{command}' 명령어 사용 예시:")
        for example in command_examples[command]:
            logger.info(f"  {example}")
        logger.info(f"\n💡 상세 옵션: python src/main.py {command} --help")
    else:
        logger.info(f"\n❓ '{command}' 명령어에 대한 예시를 찾을 수 없습니다.")
        show_available_commands()

def get_current_command_from_args() -> str:
    """현재 실행된 명령어 추출"""
    import sys
    args = sys.argv[1:]  # 스크립트 이름 제외
    
    valid_commands = ['check-deps', 'check-data', 'update-data', 'backtest', 'optimize', 'web', 'analyze-results']
    
    for arg in args:
        if arg in valid_commands:
            return arg
    
    return None

def suggest_similar_command(invalid_cmd: str, valid_commands: list) -> str:
    """유사한 명령어 제안"""
    # 간단한 문자열 유사성 검사
    suggestions = []
    for cmd in valid_commands:
        # 부분 문자열 매칭
        if invalid_cmd.lower() in cmd.lower() or cmd.lower() in invalid_cmd.lower():
            suggestions.append(cmd)
        # 첫 글자 매칭
        elif cmd.lower().startswith(invalid_cmd.lower()[0]):
            suggestions.append(cmd)
    
    if suggestions:
        return f"혹시 '{suggestions[0]}'를 의도하셨나요?"
    return ""

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
  
  # 데이터 상태 확인 (통합된 check_data_status.py 기능)
  python src/main.py check-data           # 종합 데이터 상태 및 백테스팅 적합성 분석
  python src/main.py check-data --days-back 90 --min-days 45  # 사용자 정의 분석 조건
  
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
  python src/main.py update-data --summary     # 기본 데이터베이스 현황 확인
  python src/main.py update-data --summary --backtest-analysis  # 백테스팅 분석 포함 상세 현황
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
  
  # 결과 저장 (기본값, 비활성화는 --no-save-results 사용)
  python src/main.py backtest --all-kospi --parallel  # 결과 자동 저장
  python src/main.py backtest --symbols 005930 --no-save-results  # 결과 저장하지 않음
  
  # 매개변수 최적화 및 웹 인터페이스
  python src/main.py optimize                 # 매개변수 최적화
  python src/main.py web                      # 웹 인터페이스 실행
  
  # 백테스팅 결과 분석
  python src/main.py analyze-results          # 최신 백테스팅 결과 자동 분석
  python src/main.py analyze-results --auto-find  # 최신 결과 파일 자동 검색 후 분석
  python src/main.py analyze-results --input backtest_results_20241207.json  # 특정 파일 분석
  python src/main.py analyze-results --output my_analysis  # 사용자 정의 출력 디렉토리
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # 패키지 확인 명령어
    subparsers.add_parser('check-deps', help='필수 패키지 설치 확인')
    
    # 데이터 상태 확인 명령어 (통합된 check_data_status.py 기능)
    check_parser = subparsers.add_parser('check-data', help='종합 데이터 상태 확인 (백테스팅 적합성 분석)')
    check_parser.add_argument('--days-back', type=int, default=60, help='분석 기간 (현재부터 N일 전, 기본: 60일)')
    check_parser.add_argument('--min-days', type=int, default=30, help='백테스팅 최소 데이터 요구 일수 (기본: 30일)')
    check_parser.add_argument('--top-limit', type=int, default=20, help='상위 종목 표시 개수 (기본: 20개)')
    
    # 데이터 업데이트 명령어
    update_parser = subparsers.add_parser('update-data', help='주식 데이터 업데이트')
    update_parser.add_argument('--symbols', nargs='+', help='업데이트할 종목 코드들')
    update_parser.add_argument('--top-kospi', type=int, default=30, dest='top_kospi', help='코스피 상위 N개 종목 (기본: 30)')
    update_parser.add_argument('--all-kospi', action='store_true', dest='all_kospi', help='코스피 전체 종목 업데이트 (~962개)')
    update_parser.add_argument('--force', action='store_true', help='강제 업데이트')
    update_parser.add_argument('--summary', action='store_true', help='데이터베이스 현황 보기')
    update_parser.add_argument('--backtest-analysis', action='store_true', dest='backtest_analysis', help='백테스팅 적합성 분석 포함 (--summary와 함께 사용)')
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
    
    # 백테스팅 결과 저장 옵션 (기본 저장)
    backtest_output_group = backtest_parser.add_argument_group('결과 저장 (기본: 저장함)')
    backtest_output_group.add_argument('--no-save-results', action='store_true', help='결과를 저장하지 않음 (기본: 저장함)')
    backtest_output_group.add_argument('--output-dir', default='backtest_results', help='결과 저장 디렉토리 (기본: backtest_results)')
    
    # 최적화 명령어
    optimize_parser = subparsers.add_parser('optimize', help='매개변수 최적화')
    optimize_parser.add_argument('--symbols', nargs='+', help='최적화할 종목 코드들')
    
    # 웹 인터페이스 명령어
    subparsers.add_parser('web', help='Streamlit 웹 인터페이스 실행')
    
    # 백테스팅 결과 분석 명령어
    analyze_parser = subparsers.add_parser('analyze-results', help='백테스팅 결과 분석 및 리포트 생성')
    analyze_parser.add_argument('--input', '-i', 
                               default='backtest_results/backtest_results_latest.json',
                               help='입력 결과 파일 경로 (JSON 형식)')
    analyze_parser.add_argument('--output', '-o', 
                               default='backtest_results/analysis',
                               help='출력 디렉토리 (기본: backtest_results/analysis)')
    analyze_parser.add_argument('--auto-find', action='store_true',
                               help='최신 백테스팅 결과 파일 자동 검색')
    
    # 인자 파싱 및 에러 처리
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse에서 --help나 잘못된 인자로 인한 SystemExit 처리
        if e.code != 0:  # 에러로 인한 종료인 경우
            current_command = get_current_command_from_args()
            
            if current_command:
                # 특정 명령어에서 잘못된 인자 사용
                logger.error(f"\n❌ '{current_command}' 명령어에서 잘못된 인자를 사용했습니다.")
                show_command_help(current_command)
            else:
                # 잘못된 명령어 또는 일반적인 에러
                logger.error("\n❌ 잘못된 명령어 또는 인자입니다.")
                show_available_commands()
        sys.exit(e.code)
    
    if not args.command:
        logger.info("명령어가 지정되지 않았습니다.\n")
        show_available_commands()
        logger.info("\n자세한 사용법은 다음 명령어로 확인하세요:")
        logger.info("python src/main.py --help")
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
            
        elif args.command == 'check-data':
            run_check_data(args)
            
        elif args.command == 'analyze-results':
            run_analyze_results(args)
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
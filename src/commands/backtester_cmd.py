import logging
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from src.data.stock_data_manager import StockDataManager
from src.trading.backtest import BacktestEngine, BacktestConfig
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.bollinger_band_strategy import BollingerBandStrategy
from src.strategies.moving_average_strategy import MovingAverageStrategy
from src.config_loader import get_project_root
from src.utils.common import load_stock_data

logger = logging.getLogger(__name__)
PROJECT_ROOT = get_project_root()

def run_backtest(args):
    """백테스팅을 실행합니다."""
    try:
        logger.info("=== 백테스팅 시작 ===")
        
        db_path = PROJECT_ROOT / "data" / "trading.db"
        if not db_path.exists():
            logger.error("❌ 데이터베이스가 없습니다. 먼저 데이터를 업데이트하세요.")
            logger.info("권장 명령어: python src/main.py update-data --period 2y --parallel")
            return

        dm = StockDataManager(db_path=str(db_path))

        # 심볼 리스트 결정
        symbols = args.symbols or ["005930"]  # 기본값: 삼성전자
        logger.info(f"📊 지정 종목 {len(symbols)}개 백테스팅")
        
        # 백테스팅 실행
        results = run_backtest_with_symbols(
            symbols=symbols,
            strategies=args.strategy if isinstance(args.strategy, list) else [args.strategy],
            start_date=args.start_date,
            end_date=args.end_date,
            days=args.days,
            parallel=args.parallel,
            workers=args.workers,
            chunk_size=args.chunk_size,
            optimizer=getattr(args, 'optimizer', None),
            dm=dm
        )
        
        # 결과 저장 및 출력
        if results and not args.no_save_results:
            save_backtest_results(results)
        
        logger.info("=== 백테스팅 완료 ===")
        
    except Exception as e:
        logger.error(f"백테스팅 실행 중 오류 발생: {e}", exc_info=True)

def run_backtest_with_symbols(symbols, strategies, start_date, end_date, days, parallel, workers, chunk_size, optimizer, dm):
    results = []
    
    # 전략 매핑
    strategy_map = {
        'macd': MACDStrategy,
        'rsi': RSIStrategy,
        'bollinger': BollingerBandStrategy,
        'ma': MovingAverageStrategy
    }
    
    for symbol in symbols:
        try:
            # StockDataManager를 직접 사용하여 데이터 로딩
            df = dm.get_latest_data(symbol, days=days or 730)  # 2년치 데이터
            print(f"{symbol} 원본 row: {len(df)}, 인덱스 타입: {type(df.index)}")
            
            if not df.empty:
                # 날짜 인덱스 변환
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                elif not pd.api.types.is_datetime64_any_dtype(df.index):
                    df.index = pd.to_datetime(df.index)
                
                print(f"{symbol} 인덱스 변환 후: min: {df.index.min() if not df.empty else 'N/A'}, max: {df.index.max() if not df.empty else 'N/A'}")
                
                # 날짜 필터링 (기본값 설정)
                if not start_date:
                    start_date = (df.index.max() - pd.Timedelta(days=730)).strftime('%Y-%m-%d')
                if not end_date:
                    end_date = df.index.max().strftime('%Y-%m-%d')
                
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                df = df[(df.index >= start_dt) & (df.index <= end_dt)]
                print(f"{symbol} 필터링 후 row: {len(df)}, min: {df.index.min() if not df.empty else 'N/A'}, max: {df.index.max() if not df.empty else 'N/A'}")
            else:
                print(f"{symbol} 필터링 후 row: 0")
            
            if not isinstance(df, pd.DataFrame) or df.empty:
                print(f"{symbol}: 유효한 데이터가 없습니다.")
                continue
                
            filtered_data = {symbol: df}
            
            # 전략 인스턴스 생성 (첫 번째 전략 사용)
            strategy_name = strategies[0] if isinstance(strategies, list) else strategies
            strategy_class = strategy_map.get(strategy_name.lower(), RSIStrategy)
            strategy = strategy_class()
            
            print(f"{symbol}: {strategy_name} 전략 사용")
            
            # 백테스트 엔진 및 실행
            config = BacktestConfig(initial_capital=1_000_000)
            engine = BacktestEngine(config)
            result = engine.run_backtest(strategy, filtered_data, start_date, end_date)
            results.append(result)
            
            print(f"{symbol} 결과: 거래수={result['total_trades']}, 수익률={result['total_return']:.2%}, MDD={result['max_drawdown']:.2%}, 샤프={result['sharpe_ratio']:.2f}")
            
        except Exception as e:
            print(f"{symbol} 백테스트 실패: {e}")
            logger.error(f"{symbol} 백테스트 실패: {e}", exc_info=True)
            # 실패한 경우 빈 결과 추가
            results.append({
                'symbol': symbol,
                'total_trades': 0,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'error': str(e)
            })
    
    return results

def save_backtest_results(results):
    # Implementation of save_backtest_results function
    pass
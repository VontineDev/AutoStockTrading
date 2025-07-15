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

logger = logging.getLogger(__name__)
PROJECT_ROOT = get_project_root()

def run_backtest(args):
    """백테스팅 실행 (병렬 처리 지원)"""
    try:
        logger.info("🚀 백테스팅 시작...")

        db_path = PROJECT_ROOT / "data" / "trading.db"
        if not db_path.exists():
            logger.error("❌ 데이터베이스가 없습니다. 먼저 데이터를 업데이트하세요.")
            logger.info(
                "python src/main.py update-data --top-kospi 962 --period 2y --parallel"
            )
            return

        dm = StockDataManager(db_path=str(db_path))

        # 종목 선택 로직
        symbols = []
        if args.all_kospi:
            logger.info("📊 코스피 전체 종목 백테스팅 모드")
            symbols = dm.get_all_symbols()
            logger.info(f"코스피 전체 {len(symbols)}개 종목 대상")
        elif args.top_kospi:
            logger.info(f"📊 코스피 상위 {args.top_kospi}개 종목 백테스팅")
            symbols = dm.get_top_market_cap_symbols(args.top_kospi)
        elif args.symbols:
            symbols = args.symbols
            logger.info(f"📊 지정 종목 {len(symbols)}개 백테스팅")
        else:
            symbols = ["005930"]  # 기본: 삼성전자
            logger.info("📊 기본값: 삼성전자 백테스팅")

        # 백테스팅 기간 설정
        from src.commands.data_updater_cmd import calculate_date_range
        start_date_dt, end_date_dt = calculate_date_range(args)
        start_date = start_date_dt.strftime('%Y-%m-%d')
        end_date = end_date_dt.strftime('%Y-%m-%d')

        logger.info(
            f"📅 백테스팅 기간: {start_date} ~ {end_date} ({args.days}일)"
        )

        # 데이터 로드
        logger.info("📚 데이터 로딩 중...")
        data = {}
        failed_symbols = []
        for symbol in symbols:
            try:
                df = dm.get_stock_data(symbol, start_date, end_date)
                if not df.empty and len(df) >= 20:
                    data[symbol] = df
                    logger.info(f"✅ {symbol}: {len(df)}건 로드")
                else:
                    failed_symbols.append(symbol)
                    logger.info(f"❌ {symbol}: 데이터 부족 ({len(df) if not df.empty else 0}건)")
            except Exception as e:
                failed_symbols.append(symbol)
                logger.error(f"❌ {symbol}: 로드 실패 ({e})")

        if not data:
            logger.error("❌ 백테스팅할 데이터가 없습니다.")
            return

        if failed_symbols:
            logger.warning(f"⚠️  데이터 부족으로 제외된 종목: {len(failed_symbols)}개")

        logger.info(f"✅ 데이터 로드 완료: {len(data)}개 종목")

        # 전략 설정
        strategy_name = getattr(args, "strategy", "macd").lower()
        strategies = {
            "macd": MACDStrategy,
            "rsi": RSIStrategy,
            "bollinger": BollingerBandStrategy,
            "ma": MovingAverageStrategy,
        }

        strategies_to_test = []
        if strategy_name == "all":
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
        force_parallel = getattr(args, "parallel", False)
        force_optimized = getattr(args, "optimized", False)

        # 엔진 선택 로직
        if force_optimized:
            engine_type = "optimized"
            logger.info(f"🎯 사용자 지정: OptimizedBacktestEngine (캐싱 + 병렬 + 배치)")
        elif force_parallel:
            engine_type = "parallel"
            logger.info(f"🎯 사용자 지정: ParallelBacktestEngine (병렬 처리)")
        elif num_symbols >= 100:
            engine_type = "optimized"
            logger.info(
                f"🚀 자동 선택: OptimizedBacktestEngine (대규모 {num_symbols}개 종목)"
            )
            logger.info("   └─ 이유: 캐싱 + 메모리 최적화 + 병렬 처리로 최고 성능")
        elif num_symbols >= 10:
            engine_type = "parallel"
            logger.info(
                f"⚡ 자동 선택: ParallelBacktestEngine (중규모 {num_symbols}개 종목)"
            )
            logger.info("   └─ 이유: 병렬 처리로 최적 성능/안정성 균형")
        else:
            engine_type = "sequential"
            logger.info(f"🐌 자동 선택: BacktestEngine (소규모 {num_symbols}개 종목)")
            logger.info("   └─ 이유: 순차 처리로 디버깅 및 상세 분석 최적화")

        # 성능 예측 정보 출력
        if num_symbols > 1:
            if engine_type == "optimized":
                estimated_time = max(30, num_symbols * 0.15)  # 대규모에서 캐싱 효과
                logger.info(
                    f"   ⏱️  예상 소요 시간: {estimated_time:.0f}초 (캐시 히트 시 90% 단축)"
                )
            elif engine_type == "parallel":
                estimated_time = max(10, num_symbols * 0.25)  # 병렬 처리 효과
                logger.info(
                    f"   ⏱️  예상 소요 시간: {estimated_time:.0f}초 (순차 대비 {min(args.workers, 8)}배 빠름)"
                )
            else:
                estimated_time = num_symbols * 2  # 순차 처리
                logger.info(
                    f"   ⏱️  예상 소요 시간: {estimated_time:.0f}초 (상세 분석 포함)"
                )

        # 선택된 엔진으로 백테스팅 실행
        all_results = {}
        total_start_time = time.time()

        if engine_type == "optimized":
            # OptimizedBacktestEngine 사용
            logger.info(f"\n🚀 최적화 엔진 시작 (워커: {args.workers}개, 캐시: 활성화)")
            logger.info("   📊 내부적으로 병렬 처리와 캐싱을 통합 운영합니다")

            from src.trading.optimized_backtest import (
                OptimizedBacktestEngine,
                OptimizedBacktestConfig,
            )

            optimized_config = OptimizedBacktestConfig(
                max_workers=args.workers,
                chunk_size=args.chunk_size,
                enable_cache=True,
                cache_max_age_hours=24,
                batch_size=args.chunk_size,
                max_memory_usage_mb=1024,
                initial_capital=1000000,
            )

            optimized_engine = OptimizedBacktestEngine(optimized_config)

            for strategy_name, strategy_class in strategies_to_test:
                logger.info(f"\n🔄 {strategy_name} 전략 최적화 백테스팅 실행...")
                strategy_start_time = time.time()

                optimized_results = optimized_engine.run_optimized_backtest(
                    strategy_class=strategy_class,
                    symbols=list(data.keys()),
                    strategy_params={},
                    days=args.days,
                )

                strategy_elapsed = time.time() - strategy_start_time
                logger.info(f"✅ {strategy_name} 완료: {strategy_elapsed:.1f}초")

                # 최적화 성능 정보 출력
                opt_stats = optimized_results.get("optimization_stats", {})
                cache_efficiency = opt_stats.get("cache_efficiency", 0)
                memory_efficiency = opt_stats.get("memory_efficiency", 0)
                if cache_efficiency > 0 or memory_efficiency > 0:
                    logger.info(
                        f"   └─ 캐시 효율성: {cache_efficiency:.1%}, 메모리 효율성: {memory_efficiency:.1%}"
                    )

                all_results[strategy_name] = optimized_results

        elif engine_type == "parallel":
            # ParallelBacktestEngine 사용
            logger.info(
                f"\n⚡ 병렬 엔진 시작 (워커: {args.workers}개, 청크: {args.chunk_size}개)"
            )

            from src.trading.parallel_backtest import (
                ParallelBacktestEngine,
                ParallelBacktestConfig,
            )

            parallel_config = ParallelBacktestConfig(
                max_workers=args.workers,
                chunk_size=args.chunk_size,
                timeout=600,  # 10분 타임아웃
            )

            parallel_engine = ParallelBacktestEngine(parallel_config)

            for strategy_name, strategy_class in strategies_to_test:
                logger.info(f"\n🔄 {strategy_name} 전략 병렬 백테스팅 실행...")
                strategy_start_time = time.time()

                parallel_results = parallel_engine.run_parallel_backtest(
                    strategy_class=strategy_class,
                    symbols_data=data,
                    strategy_params={},
                    backtest_config={"initial_capital": 1000000},
                )

                strategy_elapsed = time.time() - strategy_start_time
                success_count = parallel_results["performance_stats"][
                    "successful_backtests"
                ]
                success_rate = success_count / num_symbols * 100
                processing_speed = num_symbols / strategy_elapsed

                logger.info(f"✅ {strategy_name} 완료: {strategy_elapsed:.1f}초")
                logger.info(
                    f"   └─ 성공률: {success_rate:.1f}% ({success_count}/{num_symbols}) | 처리 속도: {processing_speed:.1f} 종목/초"
                )

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
                results = engine.run_backtest(
                    strategy,
                    data,
                    start_date,
                    end_date,
                )

                strategy_elapsed = time.time() - strategy_start_time
                total_trades = results.get("total_trades", 0)
                total_return = results.get("total_return", 0)

                logger.info(f"✅ {strategy_name} 완료: {strategy_elapsed:.1f}초")
                logger.info(
                    f"   └─ 총 거래: {total_trades}회, 수익률: {total_return:.2%}"
                )

                all_results[strategy_name] = {"results": {f"portfolio": results}}

        # 전체 실행 시간 계산
        total_elapsed = time.time() - total_start_time
        logger.info(f"\n🏁 전체 백테스팅 완료: {total_elapsed:.1f}초")

        # 성능 평가 출력
        if num_symbols > 1:
            overall_speed = num_symbols * len(strategies_to_test) / total_elapsed
            logger.info(f"   📈 전체 처리 속도: {overall_speed:.1f} 종목×전략/초")

            if engine_type == "parallel":
                efficiency = min(args.workers, num_symbols) / (
                    total_elapsed / (num_symbols * len(strategies_to_test) * 2)
                )
                logger.info(
                    f"   ⚡ 병렬 처리 효율성: {efficiency:.1f}배 (순차 처리 대비)"
                )
            elif engine_type == "optimized":
                logger.info(f"   🚀 최적화 엔진 선택으로 대규모 처리 성공")

        # 결과 출력 및 저장
        logger.info("\n" + "=" * 60)
        logger.info("📊 백테스팅 결과 요약")
        logger.info("=" * 60)

        for strategy_name, strategy_results in all_results.items():
            logger.info(f"\n🎯 [{strategy_name.upper()} 전략]")

            if "results" in strategy_results:
                results_data = strategy_results["results"]

                # 성과 통계 계산
                if results_data:
                    # 첫 번째 종목의 결과 구조 확인
                    sample_result = next(iter(results_data.values()))

                    if isinstance(sample_result, dict):
                        total_returns = [
                            r.get("total_return", 0)
                            for r in results_data.values()
                            if isinstance(r, dict)
                        ]
                        sharpe_ratios = [
                            r.get("sharpe_ratio", 0)
                            for r in results_data.values()
                            if isinstance(r, dict)
                        ]
                        max_drawdowns = [
                            r.get("max_drawdown", 0)
                            for r in results_data.values()
                            if isinstance(r, dict)
                        ]
                        win_rates = [
                            r.get("win_rate", 0)
                            for r in results_data.values()
                            if isinstance(r, dict)
                        ]
                        total_trades = [
                            r.get("total_trades", 0)
                            for r in results_data.values()
                            if isinstance(r, dict)
                        ]

                        if total_returns:
                            logger.info(
                                f"  평균 수익률: {sum(total_returns)/len(total_returns):.2%}"
                            )
                            logger.info(
                                f"  평균 샤프 비율: {sum(sharpe_ratios)/len(sharpe_ratios):.3f}"
                            )
                            logger.info(
                                f"  평균 최대 낙폭: {sum(max_drawdowns)/len(max_drawdowns):.2%}"
                            )
                            logger.info(
                                f"  평균 승률: {sum(win_rates)/len(win_rates):.2%}"
                            )
                            logger.info(f"  총 거래 수: {sum(total_trades):,}회")
                            logger.info(f"  처리 종목 수: {len(results_data)}개")

        # 결과 저장 (기본 저장, --no-save-results로 비활성화 가능)
        if not getattr(args, "no_save_results", False):
            output_dir = Path(args.output_dir)
            output_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # JSON 저장
            json_file = output_dir / f"backtest_results_{timestamp}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"\n💾 결과 저장됨: {json_file}")

        logger.info("\n✅ 백테스팅 완료!")

    except Exception as e:
        import traceback

        logger.error(f"❌ 백테스팅 실패: {e}")
        logger.error(traceback.format_exc())
        logger.error(f"백테스팅 실패: {e}")
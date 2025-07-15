import logging
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
from src.config_loader import get_project_root

logger = logging.getLogger(__name__)
PROJECT_ROOT = get_project_root()

def load_backtest_results(file_path: str) -> dict:
    """백테스팅 결과 파일 로드"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"결과 파일 로드 실패: {e}")
        return {}

def analyze_backtest_results_data(results: dict) -> pd.DataFrame:
    """결과 분석 및 DataFrame 변환"""
    all_results = []
    for strategy, strategy_data in results.items():
        if "results" not in strategy_data:
            continue
        for symbol, data in strategy_data["results"].items():
            if not data.get("success", False):
                continue
            if data.get("total_trades", 0) == 0:
                continue
            result_row = {
                "strategy": strategy.upper(),
                "symbol": symbol,
                "total_return": data.get("total_return", 0) * 100,
                "sharpe_ratio": data.get("sharpe_ratio", 0),
                "max_drawdown": data.get("max_drawdown", 0) * 100,
                "win_rate": data.get("win_rate", 0) * 100,
                "total_trades": data.get("total_trades", 0),
                "data_points": data.get("data_points", 0),
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

    logger.info("📈 수익률 기준 상위 종목 분석...")
    top_returns = df.nlargest(50, "total_return")
    returns_file = output_path / f"top_returns_{timestamp}.csv"
    top_returns.to_csv(returns_file, index=False, encoding="utf-8-sig")

    logger.info("🎯 승률 기준 상위 종목 분석...")
    top_winrates = df.nlargest(50, "win_rate")
    winrates_file = output_path / f"top_winrates_{timestamp}.csv"
    top_winrates.to_csv(winrates_file, index=False, encoding="utf-8-sig")

    logger.info("⚖️ 샤프 비율 기준 상위 종목 분석...")
    top_sharpe = df.nlargest(50, "sharpe_ratio")
    sharpe_file = output_path / f"top_sharpe_{timestamp}.csv"
    top_sharpe.to_csv(sharpe_file, index=False, encoding="utf-8-sig")

    logger.info("🏆 종합 점수 기준 상위 종목 분석...")
    df["composite_score"] = (
        df["total_return"].fillna(0) * 0.4
        + df["win_rate"].fillna(0) * 0.3
        + df["sharpe_ratio"].fillna(0) * 30 * 0.3
    )
    top_composite = df.nlargest(50, "composite_score")
    composite_file = output_path / f"top_composite_{timestamp}.csv"
    top_composite.to_csv(composite_file, index=False, encoding="utf-8-sig")

    logger.info("📊 전략별 통계 분석...")
    strategy_stats = (
        df.groupby("strategy")
        .agg(
            {
                "total_return": ["mean", "median", "std", "max", "min"],
                "win_rate": ["mean", "median", "std", "max", "min"],
                "sharpe_ratio": ["mean", "median", "std", "max", "min"],
                "total_trades": ["sum", "mean"],
                "symbol": "count",
            }
        )
        .round(4)
    )
    strategy_stats.columns = ["_".join(col).strip() for col in strategy_stats.columns]
    strategy_file = output_path / f"strategy_stats_{timestamp}.csv"
    strategy_stats.to_csv(strategy_file, encoding="utf-8-sig")

    logger.info("📋 상세 분석 보고서 생성...")
    create_detailed_report(
        df,
        top_returns,
        top_winrates,
        top_sharpe,
        top_composite,
        strategy_stats,
        output_path,
        timestamp,
    )

    return {
        "top_returns": returns_file,
        "top_winrates": winrates_file,
        "top_sharpe": sharpe_file,
        "top_composite": composite_file,
        "strategy_stats": strategy_file,
    }

def create_detailed_report(
    df, top_returns, top_winrates, top_sharpe, top_composite, strategy_stats, output_path, timestamp
):
    """상세 분석 보고서 생성"""
    report_file = output_path / f"detailed_report_{timestamp}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# 백테스팅 결과 상세 분석 보고서\n\n")
        f.write(f"**생성 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**분석 대상**: {len(df)}개 종목×전략 조합 (거래 발생 건만)\n\n")
        f.write("## 📊 전체 통계 요약\n\n")
        f.write(f"- **평균 수익률**: {df['total_return'].mean():.2f}%\n")
        f.write(f"- **평균 승률**: {df['win_rate'].mean():.2f}%\n")
        f.write(f"- **평균 샤프 비율**: {df['sharpe_ratio'].mean():.3f}\n")
        f.write(f"- **총 거래 수**: {df['total_trades'].sum():,}회\n")
        f.write(
            f"- **수익률 > 0%**: {len(df[df['total_return'] > 0])}개 ({len(df[df['total_return'] > 0])/len(df)*100:.1f}%)\n"
        )
        f.write(
            f"- **승률 > 50%**: {len(df[df['win_rate'] > 50])}개 ({len(df[df['win_rate'] > 50])/len(df)*100:.1f}%)\n\n"
        )
        f.write("## 🥇 수익률 TOP 10\n\n")
        f.write("| 순위 | 전략 | 종목 | 수익률 | 승률 | 샤프비율 | 거래수 |\n")
        f.write("|------|------|------|--------|------|----------|--------|\n")
        for i, row in top_returns.head(10).iterrows():
            f.write(
                f"| {len(top_returns) - list(top_returns.index).index(i)} | {row['strategy']} | {row['symbol']} | "
                f"{row['total_return']:.2f}% | {row['win_rate']:.1f}% | {row['sharpe_ratio']:.3f} | {row['total_trades']} |\n"
            )
        f.write("\n")
        f.write("## 🎯 승률 TOP 10\n\n")
        f.write("| 순위 | 전략 | 종목 | 승률 | 수익률 | 샤프비율 | 거래수 |\n")
        f.write("|------|------|------|------|--------|----------|--------|\n")
        for i, row in top_winrates.head(10).iterrows():
            f.write(
                f"| {len(top_winrates) - list(top_winrates.index).index(i)} | {row['strategy']} | {row['symbol']} | "
                f"{row['win_rate']:.1f}% | {row['total_return']:.2f}% | {row['sharpe_ratio']:.3f} | {row['total_trades']} |\n"
            )
        f.write("\n")
        f.write("## ⚖️ 샤프 비율 TOP 10\n\n")
        f.write("| 순위 | 전략 | 종목 | 샤프비율 | 수익률 | 승률 | 거래수 |\n")
        f.write("|------|------|------|----------|--------|------|--------|\n")
        for i, row in top_sharpe.head(10).iterrows():
            f.write(
                f"| {len(top_sharpe) - list(top_sharpe.index).index(i)} | {row['strategy']} | {row['symbol']} | "
                f"{row['sharpe_ratio']:.3f} | {row['total_return']:.2f}% | {row['win_rate']:.1f}% | {row['total_trades']} |\n"
            )
        f.write("\n")
        f.write("## 🏆 종합 점수 TOP 10\n\n")
        f.write(
            "| 순위 | 전략 | 종목 | 종합점수 | 수익률 | 승률 | 샤프비율 | 거래수 |\n"
        )
        f.write(
            "|------|------|------|----------|--------|------|----------|--------|\n"
        )
        for i, row in top_composite.head(10).iterrows():
            f.write(
                f"| {len(top_composite) - list(top_composite.index).index(i)} | {row['strategy']} | {row['symbol']} | "
                f"{row['composite_score']:.2f} | {row['total_return']:.2f}% | {row['win_rate']:.1f}% | "
                f"{row['sharpe_ratio']:.3f} | {row['total_trades']} |\n"
            )
        f.write("\n")
        f.write("## 📈 전략별 성과 비교\n\n")
        f.write(
            "| 전략 | 평균 수익률 | 평균 승률 | 평균 샤프비율 | 총 거래수 | 종목수 |\n"
        )
        f.write(
            "|------|-------------|-----------|---------------|----------|--------|\n"
        )
        for strategy in strategy_stats.index:
            f.write(
                f"| {strategy} | {strategy_stats.loc[strategy, 'total_return_mean']:.2f}% | "
                f"{strategy_stats.loc[strategy, 'win_rate_mean']:.1f}% | "
                f"{strategy_stats.loc[strategy, 'sharpe_ratio_mean']:.3f} | "
                f"{strategy_stats.loc[strategy, 'total_trades_sum']:.0f} | "
                f"{strategy_stats.loc[strategy, 'symbol_count']:.0f} |\n"
            )
        f.write("\n")
        f.write("## 💡 투자 추천 종목\n\n")
        recommended = top_composite.head(5)
        f.write(
            "**종합 점수 기준 상위 5개 종목 (수익률, 승률, 샤프비율 종합 고려)**\n\n"
        )
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
    if args.auto_find or not Path(args.input).exists():
        backtest_dir = PROJECT_ROOT / "backtest_results"
        if not backtest_dir.exists():
            logger.error(f"백테스팅 결과 디렉토리가 없습니다: {backtest_dir}")
            return
        json_files = list(backtest_dir.glob("backtest_results_*.json"))
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
    results = load_backtest_results(str(input_file))
    if not results:
        logger.error("결과 파일을 로드할 수 없습니다.")
        return
    df = analyze_backtest_results_data(results)
    if df.empty:
        logger.error("분석할 데이터가 없습니다.")
        return
    logger.info(f"📊 총 {len(df)}개 종목×전략 조합 분석 중...")
    output_files = create_sorted_analysis(df, args.output)
    logger.info("\n" + "=" * 60)
    logger.info("✅ 분석 완료!")
    logger.info("=" * 60)
    logger.info("📁 생성된 파일:")
    for name, path in output_files.items():
        logger.info(f"   • {name}: {path}")
    logger.info("\n📊 분석 요약:")
    logger.info(f"   • 전체 결과: {len(df)}개")
    logger.info(
        f"   • 수익률 > 0%: {len(df[df['total_return'] > 0])}개 ({len(df[df['total_return'] > 0])/len(df)*100:.1f}%)"
    )
    logger.info(
        f"   • 승률 > 50%: {len(df[df['win_rate'] > 50])}개 ({len(df[df['win_rate'] > 50])/len(df)*100:.1f}%)"
    )
    logger.info(f"   • 최고 수익률: {df['total_return'].max():.2f}%")
    logger.info(f"   • 최고 승률: {df['win_rate'].max():.1f}%")
    if "composite_score" in df.columns:
        top_5 = df.nlargest(5, "composite_score")
        logger.info("\n💡 TOP 5 추천 종목 (종합 점수 기준):")
        for i, (_, row) in enumerate(top_5.iterrows(), 1):
            logger.info(
                f"   {i}. {row['symbol']} ({row['strategy']}) - "
                f"수익률: {row['total_return']:.2f}%, "
                f"승률: {row['win_rate']:.1f}%, "
                f"샤프: {row['sharpe_ratio']:.3f}"
            )

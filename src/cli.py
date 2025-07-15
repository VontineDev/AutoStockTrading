#!/usr/bin/env python3
"""
TA-Lib 스윙 트레이딩 자동매매 시스템 메인 진입점

pykrx + TA-Lib 기반의 100만원 규모 스윙 트레이딩 시스템
"""

import sys
import os
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 sys.path에 추가하여 src.config_loader 등을 임포트할 수 있도록 함
# 이 코드는 다른 모듈 임포트 전에 위치해야 함
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config_loader import CONFIG, get_project_root
from src.utils.logging_utils import setup_logging
from src.data.database import DatabaseManager
from src.utils.display_utils import display_data_summary
import pandas as pd
import numpy as np

# --- 초기 설정 ---
# 프로젝트 루트 디렉토리
PROJECT_ROOT = get_project_root()

# 로깅 설정 (config.yaml 기반)
log_config = CONFIG.get('logging', {})
setup_logging(
    log_dir=log_config.get('log_dir', PROJECT_ROOT / 'logs'),
    log_level=getattr(logging, log_config.get('level', 'INFO').upper(), logging.INFO)
)
logger = logging.getLogger(__name__)

# Streamlit 환경에서도 DEBUG 레벨 강제 적용
try:
    import streamlit as st
    logging.getLogger().setLevel(logging.DEBUG)
except ImportError:
    pass


from src.commands.checker_cmd import run_check_data, check_dependencies


from src.commands.data_updater_cmd import run_data_update, calculate_date_range


from src.commands.backtester_cmd import run_backtest


from src.commands.web_cmd import run_streamlit





from src.commands.analyzer_cmd import run_analyze_results


def show_available_commands():
    """사용 가능한 명령어 목록 표시"""
    commands = {
        "check-deps": "필수 패키지 설치 확인",
        "check-data": "종합 데이터 상태 확인 (백테스팅 적합성 분석)",
        "update-data": "주식 데이터 업데이트",
        "backtest": "백테스팅 실행",
        "web": "Streamlit 웹 인터페이스 실행",
        "analyze-results": "백테스팅 결과 분석 및 리포트 생성",
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
        "check-deps": ["python src/main.py check-deps"],
        "check-data": [
            "python src/main.py check-data",
            "python src/main.py check-data --days-back 90 --min-days 45",
            "python src/main.py check-data --top-limit 30",
        ],
        "update-data": [
            "python src/main.py update-data",
            "python src/main.py update-data --symbols 005930 000660",
            "python src/main.py update-data --top-kospi 50",
            "python src/main.py update-data --all-kospi",
            "python src/main.py update-data --all-kospi --parallel --workers 8",
            "python src/main.py update-data --days 180",
            "python src/main.py update-data --period 6m",
            "python src/main.py update-data --period 2y",
            "python src/main.py update-data --start-date 2024-01-01",
            "python src/main.py update-data --yesterday-only",
            "python src/main.py update-data --all-kospi --yesterday-only",
            "python src/main.py update-data --summary",
            "python src/main.py update-data --api-status",
        ],
        "backtest": [
            "python src/main.py backtest",
            "python src/main.py backtest --symbols 005930 000660",
            "python src/main.py backtest --top-kospi 10",
            "python src/main.py backtest --all-kospi",
            "python src/main.py backtest --strategy rsi",
            "python src/main.py backtest --days 365",
            "python src/main.py backtest --start-date 2024-01-01 --end-date 2024-06-30",
            "python src/main.py backtest --parallel --workers 8",
            "python src/main.py backtest --optimized --chunk-size 50",
        ],
        "web": ["python src/main.py web"],
        "analyze-results": [
            "python src/main.py analyze-results",
            "python src/main.py analyze-results --auto-find",
            "python src/main.py analyze-results --input results.json",
            "python src/main.py analyze-results --output my_analysis",
        ],
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

    valid_commands = [
        "check-deps",
        "check-data",
        "update-data",
        "backtest",
        "web",
        "analyze-results",
    ]

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
    logger.info(f"=== {CONFIG['project']['name']} v{CONFIG['project']['version']} ===")

    # 인자 파서 설정
    parser = argparse.ArgumentParser(
        description="TA-Lib 스윙 트레이딩 자동매매 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python src/main.py check-deps           # 패키지 설치 확인
  
  # 데이터 상태 확인 (통합된 check_data_status.py 기능)
  python src/main.py check-data           # 종합 데이터 상태 및 백테스팅 적합성 분석
  python src/main.py check-data --days-back 90 --min-days 45  # 사용자 정의 분석 조건
  
  # 데이터 업데이트 (기본: 전체 시장 1년 데이터)
  python src/main.py update-data          # 전체 시장(코스피, 코스닥) 1년 데이터 업데이트
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
  
  # 웹 인터페이스
  python src/main.py web                      # 웹 인터페이스 실행
  
  # 백테스팅 결과 분석
  python src/main.py analyze-results          # 최신 백테스팅 결과 자동 분석
  python src/main.py analyze-results --auto-find  # 최신 결과 파일 자동 검색 후 분석
  python src/main.py analyze-results --input backtest_results_20241207.json  # 특정 파일 분석
  python src/main.py analyze-results --output my_analysis  # 사용자 정의 출력 디렉토리
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")

    # 패키지 확인 명령어
    subparsers.add_parser("check-deps", help="필수 패키지 설치 확인")

    # 데이터 상태 확인 명령어 (통합된 check_data_status.py 기능)
    check_parser = subparsers.add_parser(
        "check-data", help="종합 데이터 상태 확인 (백테스팅 적합성 분석)"
    )
    check_parser.add_argument(
        "--days-back",
        type=int,
        default=60,
        help="분석 기간 (현재부터 N일 전, 기본: 60일)",
    )
    check_parser.add_argument(
        "--min-days",
        type=int,
        default=30,
        help="백테스팅 최소 데이터 요구 일수 (기본: 30일)",
    )
    check_parser.add_argument(
        "--top-limit", type=int, default=20, help="상위 종목 표시 개수 (기본: 20개)"
    )

    # 데이터 업데이트 명령어
    update_parser = subparsers.add_parser("update-data", help="주식 데이터 업데이트")
    update_parser.add_argument("--symbols", nargs="+", help="업데이트할 종목 코드들")
    update_parser.add_argument(
        "--top-kospi",
        type=int,
        dest="top_kospi",
        help="코스피 상위 N개 종목. 지정하지 않으면 전체 시장을 업데이트합니다.",
    )
    update_parser.add_argument(
        "--all-kospi",
        action="store_true",
        dest="all_kospi",
        help="코스피 전체 종목 업데이트 (~962개)",
    )
    update_parser.add_argument("--force", action="store_true", help="강제 업데이트")
    update_parser.add_argument(
        "--summary", action="store_true", help="데이터베이스 현황 보기"
    )
    update_parser.add_argument(
        "--backtest-analysis",
        action="store_true",
        dest="backtest_analysis",
        help="백테스팅 적합성 분석 포함 (--summary와 함께 사용)",
    )
    update_parser.add_argument(
        "--api-status",
        action="store_true",
        dest="api_status",
        help="API 사용량 현황 보기",
    )
    update_parser.add_argument(
        "--yesterday-only",
        "-y",
        action="store_true",
        dest="yesterday_only",
        help="전날 데이터만 업데이트 (효율적)",
    )

    # 날짜 범위 옵션 추가
    date_group = update_parser.add_argument_group("날짜 범위 설정")
    date_group.add_argument(
        "--days", type=int, help="현재부터 N일 전까지 데이터 수집 (예: 180)"
    )
    date_group.add_argument(
        "--start-date", help="시작 날짜 (YYYY-MM-DD 또는 YYYYMMDD 형식)"
    )
    date_group.add_argument(
        "--end-date", help="종료 날짜 (YYYY-MM-DD 또는 YYYYMMDD 형식, 기본: 오늘)"
    )
    date_group.add_argument(
        "--period",
        choices=["1w", "1m", "3m", "6m", "1y", "2y"],
        default="1y",
        help="기본 수집 기간 (기본: 1y=1년)",
    )

    # 병렬 처리 옵션 추가
    parallel_group = update_parser.add_argument_group("병렬 처리 설정")
    parallel_group.add_argument(
        "--parallel",
        "-p",
        action="store_true",
        help="병렬 처리로 데이터 수집 (빠른 속도)",
    )
    parallel_group.add_argument(
        "--workers", type=int, default=5, help="병렬 처리 워커 수 (기본: 5)"
    )

    # 백테스팅 명령어
    backtest_parser = subparsers.add_parser("backtest", help="백테스팅 실행")
    backtest_parser.add_argument("--symbols", nargs="+", help="백테스팅할 종목 코드들")
    backtest_parser.add_argument(
        "--top-kospi", type=int, help="코스피 상위 N개 종목 백테스팅"
    )
    backtest_parser.add_argument(
        "--all-kospi", action="store_true", help="코스피 전체 종목 백테스팅 (962개)"
    )
    backtest_parser.add_argument(
        "--start-date", dest="start_date", help="백테스팅 시작날짜 (YYYY-MM-DD)"
    )
    backtest_parser.add_argument(
        "--end-date", dest="end_date", help="백테스팅 종료날짜 (YYYY-MM-DD)"
    )
    backtest_parser.add_argument(
        "--days", type=int, default=180, help="백테스팅 기간 (일수, 기본: 180일)"
    )
    backtest_parser.add_argument(
        "--strategy",
        choices=["macd", "rsi", "bollinger", "ma", "all"],
        default="macd",
        help="사용할 전략 (기본: macd, all: 모든 전략)",
    )

    # 백테스팅 병렬 처리 옵션
    backtest_parallel_group = backtest_parser.add_argument_group(
        "엔진 선택 및 성능 설정"
    )
    backtest_parallel_group.add_argument(
        "--parallel",
        "-p",
        action="store_true",
        help="병렬 처리 엔진 강제 사용 (중규모 최적)",
    )
    backtest_parallel_group.add_argument(
        "--optimized",
        "-o",
        action="store_true",
        help="최적화 엔진 강제 사용 (대규모 최적, 캐싱)",
    )
    backtest_parallel_group.add_argument(
        "--workers", type=int, default=4, help="병렬 처리 워커 수 (기본: 4)"
    )
    backtest_parallel_group.add_argument(
        "--chunk-size", type=int, default=20, help="청크당 종목 수 (기본: 20)"
    )

    # 자동 엔진 선택 안내
    engine_help = backtest_parser.add_argument_group("자동 엔진 선택 (옵션 미지정 시)")
    engine_help.description = """
🤖 종목 수에 따른 자동 엔진 선택:
• 1-9개 종목: BacktestEngine (순차 처리, 디버깅 최적)
• 10-99개 종목: ParallelBacktestEngine (병렬 처리, 성능/안정성 균형)  
• 100개+ 종목: OptimizedBacktestEngine (캐싱+병렬+배치, 최고 성능)
"""

    # 백테스팅 결과 저장 옵션 (기본 저장)
    backtest_output_group = backtest_parser.add_argument_group(
        "결과 저장 (기본: 저장함)"
    )
    backtest_output_group.add_argument(
        "--no-save-results",
        action="store_true",
        help="결과를 저장하지 않음 (기본: 저장함)",
    )
    backtest_output_group.add_argument(
        "--output-dir",
        default="backtest_results",
        help="결과 저장 디렉토리 (기본: backtest_results)",
    )

    # 웹 인터페이스 명령어
    subparsers.add_parser("web", help="Streamlit 웹 인터페이스 실행")

    # 백테스팅 결과 분석 명령어
    analyze_parser = subparsers.add_parser(
        "analyze-results", help="백테스팅 결과 분석 및 리포트 생성"
    )
    analyze_parser.add_argument(
        "--input",
        "-i",
        default="backtest_results/backtest_results_latest.json",
        help="입력 결과 파일 경로 (JSON 형식)",
    )
    analyze_parser.add_argument(
        "--output",
        "-o",
        default="backtest_results/analysis",
        help="출력 디렉토리 (기본: backtest_results/analysis)",
    )
    analyze_parser.add_argument(
        "--auto-find", action="store_true", help="최신 백테스팅 결과 파일 자동 검색"
    )

    # 인자 파싱 및 에러 처리
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse에서 --help나 잘못된 인자로 인한 SystemExit 처리
        if e.code != 0:  # 에러로 인한 종료인 경우
            current_command = get_current_command_from_args()

            if current_command:
                # 특정 명령어에서 잘못된 인자 사용
                logger.error(
                    f"\n❌ '{current_command}' 명령어에서 잘못된 인자를 사용했습니다."
                )
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
        if args.command == "check-deps":
            if check_dependencies():
                logger.info("\n시스템이 정상적으로 설정되었습니다!")
            else:
                sys.exit(1)

        elif args.command == "update-data":
            run_data_update(args)

        elif args.command == "backtest":
            run_backtest(args)

        elif args.command == "web":
            run_streamlit()

        elif args.command == "check-data":
            run_check_data(args)

        elif args.command == "analyze-results":
            run_analyze_results(args)

    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

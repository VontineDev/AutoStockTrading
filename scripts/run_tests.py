#!/usr/bin/env python3
"""
테스트 실행기

커서룰의 테스트 원칙에 따라 전체 테스트 스위트를 실행하고 커버리지를 보고
"""

import sys
import unittest
import logging
from pathlib import Path
import subprocess
import time
from typing import Dict, List, Any

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / 'logs' / 'test_results.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def discover_and_run_tests(test_directory: str = "tests", verbosity: int = 2) -> Dict[str, Any]:
    """
    테스트 디렉토리에서 모든 테스트를 발견하고 실행
    
    Args:
        test_directory: 테스트 디렉토리 경로
        verbosity: 테스트 출력 상세도 (0-2)
    
    Returns:
        테스트 결과 딕셔너리
    """
    logger.info(f"🧪 테스트 발견 및 실행 시작: {test_directory}")
    
    # 테스트 디렉토리 경로
    test_path = PROJECT_ROOT / test_directory
    
    if not test_path.exists():
        logger.error(f"테스트 디렉토리가 존재하지 않습니다: {test_path}")
        return {"error": f"테스트 디렉토리 없음: {test_path}"}
    
    # 테스트 발견
    loader = unittest.TestLoader()
    start_dir = str(test_path)
    
    try:
        test_suite = loader.discover(start_dir, pattern='test_*.py')
        
        # 테스트 실행
        start_time = time.time()
        runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
        result = runner.run(test_suite)
        end_time = time.time()
        
        # 결과 정리
        test_results = {
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0,
            "success": result.wasSuccessful(),
            "execution_time": end_time - start_time,
            "failure_details": [str(failure) for failure in result.failures],
            "error_details": [str(error) for error in result.errors]
        }
        
        # 결과 로깅
        logger.info(f"✅ 테스트 실행 완료")
        logger.info(f"   총 테스트: {test_results['tests_run']}")
        logger.info(f"   성공: {test_results['tests_run'] - test_results['failures'] - test_results['errors']}")
        logger.info(f"   실패: {test_results['failures']}")
        logger.info(f"   오류: {test_results['errors']}")
        logger.info(f"   건너뜀: {test_results['skipped']}")
        logger.info(f"   실행 시간: {test_results['execution_time']:.2f}초")
        logger.info(f"   전체 성공: {'✅' if test_results['success'] else '❌'}")
        
        return test_results
        
    except Exception as e:
        logger.error(f"테스트 실행 중 오류 발생: {e}")
        return {"error": str(e)}


def run_specific_test_file(test_file: str, verbosity: int = 2) -> Dict[str, Any]:
    """
    특정 테스트 파일 실행
    
    Args:
        test_file: 테스트 파일명 (예: "test_constants.py")
        verbosity: 출력 상세도
    
    Returns:
        테스트 결과 딕셔너리
    """
    logger.info(f"🎯 특정 테스트 파일 실행: {test_file}")
    
    test_path = PROJECT_ROOT / "tests" / test_file
    
    if not test_path.exists():
        logger.error(f"테스트 파일이 존재하지 않습니다: {test_path}")
        return {"error": f"테스트 파일 없음: {test_path}"}
    
    try:
        # 모듈 로드 및 테스트 실행
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(f"tests.{test_file[:-3]}")  # .py 제거
        
        start_time = time.time()
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)
        end_time = time.time()
        
        test_results = {
            "test_file": test_file,
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "success": result.wasSuccessful(),
            "execution_time": end_time - start_time
        }
        
        logger.info(f"✅ {test_file} 테스트 완료: {test_results['tests_run']}개 실행, "
                   f"성공: {'✅' if test_results['success'] else '❌'}")
        
        return test_results
        
    except Exception as e:
        logger.error(f"{test_file} 테스트 실행 중 오류: {e}")
        return {"error": str(e)}


def run_test_coverage_analysis() -> Dict[str, Any]:
    """
    테스트 커버리지 분석 실행 (coverage.py 사용)
    
    Returns:
        커버리지 분석 결과
    """
    logger.info("📊 테스트 커버리지 분석 시작")
    
    try:
        # coverage 패키지 설치 확인
        import coverage
        
        # 커버리지 분석 실행
        cov = coverage.Coverage()
        cov.start()
        
        # 모든 테스트 실행
        test_results = discover_and_run_tests(verbosity=1)
        
        cov.stop()
        cov.save()
        
        # 커버리지 보고서 생성
        coverage_report = {}
        
        # 콘솔 보고서
        import io
        report_output = io.StringIO()
        cov.report(file=report_output)
        coverage_report['console_report'] = report_output.getvalue()
        
        # HTML 보고서 생성 (선택사항)
        html_dir = PROJECT_ROOT / "coverage_html"
        cov.html_report(directory=str(html_dir))
        coverage_report['html_report_path'] = str(html_dir)
        
        logger.info("✅ 커버리지 분석 완료")
        logger.info(f"HTML 보고서: {coverage_report['html_report_path']}")
        
        return {
            "test_results": test_results,
            "coverage": coverage_report
        }
        
    except ImportError:
        logger.warning("coverage 패키지가 설치되지 않음. pip install coverage로 설치하세요.")
        return {"error": "coverage 패키지 없음"}
    except Exception as e:
        logger.error(f"커버리지 분석 중 오류: {e}")
        return {"error": str(e)}


def generate_test_report(results: Dict[str, Any]) -> str:
    """
    테스트 결과 보고서 생성
    
    Args:
        results: 테스트 결과 딕셔너리
    
    Returns:
        보고서 문자열
    """
    if "error" in results:
        return f"❌ 테스트 실행 오류: {results['error']}"
    
    report_lines = [
        "=" * 60,
        "🧪 AutoStockTrading 테스트 결과 보고서",
        "=" * 60,
        f"📅 실행 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"⏱️  총 소요 시간: {results.get('execution_time', 0):.2f}초",
        "",
        "📊 테스트 통계:",
        f"   총 테스트 수: {results.get('tests_run', 0)}",
        f"   성공: {results.get('tests_run', 0) - results.get('failures', 0) - results.get('errors', 0)}",
        f"   실패: {results.get('failures', 0)}",
        f"   오류: {results.get('errors', 0)}",
        f"   건너뜀: {results.get('skipped', 0)}",
        "",
        f"🎯 전체 성공 여부: {'✅ 성공' if results.get('success', False) else '❌ 실패'}",
        ""
    ]
    
    # 실패 및 오류 상세 정보
    if results.get('failures') or results.get('errors'):
        report_lines.extend([
            "🔍 실패/오류 상세:",
            ""
        ])
        
        for failure in results.get('failure_details', []):
            report_lines.extend([
                "❌ 실패:",
                failure,
                ""
            ])
        
        for error in results.get('error_details', []):
            report_lines.extend([
                "🚨 오류:",
                error,
                ""
            ])
    
    # 권장사항
    report_lines.extend([
        "💡 권장사항:",
        "   - 실패한 테스트는 즉시 수정하세요",
        "   - 새로운 기능 추가 시 테스트도 함께 작성하세요",
        "   - 테스트 커버리지를 90% 이상 유지하세요",
        "   - 정기적으로 전체 테스트를 실행하세요",
        "",
        "=" * 60
    ])
    
    return "\n".join(report_lines)


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoStockTrading 테스트 실행기")
    parser.add_argument("--file", "-f", help="특정 테스트 파일 실행 (예: test_constants.py)")
    parser.add_argument("--coverage", "-c", action="store_true", help="커버리지 분석 포함")
    parser.add_argument("--verbose", "-v", type=int, default=2, choices=[0, 1, 2], 
                       help="출력 상세도 (0: 최소, 1: 보통, 2: 상세)")
    parser.add_argument("--quick", "-q", action="store_true", help="빠른 실행 (상세도 1)")
    parser.add_argument("--report", "-r", help="보고서 저장 파일 경로")
    
    args = parser.parse_args()
    
    # 빠른 실행 모드
    if args.quick:
        args.verbose = 1
    
    logger.info("🚀 AutoStockTrading 테스트 실행기 시작")
    logger.info(f"프로젝트 루트: {PROJECT_ROOT}")
    
    # 로그 디렉토리 생성
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    
    try:
        if args.file:
            # 특정 파일 테스트
            results = run_specific_test_file(args.file, args.verbose)
        elif args.coverage:
            # 커버리지 분석 포함 테스트
            results = run_test_coverage_analysis()
            if "test_results" in results:
                results = results["test_results"]
        else:
            # 전체 테스트 실행
            results = discover_and_run_tests(verbosity=args.verbose)
        
        # 보고서 생성
        report = generate_test_report(results)
        print("\n" + report)
        
        # 보고서 저장
        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"📄 보고서 저장: {report_path}")
        
        # 종료 코드 설정
        exit_code = 0 if results.get('success', False) else 1
        
        if exit_code == 0:
            logger.info("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        else:
            logger.error("💥 일부 테스트가 실패했습니다. 코드를 검토해주세요.")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("🛑 사용자에 의해 테스트가 중단되었습니다.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"🚨 예상치 못한 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
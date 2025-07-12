"""
종목-업종 자동 매핑 유틸리티

기존 데이터베이스의 종목들에 업종 정보를 자동으로 매핑하는 도구입니다.
pykrx와 정적 매핑 테이블을 활용하여 업종 정보를 수집하고 저장합니다.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time

from src.api.sector_classifier import SectorClassifier
from src.utils.common import load_config
from src.data.database import DatabaseManager

logger = logging.getLogger(__name__)


class SectorMappingTool:
    """
    종목-업종 자동 매핑 도구

    주요 기능:
    1. 기존 DB의 종목들에 업종 정보 자동 매핑
    2. 대표 종목들의 업종 정보 수집
    3. 업종별 시가총액 상위 종목 선별
    4. 매핑 결과 검증 및 리포트
    """


def __init__(self, db_path: Optional[str] = None):
    if db_path is None:
        config = load_config()
        project_root = Path(config.get("paths", {}).get("project_root", "."))
        db_path = project_root / "data" / "trading.db"

    self.db_path = Path(db_path)
    self.classifier = SectorClassifier(str(db_path))

    # 대표 종목들의 업종 매핑 (실제 업종 정보)
    self.known_mappings = self._load_known_mappings()


def _load_known_mappings(self) -> Dict[str, Dict[str, str]]:
    """알려진 대표 종목들의 업종 매핑 정보"""
    return {
        # KOSPI 주요 종목들
        "005930": {
            "sector_code": "013",
            "name": "삼성전자",
            "market": "KOSPI",
        },  # 전기전자
        "000660": {
            "sector_code": "013",
            "name": "SK하이닉스",
            "market": "KOSPI",
        },  # 전기전자
        "035420": {
            "sector_code": "025",
            "name": "NAVER",
            "market": "KOSPI",
        },  # 서비스업
        "051910": {"sector_code": "008", "name": "LG화학", "market": "KOSPI"},  # 화학
        "028260": {
            "sector_code": "016",
            "name": "삼성물산",
            "market": "KOSPI",
        },  # 유통업
        "005380": {
            "sector_code": "015",
            "name": "현대차",
            "market": "KOSPI",
        },  # 운수장비
        "000270": {"sector_code": "015", "name": "기아", "market": "KOSPI"},  # 운수장비
        "068270": {
            "sector_code": "025",
            "name": "셀트리온",
            "market": "KOSPI",
        },  # 서비스업(바이오)
        "207940": {
            "sector_code": "013",
            "name": "삼성바이오로직스",
            "market": "KOSPI",
        },  # 전기전자
        "006400": {
            "sector_code": "013",
            "name": "삼성SDI",
            "market": "KOSPI",
        },  # 전기전자
        "012330": {
            "sector_code": "015",
            "name": "현대모비스",
            "market": "KOSPI",
        },  # 운수장비
        "030200": {"sector_code": "020", "name": "KT", "market": "KOSPI"},  # 통신업
        "017670": {
            "sector_code": "020",
            "name": "SK텔레콤",
            "market": "KOSPI",
        },  # 통신업
        "003550": {
            "sector_code": "020",
            "name": "LG유플러스",
            "market": "KOSPI",
        },  # 통신업
        "055550": {"sector_code": "022", "name": "신한지주", "market": "KOSPI"},  # 은행
        "105560": {"sector_code": "022", "name": "KB금융", "market": "KOSPI"},  # 은행
        "086790": {
            "sector_code": "022",
            "name": "하나금융지주",
            "market": "KOSPI",
        },  # 은행
        "032830": {"sector_code": "023", "name": "삼성생명", "market": "KOSPI"},  # 증권
        "018260": {
            "sector_code": "018",
            "name": "삼성에스디에스",
            "market": "KOSPI",
        },  # 건설업
        "090430": {
            "sector_code": "008",
            "name": "아모레퍼시픽",
            "market": "KOSPI",
        },  # 화학
        # KOSDAQ 주요 종목들
        "035720": {"sector_code": "107", "name": "카카오", "market": "KOSDAQ"},  # IT
        "066570": {"sector_code": "107", "name": "LG전자", "market": "KOSDAQ"},  # IT
        "096770": {
            "sector_code": "107",
            "name": "SK이노베이션",
            "market": "KOSDAQ",
        },  # IT
        "251270": {
            "sector_code": "108",
            "name": "넷마블",
            "market": "KOSDAQ",
        },  # 생명과학
        "247540": {
            "sector_code": "110",
            "name": "에코프로비엠",
            "market": "KOSDAQ",
        },  # 콘텐츠
        "058470": {
            "sector_code": "105",
            "name": "리노공업",
            "market": "KOSDAQ",
        },  # 소재
        "240810": {
            "sector_code": "106",
            "name": "원익IPS",
            "market": "KOSDAQ",
        },  # 부품장비
    }


def get_stocks_without_sector(self) -> List[Tuple[str, str]]:
    """
    업종 정보가 없는 종목들 조회

    Returns:
        (symbol, name) 튜플 리스트
    """
    try:
        with sqlite3.connect(self.db_path) as conn:
            # stock_data 테이블에는 있지만 stock_sectors에는 없는 종목들
            query = """
                    SELECT DISTINCT sd.symbol, 
                           COALESCE(s.name, sd.symbol) as name
                    FROM stock_data sd
                    LEFT JOIN stock_sectors ss ON sd.symbol = ss.symbol
                    LEFT JOIN (
                        SELECT symbol, 
                               FIRST_VALUE(symbol) OVER (PARTITION BY symbol ORDER BY date DESC) as name
                        FROM stock_data
                    ) s ON sd.symbol = s.symbol
                    WHERE ss.symbol IS NULL
                    ORDER BY sd.symbol
                """

            rows = conn.execute(query).fetchall()
            return [(row[0], row[1]) for row in rows]

    except Exception as e:
        logger.error(f"업종 미매핑 종목 조회 실패: {e}")
        return []


def map_known_stocks(self) -> Dict[str, str]:
    """
    알려진 대표 종목들의 업종 정보 매핑

    Returns:
        매핑 결과 딕셔너리
    """
    results = {}

    for symbol, info in self.known_mappings.items():
        try:
            self.classifier.add_stock_sector_mapping(
                symbol=symbol,
                name=info["name"],
                sector_code=info["sector_code"],
                market=info["market"],
            )
            results[symbol] = f"✅ {info['name']} -> {info['sector_code']}"
            logger.info(
                f"종목 매핑 완료: {symbol} ({info['name']}) -> {info['sector_code']}"
            )

        except Exception as e:
            results[symbol] = f"❌ 매핑 실패: {e}"
            logger.error(f"종목 매핑 실패 ({symbol}): {e}")

    return results


def auto_map_by_name(self, symbols: List[str]) -> Dict[str, str]:
    """
    종목명 기반 자동 업종 매핑

    Args:
        symbols: 매핑할 종목 코드 리스트

    Returns:
        매핑 결과 딕셔너리
    """
    results = {}

    for symbol in symbols:
        try:
            # 종목명 조회
            with sqlite3.connect(self.db_path) as conn:
                dm = DatabaseManager(db_path=self.db_path)
                name_query = """
                        SELECT DISTINCT name 
                        FROM stock_info 
                        WHERE symbol = ? 
                        LIMIT 1
                    """
                df_name = dm.fetchdf(name_query, params=(symbol,))

                if df_name.empty:
                    results[symbol] = "❌ 종목 정보 없음"
                    continue

                name = df_name.iloc[0]["name"]

            # 업종 추정
            estimated_sector = self.classifier.classify_symbol_by_name(symbol, name)

            # 시장 구분 (간단한 규칙)
            market = "KOSPI" if symbol.startswith(("0", "1", "2", "3")) else "KOSDAQ"

            # 매핑 저장
            self.classifier.add_stock_sector_mapping(
                symbol=symbol, name=name, sector_code=estimated_sector, market=market
            )

            results[symbol] = f"✅ {name} -> {estimated_sector} (추정)"
            logger.info(f"자동 매핑 완료: {symbol} -> {estimated_sector}")

        except Exception as e:
            results[symbol] = f"❌ 자동 매핑 실패: {e}"
            logger.error(f"자동 매핑 실패 ({symbol}): {e}")

    return results


def run_full_mapping(self, max_auto_map: int = 999999) -> Dict[str, any]:
    """
    전체 종목 업종 매핑 실행

    Args:
        max_auto_map: 자동 매핑할 최대 종목 수

    Returns:
        매핑 결과 리포트
    """
    logger.info("🚀 종목-업종 전체 매핑 시작...")

    # 1. 알려진 종목들 매핑
    logger.info("1️⃣ 대표 종목들 매핑 중...")
    known_results = self.map_known_stocks()

    # 2. 업종 미매핑 종목들 조회
    logger.info("2️⃣ 업종 미매핑 종목들 조회 중...")
    unmapped_stocks = self.get_stocks_without_sector()

    # 3. 자동 매핑 (제한된 수량)
    logger.info(f"3️⃣ 자동 매핑 실행 중... (최대 {max_auto_map}개)")
    auto_map_symbols = [stock[0] for stock in unmapped_stocks[:max_auto_map]]
    auto_results = self.auto_map_by_name(auto_map_symbols)

    # 4. 결과 리포트 생성
    report = {
        "execution_time": datetime.now().isoformat(),
        "known_mappings": {
            "total": len(known_results),
            "success": len([r for r in known_results.values() if r.startswith("✅")]),
            "failed": len([r for r in known_results.values() if r.startswith("❌")]),
            "details": known_results,
        },
        "auto_mappings": {
            "total": len(auto_results),
            "success": len([r for r in auto_results.values() if r.startswith("✅")]),
            "failed": len([r for r in auto_results.values() if r.startswith("❌")]),
            "details": auto_results,
        },
        "remaining_unmapped": len(unmapped_stocks) - len(auto_map_symbols),
        "summary": {
            "total_processed": len(known_results) + len(auto_results),
            "total_success": len(
                [r for r in known_results.values() if r.startswith("✅")]
            )
            + len([r for r in auto_results.values() if r.startswith("✅")]),
            "remaining_work": max(0, len(unmapped_stocks) - len(auto_map_symbols)),
        },
    }

    # 로그 출력
    logger.info("=" * 60)
    logger.info("📊 종목-업종 매핑 완료!")
    logger.info("=" * 60)
    logger.info(
        f"✅ 대표 종목 매핑: {report['known_mappings']['success']}/{report['known_mappings']['total']}"
    )
    logger.info(
        f"🤖 자동 매핑: {report['auto_mappings']['success']}/{report['auto_mappings']['total']}"
    )
    logger.info(
        f"📋 총 처리: {report['summary']['total_success']}/{report['summary']['total_processed']}"
    )
    logger.info(f"⏳ 남은 작업: {report['summary']['remaining_work']}개 종목")

    return report


def get_sector_distribution(self) -> Dict[str, any]:
    """
    현재 업종 분포 현황 조회

    Returns:
        업종별 종목 수 분포
    """
    try:
        with sqlite3.connect(self.db_path) as conn:
            query = """
                    SELECT s.name as sector_name, s.market, s.group_name,
                           COUNT(ss.symbol) as stock_count
                    FROM sectors s
                    LEFT JOIN stock_sectors ss ON s.code = ss.sector_code
                    GROUP BY s.code, s.name, s.market, s.group_name
                    ORDER BY s.market, stock_count DESC
                """

            rows = conn.execute(query).fetchall()

            distribution = {}
            total_mapped = 0

            for row in rows:
                sector_name, market, group, count = row

                if market not in distribution:
                    distribution[market] = {}

                if group not in distribution[market]:
                    distribution[market][group] = {}

                distribution[market][group][sector_name] = count
                total_mapped += count

            return {
                "distribution": distribution,
                "total_mapped_stocks": total_mapped,
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.error(f"업종 분포 조회 실패: {e}")
        return {}


def export_optimization_groups(self, output_file: Optional[str] = None) -> str:
    """
    최적화용 업종별 종목 그룹을 JSON 파일로 내보내기

    Args:
        output_file: 출력 파일 경로

    Returns:
        생성된 파일 경로
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"optimization_groups_{timestamp}.json"

    try:
        import json

        # KOSPI, KOSDAQ 각각의 그룹 생성
        kospi_groups = self.classifier.get_sector_groups_for_optimization("KOSPI")
        kosdaq_groups = self.classifier.get_sector_groups_for_optimization("KOSDAQ")

        export_data = {
            "generation_time": datetime.now().isoformat(),
            "description": "매개변수 최적화용 업종별 종목 그룹",
            "markets": {"KOSPI": kospi_groups, "KOSDAQ": kosdaq_groups},
            "usage_example": {
                "description": "업종별 최적화 실행 방법",
                "code": """
# 제조업 종목들로 최적화
manufacturing_stocks = groups['KOSPI']['제조업']['화학'] + groups['KOSPI']['제조업']['전기전자']
results = run_optimization('MACD', 'sharpe_ratio', manufacturing_stocks)

# 금융업 종목들로 최적화  
financial_stocks = groups['KOSPI']['금융']['은행'] + groups['KOSPI']['금융']['증권']
results = run_optimization('RSI', 'total_return', financial_stocks)
                    """,
            },
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info(f"최적화 그룹 파일 생성 완료: {output_file}")
        return output_file

    except Exception as e:
        logger.error(f"최적화 그룹 내보내기 실패: {e}")
        return ""


def run_sector_mapping_cli():
    """CLI에서 실행할 수 있는 메인 함수"""
    print("🏗️  종목-업종 자동 매핑 도구")
    print("=" * 50)

    tool = SectorMappingTool()

    # 현재 상태 확인
    print("📊 현재 업종 분포 현황:")
    distribution = tool.get_sector_distribution()
    if distribution:
        print(f"   총 매핑된 종목: {distribution['total_mapped_stocks']}개")

        for market, groups in distribution["distribution"].items():
            print(f"\n   📈 {market}:")
            for group, sectors in groups.items():
                group_total = sum(sectors.values())
                if group_total > 0:
                    print(f"     • {group}: {group_total}개")

    print("\n" + "=" * 50)

    # 전체 매핑 실행
    print("🚀 전체 매핑 실행...")
    report = tool.run_full_mapping(max_auto_map=30)

    # 최적화 그룹 내보내기
    print("\n📁 최적화 그룹 파일 생성...")
    output_file = tool.export_optimization_groups()

    if output_file:
        print(f"   ✅ 파일 생성: {output_file}")
        print(f"   💡 사용법: optimization UI에서 업종별 종목 선택 시 활용")

    print("\n✨ 작업 완료!")


if __name__ == "__main__":
    run_sector_mapping_cli()

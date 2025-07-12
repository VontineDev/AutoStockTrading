#!/usr/bin/env python3
"""
Legacy Data Status Checker - 레거시 데이터 상태 확인 도구

⚠️  이 파일은 main.py에 통합되었습니다!
    이제 scripts/check_data_status_legacy.py 위치에서 마이그레이션 도구로만 사용됩니다.

🔄 마이그레이션 안내:
   이 스크립트는 곧 제거될 예정입니다. 새로운 통합 명령어를 사용하세요.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

# 프로젝트 루트로 경로 설정
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("🔄 이 스크립트는 main.py에 통합되었습니다!")
print("📁 위치가 변경되었습니다: scripts/check_data_status_legacy.py")
print("")
print("새로운 통합 명령어를 사용하세요:")
print("")
print("📊 종합 데이터 상태 확인:")
print("   python src/main.py check-data")
print("")
print("📈 상세 백테스팅 분석:")
print("   python src/main.py update-data --summary --backtest-analysis")
print("")
print("⚡ 빠른 기본 현황:")
print("   python src/main.py update-data --summary")
print("")
print("🔧 사용자 정의 분석:")
print("   python src/main.py check-data --days-back 90 --min-days 45")
print("")
print("=" * 60)
print("기존 기능을 한 번만 더 실행합니다... (곧 제거될 예정)")
print("=" * 60)
print("")

# 데이터베이스 경로 수정 (프로젝트 루트 기준)
db_path = os.path.join(project_root, "data", "trading.db")

if not os.path.exists(db_path):
    print("❌ 데이터베이스를 찾을 수 없습니다!")
    print(f"   경로: {db_path}")
    print("")
    print("다음 명령어로 데이터를 먼저 수집하세요:")
    print("   python src/main.py update-data --top-kospi 50 --period 6m")
    print("")
    print("=" * 60)
    print("⚠️  앞으로는 다음 명령어를 사용하세요:")
    print("   python src/main.py check-data")
    print("=" * 60)
    sys.exit(1)

# 데이터베이스 연결
conn = sqlite3.connect(db_path)

try:
    # 총 종목 수 확인
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM stock_data")
    total_symbols = cursor.fetchone()[0]
    print(f"📊 총 종목 수: {total_symbols:,}개")

    # 최근 60일 데이터가 있는 종목 확인
    recent_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    cursor.execute(
        """
        SELECT symbol, COUNT(*) as days, MIN(date) as start_date, MAX(date) as end_date
        FROM stock_data 
        WHERE date >= ?
        GROUP BY symbol
        HAVING COUNT(*) >= 30
        ORDER BY days DESC
        LIMIT 20
    """,
        (recent_date,),
    )

    print(f"\n📈 최근 60일간 30일 이상 데이터가 있는 상위 20개 종목:")
    valid_symbols = []
    for row in cursor.fetchall():
        symbol, days, start_date, end_date = row
        print(f"{symbol}: {days}일 ({start_date} ~ {end_date})")
        valid_symbols.append(symbol)

    # 전체 유효 종목 수 확인
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT symbol
            FROM stock_data 
            WHERE date >= ?
            GROUP BY symbol
            HAVING COUNT(*) >= 30
        ) as valid_symbols
    """,
        (recent_date,),
    )

    valid_count = cursor.fetchone()[0]
    print(f"\n✅ 백테스팅 가능 종목 수 (최근 60일 중 30일 이상): {valid_count:,}개")

    # 유효한 종목들 일부 반환
    print(f"\n🎯 테스트용 종목 리스트 (상위 10개):")
    print(",".join(valid_symbols[:10]))

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    print("")
    print("새로운 통합 명령어를 사용하세요:")
    print("   python src/main.py check-data")

finally:
    conn.close()

print("\n" + "=" * 60)
print("⚠️  이 스크립트는 곧 제거됩니다!")
print("앞으로는 다음 명령어를 사용하세요:")
print("   python src/main.py check-data")
print("=" * 60)
print("")
print("💡 새로운 기능들:")
print("   • 종합 데이터 분석")
print("   • 백테스팅 적합성 평가")
print("   • 맞춤형 권장사항")
print("   • 사용자 정의 분석 조건")
print("=" * 60)

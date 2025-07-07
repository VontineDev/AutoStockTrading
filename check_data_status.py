import sqlite3
import pandas as pd
from datetime import datetime, timedelta

print("🔄 이 스크립트는 main.py에 통합되었습니다!")
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

# 데이터베이스 연결
conn = sqlite3.connect('data/trading.db')

# 총 종목 수 확인
cursor = conn.cursor()
cursor.execute('SELECT COUNT(DISTINCT symbol) FROM stock_data')
total_symbols = cursor.fetchone()[0]
print(f'📊 총 종목 수: {total_symbols:,}개')

# 최근 60일 데이터가 있는 종목 확인
recent_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
cursor.execute('''
    SELECT symbol, COUNT(*) as days, MIN(date) as start_date, MAX(date) as end_date
    FROM stock_data 
    WHERE date >= ?
    GROUP BY symbol
    HAVING COUNT(*) >= 30
    ORDER BY days DESC
    LIMIT 20
''', (recent_date,))

print(f'\n📈 최근 60일간 30일 이상 데이터가 있는 상위 20개 종목:')
valid_symbols = []
for row in cursor.fetchall():
    symbol, days, start_date, end_date = row
    print(f'{symbol}: {days}일 ({start_date} ~ {end_date})')
    valid_symbols.append(symbol)

# 전체 유효 종목 수 확인
cursor.execute('''
    SELECT COUNT(DISTINCT symbol)
    FROM stock_data 
    WHERE date >= ?
    GROUP BY symbol
    HAVING COUNT(*) >= 30
''', (recent_date,))

cursor.execute('''
    SELECT COUNT(*)
    FROM (
        SELECT symbol
        FROM stock_data 
        WHERE date >= ?
        GROUP BY symbol
        HAVING COUNT(*) >= 30
    ) as valid_symbols
''', (recent_date,))

valid_count = cursor.fetchone()[0]
print(f'\n✅ 백테스팅 가능 종목 수 (최근 60일 중 30일 이상): {valid_count:,}개')

conn.close()

# 유효한 종목들 일부 반환
print(f'\n🎯 테스트용 종목 리스트 (상위 10개):')
print(','.join(valid_symbols[:10]))

print("\n" + "=" * 60)
print("⚠️  앞으로는 다음 명령어를 사용하세요:")
print("   python src/main.py check-data")
print("=" * 60) 
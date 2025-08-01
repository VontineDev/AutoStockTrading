#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선된 증분 업데이트 로직 사용 예시

이 스크립트는 개선된 증분 업데이트 기능을 사용하여
주식 데이터를 안전하고 효율적으로 업데이트하는 방법을 보여줍니다.
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.updater import StockDataUpdater, OptimizedDataUpdateConfig


def main():
    """증분 업데이트 예시 실행"""
    
    print("🚀 개선된 증분 업데이트 로직 테스트 시작")
    print("=" * 50)
    
    # 1. 설정 초기화
    print("\n1️⃣ 설정 초기화...")
    config = OptimizedDataUpdateConfig(
        incremental_update=True,      # 증분 업데이트 활성화
        skip_existing=True,           # 기존 데이터 건너뛰기
        force_update_days=3,          # 3일 이상 된 데이터는 강제 업데이트
        max_workers=4,                # 병렬 처리 워커 수
        api_delay=0.3,                # API 호출 간격
        enable_cache=True,            # 캐시 활성화
        cache_expiry_hours=6          # 캐시 만료 시간
    )
    
    # 2. 업데이터 초기화
    print("2️⃣ 업데이터 초기화...")
    updater = StockDataUpdater(optimization_config=config)
    
    # 3. 테스트 종목 설정
    test_symbols = [
        "005930",  # 삼성전자
        "000660",  # SK하이닉스
        "035420",  # NAVER
        "051910",  # LG화학
        "006400"   # 삼성SDI
    ]
    
    # 4. 날짜 범위 설정 (최근 30일)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"📅 업데이트 기간: {start_date} ~ {end_date}")
    print(f"📊 대상 종목: {', '.join(test_symbols)}")
    
    # 5. 데이터 일관성 검사
    print("\n3️⃣ 데이터 일관성 검사...")
    consistency_stats = updater.get_incremental_update_stats(test_symbols, start_date, end_date)
    
    print(f"   - 전체 종목 수: {consistency_stats['total_symbols']}")
    print(f"   - 누락 데이터가 있는 종목: {consistency_stats['symbols_with_missing_data']}")
    print(f"   - 품질 이슈가 있는 종목: {consistency_stats['symbols_with_quality_issues']}")
    print(f"   - 총 누락 일수: {consistency_stats['total_missing_days']}")
    
    # 6. 개별 종목 상세 분석
    print("\n4️⃣ 개별 종목 상세 분석...")
    for symbol in test_symbols:
        consistency = updater.check_data_consistency(symbol, start_date, end_date)
        status = "✅ 일관" if consistency.get("is_consistent") else "❌ 불일관"
        print(f"   {symbol}: {status}")
        
        if not consistency.get("is_consistent"):
            missing_days = consistency.get("missing_days", 0)
            quality_issues = consistency.get("data_quality_issues", [])
            
            if missing_days > 0:
                print(f"     - 누락 일수: {missing_days}")
            if quality_issues:
                print(f"     - 품질 이슈: {', '.join(quality_issues)}")
    
    # 7. 안전한 증분 업데이트 실행
    print("\n5️⃣ 안전한 증분 업데이트 실행...")
    print("   (백업 생성 후 업데이트 진행)")
    
    try:
        result = updater.safe_incremental_update(
            symbols=test_symbols,
            start_date=start_date,
            end_date=end_date,
            create_backup=True,        # 백업 생성
            strategy="auto"            # 자동 전략 선택
        )
        
        if result["success"]:
            print("✅ 업데이트 성공!")
            
            # 개선 결과 출력
            improvement = result["improvement"]
            print(f"\n📈 개선 결과:")
            print(f"   - 수정된 종목 수: {improvement['symbols_fixed']}")
            print(f"   - 감소한 누락 일수: {improvement['missing_days_reduced']}")
            print(f"   - 해결된 품질 이슈: {improvement['quality_issues_fixed']}")
            
            # 백업 정보
            if result.get("backup_path"):
                print(f"   - 백업 파일: {result['backup_path']}")
        
        else:
            print("❌ 업데이트 실패!")
            print(f"   오류: {result.get('error', 'Unknown error')}")
            
            if result.get("restore_success"):
                print("   ✅ 백업에서 복원 성공")
            else:
                print("   ❌ 백업 복원 실패")
    
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
    
    # 8. 최종 검증
    print("\n6️⃣ 최종 검증...")
    final_stats = updater.get_incremental_update_stats(test_symbols, start_date, end_date)
    
    print(f"   - 누락 데이터가 있는 종목: {final_stats['symbols_with_missing_data']}")
    print(f"   - 품질 이슈가 있는 종목: {final_stats['symbols_with_quality_issues']}")
    print(f"   - 총 누락 일수: {final_stats['total_missing_days']}")
    
    # 9. 성능 통계
    print("\n7️⃣ 성능 통계...")
    perf_stats = updater.get_optimization_stats()
    
    print(f"   - 캐시 히트: {perf_stats.get('cache_hits', 0)}")
    print(f"   - 캐시 미스: {perf_stats.get('cache_misses', 0)}")
    print(f"   - 증분 업데이트: {perf_stats.get('incremental_updates', 0)}")
    print(f"   - 전체 업데이트: {perf_stats.get('full_updates', 0)}")
    
    print("\n🎉 증분 업데이트 테스트 완료!")


def demonstrate_different_strategies():
    """다양한 업데이트 전략 시연"""
    
    print("\n" + "=" * 50)
    print("🔄 다양한 업데이트 전략 시연")
    print("=" * 50)
    
    config = OptimizedDataUpdateConfig(incremental_update=True)
    updater = StockDataUpdater(optimization_config=config)
    
    test_symbols = ["005930", "000660", "035420"]
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    strategies = ["conservative", "auto", "aggressive"]
    
    for strategy in strategies:
        print(f"\n📋 전략: {strategy.upper()}")
        print("-" * 30)
        
        try:
            result = updater.smart_incremental_update(
                symbols=test_symbols,
                start_date=start_date,
                end_date=end_date,
                strategy=strategy
            )
            
            plan = result["update_plan"]
            print(f"   - 고우선순위: {len(plan['high_priority'])}개")
            print(f"   - 중우선순위: {len(plan['medium_priority'])}개")
            print(f"   - 저우선순위: {len(plan['low_priority'])}개")
            print(f"   - 건너뛴 종목: {len(plan['skip_symbols'])}개")
            
        except Exception as e:
            print(f"   ❌ 오류: {e}")


if __name__ == "__main__":
    main()
    demonstrate_different_strategies() 
"""
업종 분류 API 테스트 스크립트

새로 구현한 업종 분류 API와 매핑 도구의 기본 기능을 테스트합니다.
"""

import sys
import logging
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.api.sector_classifier import (
    SectorClassifier, 
    get_all_sectors_api, 
    get_stocks_by_sector_api,
    get_optimization_groups_api,
    get_stock_sector_api
)
from src.utils.sector_mapping_tool import SectorMappingTool

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_sector_classifier():
    """SectorClassifier 기본 기능 테스트"""
    print("🧪 SectorClassifier 테스트 시작...")
    
    try:
        classifier = SectorClassifier()
        
        # 1. 전체 업종 조회
        print("\n1️⃣ 전체 업종 조회:")
        sectors = classifier.get_all_sectors()
        print(f"   총 {len(sectors)}개 업종")
        
        for market in ["KOSPI", "KOSDAQ"]:
            market_sectors = [s for s in sectors if s.market == market]
            print(f"   {market}: {len(market_sectors)}개")
            
            # 각 시장의 첫 3개 업종 표시
            for sector in market_sectors[:3]:
                print(f"     • {sector.code}: {sector.name} ({sector.group})")
        
        # 2. 특정 업종의 종목 조회 (화학업)
        print("\n2️⃣ 화학업(008) 종목 조회:")
        chemical_stocks = classifier.get_stocks_by_sector("008", limit=5)
        
        if chemical_stocks:
            for stock in chemical_stocks:
                print(f"   • {stock.symbol}: {stock.name} ({stock.market})")
        else:
            print("   화학업 종목이 없습니다. (매핑 필요)")
        
        # 3. 최적화용 그룹 조회
        print("\n3️⃣ 최적화용 업종 그룹:")
        groups = classifier.get_sector_groups_for_optimization("KOSPI")
        
        if groups:
            for group_name, sectors in list(groups.items())[:2]:  # 첫 2개 그룹만
                print(f"   📂 {group_name}:")
                for sector_name, stocks in list(sectors.items())[:2]:  # 각 그룹의 첫 2개 업종
                    print(f"     • {sector_name}: {len(stocks)}개 종목")
        else:
            print("   업종 그룹이 없습니다. (매핑 필요)")
        
        print("✅ SectorClassifier 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ SectorClassifier 테스트 실패: {e}")
        return False

def test_api_functions():
    """API 함수들 테스트"""
    print("\n🌐 API 함수 테스트 시작...")
    
    try:
        # 1. 전체 업종 API
        print("\n1️⃣ get_all_sectors_api:")
        result = get_all_sectors_api("KOSPI")
        print(f"   상태: {result['status']}")
        print(f"   KOSPI 업종 수: {result['total']}")
        
        # 2. 업종별 종목 API  
        print("\n2️⃣ get_stocks_by_sector_api:")
        result = get_stocks_by_sector_api("013", limit=3)  # 전기전자
        print(f"   상태: {result['status']}")
        print(f"   전기전자(013) 종목 수: {result['total']}")
        
        if result['total'] > 0:
            for stock in result['data'][:3]:
                print(f"     • {stock['symbol']}: {stock['name']}")
        
        # 3. 최적화 그룹 API
        print("\n3️⃣ get_optimization_groups_api:")
        result = get_optimization_groups_api("KOSPI")
        print(f"   상태: {result['status']}")
        print(f"   KOSPI 업종 그룹 수: {result['total_groups']}")
        
        # 4. 종목 업종 조회 API
        print("\n4️⃣ get_stock_sector_api:")
        result = get_stock_sector_api("005930")  # 삼성전자
        print(f"   상태: {result['status']}")
        
        if result['status'] == 'success':
            data = result['data']
            print(f"   삼성전자: {data['sector_name']} ({data['sector_code']})")
        
        print("✅ API 함수 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ API 함수 테스트 실패: {e}")
        return False

def test_mapping_tool():
    """매핑 도구 테스트"""
    print("\n🔧 매핑 도구 테스트 시작...")
    
    try:
        tool = SectorMappingTool()
        
        # 1. 현재 업종 분포 확인
        print("\n1️⃣ 현재 업종 분포:")
        distribution = tool.get_sector_distribution()
        
        if distribution:
            print(f"   총 매핑된 종목: {distribution['total_mapped_stocks']}개")
            
            for market, groups in distribution['distribution'].items():
                total_in_market = sum(
                    sum(sectors.values()) for sectors in groups.values()
                )
                if total_in_market > 0:
                    print(f"   {market}: {total_in_market}개")
        
        # 2. 미매핑 종목 조회
        print("\n2️⃣ 업종 미매핑 종목:")
        unmapped = tool.get_stocks_without_sector()
        print(f"   미매핑 종목: {len(unmapped)}개")
        
        if unmapped:
            for symbol, name in unmapped[:5]:  # 첫 5개만 표시
                print(f"     • {symbol}: {name}")
            if len(unmapped) > 5:
                print(f"     ... 외 {len(unmapped) - 5}개")
        
        # 3. 대표 종목 매핑 테스트 (실제 실행하지 않고 시뮬레이션)
        print("\n3️⃣ 대표 종목 매핑 시뮬레이션:")
        known_mappings = tool.known_mappings
        print(f"   매핑할 대표 종목: {len(known_mappings)}개")
        
        for symbol, info in list(known_mappings.items())[:3]:  # 첫 3개만
            print(f"     • {symbol}: {info['name']} -> {info['sector_code']}")
        
        print("✅ 매핑 도구 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 매핑 도구 테스트 실패: {e}")
        return False

def run_sample_mapping():
    """샘플 매핑 실행"""
    print("\n🚀 샘플 매핑 실행...")
    
    try:
        tool = SectorMappingTool()
        
        # 대표 종목 몇 개만 매핑 (전체가 아닌 테스트용)
        test_symbols = ["005930", "000660", "035420"]  # 삼성전자, SK하이닉스, NAVER
        
        print("매핑할 테스트 종목들:")
        for symbol in test_symbols:
            if symbol in tool.known_mappings:
                info = tool.known_mappings[symbol]
                print(f"  • {symbol}: {info['name']} -> {info['sector_code']} ({info['market']})")
                
                # 실제 매핑 수행
                tool.classifier.add_stock_sector_mapping(
                    symbol=symbol,
                    name=info["name"],
                    sector_code=info["sector_code"],
                    market=info["market"]
                )
        
        print("✅ 샘플 매핑 완료")
        
        # 매핑 결과 확인
        print("\n매핑 결과 확인:")
        for symbol in test_symbols:
            stock_info = tool.classifier.get_stock_sector(symbol)
            if stock_info:
                print(f"  • {symbol}: {stock_info.sector_name} ({stock_info.sector_code})")
            else:
                print(f"  • {symbol}: 매핑 실패")
        
        return True
        
    except Exception as e:
        print(f"❌ 샘플 매핑 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🎯 업종 분류 API 테스트 시작")
    print("=" * 50)
    
    # 각 테스트 실행
    tests = [
        ("SectorClassifier 기본 기능", test_sector_classifier),
        ("API 함수들", test_api_functions),
        ("매핑 도구", test_mapping_tool),
        ("샘플 매핑", run_sample_mapping),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 통과")
            else:
                print(f"❌ {test_name} 실패")
        except Exception as e:
            print(f"❌ {test_name} 예외 발생: {e}")
    
    # 최종 결과
    print("\n" + "=" * 50)
    print(f"🏁 테스트 완료: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트가 성공했습니다!")
        print("\n💡 다음 단계:")
        print("1. Streamlit UI에서 '업종별 선택' 기능 테스트")
        print("2. 실제 매개변수 최적화 실행")
        print("3. 업종별 성과 비교 분석")
    else:
        print("⚠️  일부 테스트가 실패했습니다. 로그를 확인해주세요.")

if __name__ == "__main__":
    main() 
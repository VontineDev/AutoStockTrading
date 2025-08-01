"""
개선된 아키텍처 기반 스윙 트레이딩 시스템 메인 앱

계층화된 구조:
- UI 서비스 계층 (데이터, 전략, 백테스트, 포트폴리오)
- UI 컴포넌트 계층 (차트, 위젯, 테이블, 폼)
- 페이지 계층 (대시보드, 백테스트, 분석 등)
"""

import streamlit as st
import sys
import os
from pathlib import Path
import logging

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 페이지 설정
st.set_page_config(
    page_title="TA-Lib 스윙 트레이딩 시스템",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_custom_css():
    """커스텀 CSS 스타일 로드"""
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #1f4e79;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    .sidebar-info {
        background: #f0f8ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f4e79;
        margin-bottom: 1rem;
    }
    
    .success-box {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #ffeaa7;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

def render_navigation():
    """네비게이션 메뉴 렌더링"""
    
    # 사이드바에 네비게이션 메뉴
    with st.sidebar:
        st.markdown('<div class="sidebar-info">', unsafe_allow_html=True)
        st.markdown("""
        ### 📊 스윙 트레이딩 시스템
        **100만원 규모 최적화**
        
        - TA-Lib 기반 기술적 분석
        - pykrx 데이터 수집
        - 실시간 백테스팅
        - 리스크 관리 시스템
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 페이지 선택
        page_names = {
            "🏠 홈": "home",
            "📈 대시보드": "dashboard", 
            "🧪 백테스트": "backtest",
            "📊 데이터 관리": "data_management",
            "⚙️ 설정": "settings"
        }
        
        selected_page = st.selectbox(
            "페이지 선택",
            options=list(page_names.keys()),
            key="page_selector"
        )
        
        return page_names[selected_page]

def render_home_page():
    """홈 페이지 렌더링"""
    
    # 메인 헤더
    st.markdown('<h1 class="main-header">📈 TA-Lib 스윙 트레이딩 시스템</h1>', 
                unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 시스템 소개
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🎯 시스템 특징
        - **100만원 규모 최적화**
        - **TA-Lib 기반 분석**
        - **스윙 트레이딩 전문**
        - **리스크 관리 시스템**
        """)
    
    with col2:
        st.markdown("""
        ### 🔧 기술 스택
        - **Python 3.13**
        - **TA-Lib (기술적 지표)**
        - **pykrx (데이터 수집)**
        - **Streamlit (웹 인터페이스)**
        """)
    
    with col3:
        st.markdown("""
        ### 📊 주요 기능
        - **실시간 차트 분석**
        - **전략 백테스팅**
        - **포트폴리오 관리**
        - **성과 분석 리포트**
        """)
    
    st.markdown("---")
    
    # 시작하기 가이드
    st.header("🚀 시작하기")
    
    guide_tabs = st.tabs(["1️⃣ 데이터 준비", "2️⃣ 전략 선택", "3️⃣ 백테스트", "4️⃣ 실제 투자"])
    
    with guide_tabs[0]:
        st.markdown("""
        ### 데이터 준비
        1. **종목 선택**: 시가총액 상위 종목 또는 관심 종목
        2. **데이터 수집**: pykrx를 통한 자동 수집
        3. **지표 계산**: TA-Lib 기반 기술적 지표
        4. **데이터 검증**: 품질 확인 및 오류 제거
        """)
    
    with guide_tabs[1]:
        st.markdown("""
        ### 전략 선택
        1. **MACD 전략**: 추세 추종형, 중간 리스크
        2. **RSI 전략**: 역추세형, 횡보장에 적합
        3. **볼린저 밴드**: 변동성 기반, 다양한 시장
        4. **이동평균**: 단순하고 안정적, 초보자 추천
        """)
    
    with guide_tabs[2]:
        st.markdown("""
        ### 백테스트 실행
        1. **전략 및 매개변수 설정**
        2. **포트폴리오 규칙 설정** (자본, 리스크 등)
        3. **백테스트 기간 선택** (최소 6개월 권장)
        4. **결과 분석** (수익률, 샤프 비율, MDD 등)
        """)
    
    with guide_tabs[3]:
        st.markdown("""
        ### 실제 투자 (주의사항)
        1. **소액 테스트**: 실제 자금의 10% 이하로 시작
        2. **지속적 모니터링**: 시장 상황 변화 관찰
        3. **리스크 관리**: 손절매 규칙 준수
        4. **성과 평가**: 정기적인 전략 검토
        """)
    
    # 시스템 상태
    st.header("📊 시스템 상태")
    
    try:
        from src.ui.services.data_service import get_data_service
        data_service = get_data_service()
        
        # 데이터 현황 조회
        data_summary = data_service.get_data_summary()
        
        if not data_summary.empty:
            st.success(f"✅ 데이터베이스 연결됨 - {len(data_summary)}개 종목 데이터 확인")
            
            # 상위 5개 종목 표시
            top_5 = data_summary.head()
            st.dataframe(top_5, use_container_width=True)
        else:
            st.warning("⚠️ 데이터가 없습니다. 데이터 관리 페이지에서 데이터를 수집해주세요.")
            
    except Exception as e:
        st.error(f"❌ 시스템 연결 실패: {e}")
    
    # 리스크 고지
    st.markdown("---")
    st.markdown("""
    ### ⚠️ 투자 위험 고지
    
    - 본 시스템은 **교육 및 연구 목적**으로 제작되었습니다
    - **모든 투자 결정은 개인의 책임**이며, 손실 위험이 있습니다
    - **백테스트 결과는 미래 성과를 보장하지 않습니다**
    - **실제 투자 전 충분한 검토와 학습**을 권장합니다
    - **100만원 이하 소액으로 시작**하여 경험을 쌓으시기 바랍니다
    """)

def render_data_management_page():
    """데이터 관리 페이지"""
    
    st.title("📊 데이터 관리")
    st.markdown("---")
    
    try:
        from src.ui.services.data_service import get_data_service
        from src.ui.components.widgets import WidgetComponent
        from src.ui.components.tables import TableComponent
        from src.ui.components.forms import FormComponent
        
        data_service = get_data_service()
        
        # 데이터 현황
        st.header("📈 현재 데이터 현황")
        data_summary = data_service.get_data_summary()
        
        if not data_summary.empty:
            TableComponent.render_dataframe(
                data=data_summary,
                title="종목별 데이터 현황",
                height=400
            )
        else:
            st.warning("데이터가 없습니다.")
        
        st.markdown("---")
        
        # 종목 추가
        st.header("➕ 새 종목 추가")
        
        form_data = FormComponent.render_add_stock_form(key="add_new_stock")
        
        if form_data['submitted'] and form_data['stock_code']:
            with st.spinner("종목을 추가하고 있습니다..."):
                success, message = data_service.add_stock_by_code(form_data['stock_code'])
                
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        st.markdown("---")
        
        # 데이터 업데이트
        st.header("🔄 데이터 업데이트")
        
        if st.button("전체 데이터 업데이트"):
            try:
                # 기존 종목들의 심볼 가져오기
                if not data_summary.empty:
                    symbols = data_summary['symbol'].tolist()
                    
                    with st.spinner("데이터를 업데이트하고 있습니다..."):
                        from datetime import datetime, timedelta
                        
                        end_date = datetime.now().strftime('%Y%m%d')
                        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                        
                        results = data_service.update_stock_data(symbols, start_date, end_date)
                        
                        success_count = sum(1 for success in results.values() if success)
                        st.success(f"데이터 업데이트 완료: {success_count}/{len(symbols)} 종목")
                        
                        if success_count < len(symbols):
                            failed_symbols = [symbol for symbol, success in results.items() if not success]
                            st.warning(f"실패한 종목: {', '.join(failed_symbols)}")
                        
                        st.rerun()
                else:
                    st.warning("업데이트할 종목이 없습니다.")
                    
            except Exception as e:
                st.error(f"데이터 업데이트 실패: {e}")
        
    except Exception as e:
        st.error(f"데이터 관리 페이지 로딩 실패: {e}")

def render_settings_page():
    """설정 페이지"""
    
    st.title("⚙️ 시스템 설정")
    st.markdown("---")
    
    # 일반 설정
    st.header("🔧 일반 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("기본 포트폴리오 설정")
        default_capital = st.number_input(
            "기본 초기 자본 (원)",
            value=1000000,
            min_value=100000,
            max_value=10000000,
            step=100000
        )
        
        default_positions = st.number_input(
            "기본 최대 포지션 수",
            value=5,
            min_value=1,
            max_value=10,
            step=1
        )
    
    with col2:
        st.subheader("리스크 관리 설정")
        default_commission = st.number_input(
            "기본 수수료율 (%)",
            value=0.015,
            min_value=0.0,
            max_value=1.0,
            step=0.001,
            format="%.3f"
        )
        
        default_risk = st.number_input(
            "기본 거래당 리스크 (%)",
            value=2.0,
            min_value=0.5,
            max_value=10.0,
            step=0.5
        )
    
    # 설정 저장
    if st.button("설정 저장"):
        # 실제로는 설정을 파일이나 데이터베이스에 저장해야 함
        st.success("설정이 저장되었습니다!")
    
    st.markdown("---")
    
    # 시스템 정보
    st.header("ℹ️ 시스템 정보")
    
    system_info = {
        "Python 버전": sys.version.split()[0],
        "Streamlit 버전": st.__version__,
        "프로젝트 루트": str(project_root),
        "데이터베이스 경로": "trading.db"
    }
    
    for key, value in system_info.items():
        st.text(f"{key}: {value}")

def main():
    """메인 앱 실행"""
    
    # 커스텀 CSS 로드
    load_custom_css()
    
    # 네비게이션
    selected_page = render_navigation()
    
    # 페이지 라우팅
    if selected_page == "home":
        render_home_page()
    elif selected_page == "dashboard":
        try:
            sys.path.append(str(Path(__file__).parent / "pages"))
            from dashboard import render_dashboard_page
            render_dashboard_page()
        except ImportError as e:
            st.error(f"대시보드 페이지 로드 실패: {e}")
            st.info("대시보드 페이지는 개발 중입니다.")
    elif selected_page == "backtest":
        try:
            sys.path.append(str(Path(__file__).parent / "pages"))  
            from backtest import render_backtest_page
            render_backtest_page()
        except ImportError as e:
            st.error(f"백테스트 페이지 로드 실패: {e}")
            st.info("백테스트 페이지는 개발 중입니다.")
    elif selected_page == "data_management":
        render_data_management_page()
    elif selected_page == "settings":
        render_settings_page()

if __name__ == "__main__":
    main() 
"""
백테스팅 UI 모듈
- 전략 선택, 기간 설정, 결과 표시 등
"""
import streamlit as st
import pandas as pd
from typing import Optional
from src.utils.backtest_utils import get_available_symbols_for_backtest, run_backtest_ui

def render_backtest() -> None:
    """
    백테스팅 페이지 UI 렌더링
    """
    st.title("📊 백테스팅")
    st.markdown("""
    📈 **전략 백테스팅**  
    매매 전략의 과거 성과를 실제 매매처럼 시뮬레이션하여 검증합니다.
    
    💡 **전략 분석 vs 백테스팅 차이:**
    - **전략 분석**: 신호 생성, 지표 분석, 매개변수 최적화 (분석 중심)
    - **백테스팅**: 실제 매매 시뮬레이션, 자본 관리, 수익률 계산 (실전 중심)
    """)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("⚙️ 백테스팅 설정")
        symbols_df = get_available_symbols_for_backtest()
        if not symbols_df.empty:
            selected_display_names = st.multiselect(
                "백테스팅 종목:",
                symbols_df['display_name'].tolist(),
                default=symbols_df['display_name'].head(3).tolist(),
                help="여러 종목을 선택할 수 있습니다"
            )
            
            selected_symbols = []
            if selected_display_names:
                for display_name in selected_display_names:
                    symbol = display_name.split('(')[0]
                    selected_symbols.append(symbol)
        else:
            st.warning("백테스팅할 수 있는 종목이 없습니다.")
            selected_symbols = []
        
        period_type = st.selectbox(
            "기간 설정:",
            ["최근 N일", "날짜 직접 지정"]
        )
        if period_type == "최근 N일":
            days = st.slider("데이터 기간 (일)", 30, 1000, 365)
            start_date = end_date = None
        else:
            start_date = st.date_input("시작 날짜")
            end_date = st.date_input("종료 날짜")
            days = None
        strategy = st.selectbox(
            "매매 전략:",
            ["MACD 전략", "RSI 전략", "볼린저 밴드 전략", "이동평균 전략"]
        )
        initial_capital = st.number_input(
            "초기 자본 (원):",
            min_value=100000,
            max_value=100000000,
            value=1000000,
            step=100000
        )
        run_backtest = st.button("🚀 백테스팅 실행", use_container_width=True)
    with col2:
        st.subheader("📊 백테스팅 결과")
        if run_backtest and selected_symbols:
            with st.spinner("백테스팅 실행 중..."):
                results = run_backtest_ui(
                    symbols=selected_symbols,
                    start_date=str(start_date) if start_date else None,
                    end_date=str(end_date) if end_date else None,
                    initial_capital=initial_capital,
                    strategy_name=strategy
                )
                if results:
                    st.success("✅ 백테스팅 완료!")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        total_return = results.get('총 수익률', 0)
                        st.metric(
                            "총 수익률",
                            f"{total_return:.2f}%",
                            delta=f"{total_return:.2f}%"
                        )
                    with col2:
                        win_rate = results.get('승률', 0)
                        st.metric(
                            "승률",
                            f"{win_rate:.1f}%",
                            delta=f"{win_rate-50:.1f}%"
                        )
                    with col3:
                        sharpe = results.get('샤프 비율', 0)
                        st.metric(
                            "샤프 비율",
                            f"{sharpe:.2f}",
                            delta="Good" if sharpe > 1 else "Poor"
                        )
                    with col4:
                        max_dd = results.get('최대 낙폭', 0)
                        st.metric(
                            "최대 낙폭",
                            f"{max_dd:.2f}%",
                            delta=f"{max_dd:.2f}%",
                            delta_color="inverse"
                        )
                    if 'detailed_results' in results:
                        st.subheader("📋 종목별 상세 결과")
                        detailed_df = pd.DataFrame(results['detailed_results'])
                        st.dataframe(detailed_df, use_container_width=True)
                    if 'trades' in results:
                        st.subheader("💼 거래 내역")
                        trades_df = pd.DataFrame(results['trades'])
                        st.dataframe(trades_df.tail(20), use_container_width=True)
                else:
                    st.error("❌ 백테스팅 실행 실패")
        elif run_backtest and not selected_symbols:
            st.warning("종목을 선택해주세요.")
        else:
            st.info("설정을 완료하고 '백테스팅 실행' 버튼을 클릭하세요.") 
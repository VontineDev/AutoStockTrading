"""
백테스트 페이지
- 전략 선택 및 매개변수 설정
- 백테스트 실행 및 결과 분석
- 성과 지표 시각화
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging

# 서비스 계층 임포트
from src.ui.services.data_service import get_data_service
from src.ui.services.strategy_service import get_strategy_service
from src.ui.services.backtest_service import get_backtest_service

# 컴포넌트 임포트
from src.ui.components.charts import ChartComponent
from src.ui.components.widgets import WidgetComponent
from src.ui.components.tables import TableComponent


def render_backtest_page():
    """백테스트 페이지 렌더링"""
    
    # 헤더
    st.title("🧪 전략 백테스트")
    st.markdown("---")
    
    # 서비스 인스턴스
    data_service = get_data_service()
    strategy_service = get_strategy_service()
    backtest_service = get_backtest_service()
    
    # 사이드바 - 백테스트 설정
    with st.sidebar:
        st.header("⚙️ 백테스트 설정")
        
        # 전략 선택
        available_strategies = strategy_service.get_available_strategies()
        selected_strategy = WidgetComponent.render_strategy_selector(
            strategies=available_strategies,
            key="backtest_strategy_selector"
        )
        
        if not selected_strategy:
            st.warning("전략을 선택해주세요.")
            st.stop()
        
        # 전략 정보 표시
        strategy_info = strategy_service.get_strategy_info(selected_strategy)
        if strategy_info:
            st.info(f"**{strategy_info.get('name', selected_strategy)}**\n\n"
                   f"{strategy_info.get('description', '')}\n\n"
                   f"**적합한 시장:** {strategy_info.get('suitable_for', 'N/A')}\n\n"
                   f"**리스크 레벨:** {strategy_info.get('risk_level', 'N/A')}")
        
        # 전략 매개변수 입력
        strategy_params = WidgetComponent.render_parameter_inputs(
            strategy_info=strategy_info,
            key_prefix=f"backtest_{selected_strategy}"
        )
        
        # 포트폴리오 설정
        portfolio_settings = WidgetComponent.render_portfolio_settings(
            key_prefix="backtest_portfolio"
        )
        
        # 종목 선택
        st.header("🎯 종목 선택")
        available_symbols = data_service.get_available_symbols(min_data_days=100)
        
        if available_symbols.empty:
            st.warning("사용 가능한 종목이 없습니다.")
            st.stop()
        
        selected_symbols = WidgetComponent.render_stock_selector(
            available_symbols=available_symbols,
            key="backtest_symbol_selector",
            multi=True,
            max_selections=5
        )
        
        if not selected_symbols:
            st.warning("최소 1개 종목을 선택해주세요.")
            st.stop()
        
        # 날짜 범위 선택
        st.header("📅 백테스트 기간")
        start_date, end_date = WidgetComponent.render_date_range_selector(
            key="backtest_date_range",
            default_days=365,
            max_days=1000
        )
        
        # 백테스트 실행 버튼
        run_backtest = st.button("🚀 백테스트 실행", type="primary")
    
    # 메인 컨텐츠
    if run_backtest:
        if selected_strategy and selected_symbols and start_date and end_date:
            try:
                # 진행상황 표시
                progress_container = st.container()
                with progress_container:
                    st.info("백테스트를 실행하고 있습니다...")
                    progress_bar = st.progress(0)
                
                # 데이터 로드
                progress_bar.progress(20, "데이터 로딩 중...")
                stock_data = {}
                
                for i, symbol in enumerate(selected_symbols):
                    data = data_service.get_stock_data_with_indicators(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date
                    )
                    if not data.empty:
                        stock_data[symbol] = data
                    
                    # 진행률 업데이트
                    progress = 20 + (i + 1) / len(selected_symbols) * 30
                    progress_bar.progress(int(progress), f"데이터 로딩 중... ({i+1}/{len(selected_symbols)})")
                
                if not stock_data:
                    st.error("선택한 종목들의 데이터를 불러올 수 없습니다.")
                    st.stop()
                
                # 백테스트 실행
                progress_bar.progress(60, "백테스트 실행 중...")
                
                # RSI 전략 파라미터 매핑
                if selected_strategy.lower() == "rsi":
                    if "oversold_threshold" in strategy_params:
                        strategy_params["rsi_oversold"] = strategy_params.pop("oversold_threshold")
                    if "overbought_threshold" in strategy_params:
                        strategy_params["rsi_overbought"] = strategy_params.pop("overbought_threshold")
                    if "period" in strategy_params:
                        strategy_params["rsi_period"] = strategy_params.pop("period")

                backtest_results = backtest_service.run_simple_backtest(
                    strategy_name=selected_strategy,
                    symbols=list(stock_data.keys()),
                    data=stock_data,
                    initial_capital=portfolio_settings['initial_capital'],
                    **strategy_params
                )
                
                progress_bar.progress(80, "결과 분석 중...")
                
                # 백테스트 결과 판정
                if not isinstance(backtest_results, dict) or not backtest_results or 'equity_curve' not in backtest_results:
                    st.error(f"백테스트 실행에 실패했습니다. 결과: {backtest_results}")
                    st.stop()
                
                # portfolio_values → equity_curve['total_value']로 변경
                portfolio_values = backtest_results['equity_curve']['total_value']
                
                # 성과 지표 계산
                performance_metrics = backtest_service.calculate_performance_metrics(backtest_results)
                if not isinstance(performance_metrics, dict) or not performance_metrics:
                    st.warning("표시할 성과 지표가 없습니다.")
                
                progress_bar.progress(100, "완료!")
                progress_container.empty()
                
                # 결과 표시
                st.success("백테스트가 완료되었습니다!")
                
                # 성과 지표 카드
                WidgetComponent.render_metric_cards(
                    metrics=performance_metrics,
                    title="📊 백테스트 성과"
                )
                
                # 탭으로 결과 구성
                tab1, tab2, tab3, tab4 = st.tabs(["📈 포트폴리오 성과", "💹 거래 내역", "📊 상세 분석", "⚙️ 설정 요약"])
                
                with tab1:
                    # 포트폴리오 가치 차트
                    if 'equity_curve' in backtest_results:
                        equity_curve = backtest_results['equity_curve']
                        if isinstance(equity_curve, dict):
                            equity_curve = pd.Series(equity_curve['total_value'])
                        
                        ChartComponent.render_performance_chart(
                            portfolio_values=equity_curve,
                            title="포트폴리오 가치 변화"
                        )
                    
                    # 성과 테이블
                    TableComponent.render_performance_table(
                        metrics=performance_metrics,
                        title="성과 지표 상세"
                    )
                
                with tab2:
                    # 거래 내역
                    trades = backtest_results.get('trades', None)
                    if trades is not None:
                        if isinstance(trades, (pd.DataFrame, pd.Series)):
                            if not trades.empty:
                                trades_df = pd.DataFrame(trades)
                                TableComponent.render_dataframe(
                                    data=trades_df,
                                    title="거래 내역",
                                    height=400
                                )
                            else:
                                st.info("거래 내역이 없습니다.")
                        elif isinstance(trades, list):
                            if len(trades) > 0:
                                trades_df = pd.DataFrame(trades)
                                TableComponent.render_dataframe(
                                    data=trades_df,
                                    title="거래 내역",
                                    height=400
                                )
                            else:
                                st.info("거래 내역이 없습니다.")
                        else:
                            st.info("거래 내역이 없습니다.")
                    else:
                        st.info("거래 내역이 없습니다.")
                
                with tab3:
                    # 상세 분석
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # 월별 수익률
                        if 'equity_curve' in backtest_results:
                            st.subheader("월별 수익률")
                            # 월별 수익률 계산 로직 (간단화)
                            st.info("월별 수익률 분석은 추후 구현 예정입니다.")
                    
                    with col2:
                        # 드로우다운 분석
                        st.subheader("드로우다운 분석")
                        if 'equity_curve' in backtest_results:
                            equity_curve = backtest_results['equity_curve']
                            # DataFrame이면 'total_value'만, dict면 Series로 변환, Series면 그대로
                            if isinstance(equity_curve, pd.DataFrame):
                                equity_curve = equity_curve['total_value']
                            elif isinstance(equity_curve, dict):
                                equity_curve = pd.Series(equity_curve['total_value'])
                            # 이제 equity_curve는 numeric Series임이 보장됨
                            peak = equity_curve.expanding().max()
                            drawdown = (equity_curve - peak) / peak * 100
                            ChartComponent.render_line_chart(
                                data=pd.DataFrame({'drawdown': drawdown}),
                                y_columns=['drawdown'],
                                title="드로우다운 (%)",
                                height=300
                            )
                
                with tab4:
                    # 설정 요약
                    st.subheader("백테스트 설정 요약")
                    
                    config_summary = {
                        "전략": selected_strategy,
                        "종목": ", ".join(selected_symbols),
                        "기간": f"{start_date} ~ {end_date}",
                        "초기 자본": f"{portfolio_settings['initial_capital']:,.0f}원",
                        "수수료율": f"{portfolio_settings['commission_rate']*100:.3f}%",
                        "최대 포지션": f"{portfolio_settings['max_positions']}개"
                    }
                    
                    # 전략 매개변수 추가
                    for param_name, param_value in strategy_params.items():
                        config_summary[f"전략 매개변수 - {param_name}"] = str(param_value)
                    
                    TableComponent.render_performance_table(
                        metrics=config_summary,
                        title=""
                    )
                
            except Exception as e:
                logging.error(f"백테스트 페이지 오류: {e}")
                st.error(f"백테스트 실행 중 오류가 발생했습니다: {e}")
        else:
            st.warning("모든 설정을 완료한 후 백테스트를 실행해주세요.")
    else:
        # 백테스트 실행 전 안내
        st.info("""
        ### 백테스트 실행 방법
        1. **사이드바에서 전략을 선택**하고 매개변수를 조정하세요
        2. **포트폴리오 설정**을 확인하세요
        3. **백테스트할 종목**을 선택하세요 (최대 5개)
        4. **백테스트 기간**을 설정하세요
        5. **"백테스트 실행" 버튼**을 클릭하세요
        
        ### 주의사항
        - 백테스트는 과거 데이터를 기반으로 하며, 실제 투자 성과를 보장하지 않습니다
        - 수수료, 슬리피지 등이 실제 거래와 다를 수 있습니다
        - 100만원 규모 스윙 트레이딩에 최적화되어 있습니다
        """)


if __name__ == "__main__":
    render_backtest_page() 
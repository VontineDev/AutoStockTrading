"""
대시보드 페이지
- 종목 차트 및 분석
- 실시간 데이터 표시
- 기술적 지표 시각화
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging
import sys
from pathlib import Path
from typing import Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_import(module_name: str, class_name: Optional[str] = None):
    """안전한 모듈 임포트"""
    try:
        module = __import__(module_name, fromlist=[class_name] if class_name else [])
        if class_name:
            return getattr(module, class_name)
        return module
    except ImportError as e:
        st.error(f"모듈 임포트 실패 {module_name}: {e}")
        return None

# 서비스 계층 임포트
data_service_func = safe_import('src.ui.services.data_service', 'get_data_service')
data_service = None
if data_service_func:
    try:
        data_service = data_service_func()
    except Exception as e:
        st.error(f"데이터 서비스 초기화 실패: {e}")

# 컴포넌트 임포트
ChartComponent = safe_import('src.ui.components.charts', 'ChartComponent')
WidgetComponent = safe_import('src.ui.components.widgets', 'WidgetComponent')
TableComponent = safe_import('src.ui.components.tables', 'TableComponent')

def render_simple_dashboard():
    """간단한 대시보드 (컴포넌트 오류 시 사용)"""
    st.title("📈 스윙 트레이딩 대시보드")
    st.markdown("---")
    
    # 사이드바
    with st.sidebar:
        st.header("🎯 종목 선택")
        
        # 기본 종목들
        default_symbols = ["005930", "000660", "035420", "051910", "028260"]
        symbol_names = {
            "005930": "삼성전자",
            "000660": "SK하이닉스", 
            "035420": "NAVER",
            "051910": "LG화학",
            "028260": "삼성물산",
        }
        
        selected_symbol = st.selectbox(
            "종목 선택",
            default_symbols,
            format_func=lambda x: f"{x} ({symbol_names.get(x, 'Unknown')})"
        )
        
        # 날짜 범위
        st.header("📅 기간 설정")
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "시작 날짜",
                value=datetime.now().date() - timedelta(days=365),
                max_value=datetime.now().date()
            )
        
        with col2:
            end_date = st.date_input(
                "종료 날짜", 
                value=datetime.now().date(),
                min_value=start_date,
                max_value=datetime.now().date()
            )
        
        # 차트 옵션
        st.header("📊 차트 옵션")
        show_volume = st.checkbox("거래량 표시", value=True)
        show_indicators = st.checkbox("기술적 지표 표시", value=True)
    
    # 메인 컨텐츠
    if selected_symbol and start_date and end_date:
        try:
            # 데이터 로드
            with st.spinner("데이터를 불러오는 중..."):
                if data_service:
                    stock_data = data_service.get_stock_data_with_indicators(
                        symbol=selected_symbol,
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d')
                    )
                else:
                    st.error("데이터 서비스를 불러올 수 없습니다.")
                    return
                
            if stock_data.empty:
                st.error(f"{selected_symbol}의 데이터가 없습니다.")
                st.info("데이터 관리 페이지에서 데이터를 업데이트해주세요.")
                return
            
            # 종목 정보 표시
            col1, col2, col3, col4 = st.columns(4)
            
            try:
                current_price = stock_data['close'].iloc[-1]
                prev_price = stock_data['close'].iloc[-2] if len(stock_data) > 1 else current_price
                price_change = current_price - prev_price
                price_change_pct = (price_change / prev_price * 100) if prev_price != 0 else 0
                
                with col1:
                    st.metric(
                        label="현재가",
                        value=f"{current_price:,.0f}원",
                        delta=f"{price_change:+,.0f}원"
                    )
                
                with col2:
                    st.metric(
                        label="등락률",
                        value=f"{price_change_pct:+.2f}%"
                    )
                
                with col3:
                    st.metric(
                        label="거래량",
                        value=f"{stock_data['volume'].iloc[-1]:,.0f}"
                    )
                
                with col4:
                    st.metric(
                        label="데이터 일수",
                        value=f"{len(stock_data)}일"
                    )
            except Exception as e:
                st.error(f"지표 계산 실패: {e}")
            
            # 차트 섹션
            st.header("📈 주식 차트")
            
            # 간단한 차트 (Plotly 직접 사용)
            try:
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                
                # 서브플롯 생성
                if show_volume:
                    fig = make_subplots(
                        rows=2, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.03,
                        subplot_titles=(f"{selected_symbol} 주식 차트", '거래량'),
                        row_width=[0.7, 0.3]
                    )
                else:
                    fig = go.Figure()
                
                # 캔들스틱 차트
                candlestick = go.Candlestick(
                    x=stock_data.index,
                    open=stock_data['open'],
                    high=stock_data['high'],
                    low=stock_data['low'],
                    close=stock_data['close'],
                    name="OHLC",
                    increasing_line_color='red',
                    decreasing_line_color='blue'
                )
                
                if show_volume:
                    fig.add_trace(candlestick, row=1, col=1)
                else:
                    fig.add_trace(candlestick)
                
                # 볼륨 차트
                if show_volume and 'volume' in stock_data.columns:
                    colors = ['red' if close >= open else 'blue' 
                             for close, open in zip(stock_data['close'], stock_data['open'])]
                    
                    fig.add_trace(
                        go.Bar(
                            x=stock_data.index,
                            y=stock_data['volume'],
                            name="거래량",
                            marker_color=colors,
                            opacity=0.7
                        ),
                        row=2, col=1
                    )
                
                # 레이아웃 설정
                fig.update_layout(
                    title=f"{selected_symbol} 주식 차트",
                    height=600,
                    xaxis_rangeslider_visible=False,
                    showlegend=True,
                    template="plotly_white"
                )
                
                if show_volume:
                    fig.update_xaxes(showgrid=True, row=2, col=1)
                    fig.update_yaxes(title="가격 (원)", row=1, col=1)
                    fig.update_yaxes(title="거래량", row=2, col=1)
                
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"차트 렌더링 실패: {e}")
            
            # 최근 데이터 테이블
            st.header("📋 최근 데이터")
            try:
                recent_data = stock_data.tail(10)
                st.dataframe(recent_data, use_container_width=True)
            except Exception as e:
                st.error(f"데이터 테이블 렌더링 실패: {e}")
            
        except Exception as e:
            st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")

def render_dashboard_page():
    """대시보드 페이지 렌더링"""
    
    try:
        # 컴포넌트들이 모두 로드되었는지 확인
        if all([ChartComponent, WidgetComponent, TableComponent, data_service]):
            # 전체 기능 대시보드
            render_full_dashboard()
        else:
            # 간단한 대시보드
            render_simple_dashboard()
            
    except Exception as e:
        logger.error(f"대시보드 페이지 렌더링 실패: {e}")
        st.error(f"페이지 로딩 중 오류가 발생했습니다: {e}")
        st.info("간단한 대시보드로 전환합니다.")
        render_simple_dashboard()

def render_full_dashboard():
    """전체 기능 대시보드"""
    st.title("📈 스윙 트레이딩 대시보드")
    st.markdown("---")
    
    try:
        # 사이드바 - 종목 선택
        with st.sidebar:
            st.header("🎯 종목 선택")
            
            # 사용 가능한 종목 목록 조회
            if data_service is None:
                st.error("데이터 서비스를 사용할 수 없습니다.")
                st.stop()
                
            available_symbols = data_service.get_available_symbols(min_data_days=30)
            
            if available_symbols.empty:
                st.warning("사용 가능한 종목이 없습니다.")
                st.info("데이터 관리 페이지에서 종목을 추가해주세요.")
                st.stop()
            
            # 종목 선택 위젯
            if WidgetComponent is None:
                st.error("위젯 컴포넌트를 사용할 수 없습니다.")
                st.stop()
                
            selected_symbol = WidgetComponent.render_stock_selector(
                available_symbols=available_symbols,
                key="dashboard_symbol_selector",
                multi=False
            )
            
            if not selected_symbol:
                st.warning("종목을 선택해주세요.")
                st.stop()
            
            # 날짜 범위 선택
            st.header("📅 기간 설정")
            start_date, end_date = WidgetComponent.render_date_range_selector(
                key="dashboard_date_range",
                default_days=365
            )
            
            if not start_date or not end_date:
                st.warning("날짜 범위를 설정해주세요.")
                st.stop()
            
            # 차트 옵션
            st.header("📊 차트 옵션")
            show_volume = st.checkbox("거래량 표시", value=True)
            show_indicators = st.checkbox("기술적 지표 표시", value=True)
            
            if show_indicators:
                selected_indicators = st.multiselect(
                    "표시할 지표",
                    options=['SMA_20', 'EMA_12', 'EMA_26', 'BB_upper', 'BB_lower'],
                    default=['SMA_20', 'EMA_12']
                )
            else:
                selected_indicators = []
        
        # 메인 컨텐츠
        if selected_symbol and start_date and end_date:
            try:
                # 데이터 로드
                with st.spinner("데이터를 불러오는 중..."):
                    stock_data = data_service.get_stock_data_with_indicators(
                        symbol=selected_symbol,
                        start_date=start_date,
                        end_date=end_date
                    )
                
                if stock_data.empty:
                    st.error(f"{selected_symbol}의 데이터가 없습니다.")
                    st.info("데이터 관리 페이지에서 데이터를 업데이트해주세요.")
                    st.stop()
                
                # 종목 정보 표시
                col1, col2, col3, col4 = st.columns(4)
                
                try:
                    current_price = stock_data['close'].iloc[-1]
                    prev_price = stock_data['close'].iloc[-2] if len(stock_data) > 1 else current_price
                    price_change = current_price - prev_price
                    price_change_pct = (price_change / prev_price * 100) if prev_price != 0 else 0
                    
                    with col1:
                        st.metric(
                            label="현재가",
                            value=f"{current_price:,.0f}원",
                            delta=f"{price_change:+,.0f}원"
                        )
                    
                    with col2:
                        st.metric(
                            label="등락률",
                            value=f"{price_change_pct:+.2f}%"
                        )
                    
                    with col3:
                        st.metric(
                            label="거래량",
                            value=f"{stock_data['volume'].iloc[-1]:,.0f}"
                        )
                    
                    with col4:
                        st.metric(
                            label="데이터 일수",
                            value=f"{len(stock_data)}일"
                        )
                except Exception as e:
                    st.error(f"지표 계산 실패: {e}")
                
                # 차트 섹션
                st.header("📈 주식 차트")
                
                # 지표 데이터 준비
                indicators_data = {}
                if show_indicators and selected_indicators:
                    for indicator in selected_indicators:
                        if indicator in stock_data.columns:
                            indicators_data[indicator] = stock_data[indicator]
                
                # 캔들스틱 차트 렌더링
                if ChartComponent is None:
                    st.error("차트 컴포넌트를 사용할 수 없습니다.")
                else:
                    try:
                        ChartComponent.render_candlestick_chart(
                            data=stock_data,
                            title=f"{selected_symbol} 주식 차트",
                            volume=show_volume,
                            indicators=indicators_data if indicators_data else None
                        )
                    except Exception as e:
                        st.error(f"차트 렌더링 실패: {e}")
                
                # 기술적 지표 섹션
                if show_indicators:
                    st.header("📊 기술적 지표")
                    
                    # 지표 탭
                    indicator_tabs = st.tabs(["추세", "모멘텀", "변동성"])
                    
                    with indicator_tabs[0]:  # 추세
                        trend_indicators = ['SMA_20', 'EMA_12', 'EMA_26']
                        available_trend = [ind for ind in trend_indicators if ind in stock_data.columns]
                        
                        if available_trend and ChartComponent is not None:
                            try:
                                ChartComponent.render_line_chart(
                                    data=stock_data,
                                    y_columns=available_trend,
                                    title="추세 지표",
                                    height=300
                                )
                            except Exception as e:
                                st.error(f"추세 지표 차트 실패: {e}")
                        else:
                            st.info("추세 지표 데이터가 없습니다.")
                    
                    with indicator_tabs[1]:  # 모멘텀
                        if 'RSI' in stock_data.columns and ChartComponent is not None:
                            try:
                                ChartComponent.render_indicator_chart(
                                    data=stock_data,
                                    indicator_columns=['RSI'],
                                    title="RSI",
                                    height=300,
                                    thresholds={'RSI': [30, 70]}
                                )
                            except Exception as e:
                                st.error(f"RSI 차트 실패: {e}")
                        else:
                            st.info("RSI 데이터가 없습니다.")
                    
                    with indicator_tabs[2]:  # 변동성
                        volatility_indicators = ['BB_upper', 'BB_middle', 'BB_lower']
                        available_volatility = [ind for ind in volatility_indicators if ind in stock_data.columns]
                        
                        if available_volatility and ChartComponent is not None:
                            try:
                                ChartComponent.render_line_chart(
                                    data=stock_data,
                                    y_columns=available_volatility,
                                    title="볼린저 밴드",
                                    height=300
                                )
                            except Exception as e:
                                st.error(f"볼린저 밴드 차트 실패: {e}")
                        else:
                            st.info("변동성 지표 데이터가 없습니다.")
                
                # 최근 데이터 테이블
                st.header("📋 최근 데이터")
                if TableComponent is None:
                    st.error("테이블 컴포넌트를 사용할 수 없습니다.")
                else:
                    try:
                        recent_data = stock_data.tail(10)
                        TableComponent.render_dataframe(
                            data=recent_data,
                            height=300
                        )
                    except Exception as e:
                        st.error(f"데이터 테이블 렌더링 실패: {e}")
                
            except Exception as e:
                logging.error(f"대시보드 데이터 처리 실패: {e}")
                st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
        
    except Exception as e:
        logging.error(f"대시보드 페이지 렌더링 실패: {e}")
        st.error(f"페이지 로딩 중 오류가 발생했습니다: {e}")
        st.info("시스템을 다시 시작해주세요.")


if __name__ == "__main__":
    render_dashboard_page() 
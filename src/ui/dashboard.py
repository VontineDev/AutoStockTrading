"""
대시보드 UI 모듈
- 종목 차트, 지표, 종목 선택 등
"""
import streamlit as st
import pandas as pd
from typing import Any
from src.utils.common import load_config, load_stock_data, calculate_ta_indicators, create_candlestick_chart

def render_dashboard() -> None:
    """
    대시보드 페이지 UI 렌더링
    """
    config = load_config()
    
    # 헤더
    st.markdown(f'<h1 class="main-header">📈 {config["project"]["name"]}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p style="text-align: center; color: #666;">v{config["project"]["version"]} | 100만원 규모 스윙 트레이딩 시스템</p>', unsafe_allow_html=True)
    
    # 사이드바 - 종목 선택
    st.sidebar.header("🎯 종목 선택")
    
    # 기본 종목들
    default_symbols = ['005930', '000660', '035420', '051910', '028260']
    symbol_names = {
        '005930': '삼성전자',
        '000660': 'SK하이닉스', 
        '035420': 'NAVER',
        '051910': 'LG화학',
        '028260': '삼성물산'
    }
    
    selected_symbol = st.sidebar.selectbox(
        "종목 선택",
        default_symbols,
        format_func=lambda x: f"{x} ({symbol_names.get(x, 'Unknown')})"
    )
    
    # 분석 기간 설정
    st.sidebar.header("📅 분석 기간")
    period_options = {
        '1개월': 30,
        '3개월': 90,
        '6개월': 180,
        '1년': 365,
        '2년': 730
    }
    
    selected_period = st.sidebar.selectbox("기간 선택", list(period_options.keys()), index=2)
    data_limit = period_options[selected_period]
    
    # 데이터 로드
    with st.spinner("데이터를 로드하는 중..."):
        data = load_stock_data([selected_symbol], limit=data_limit)
    
    if not data or selected_symbol not in data:
        st.error("데이터를 찾을 수 없습니다. 먼저 데이터를 업데이트해주세요.")
        st.code("python src/main.py update-data")
        return
    
    df = data[selected_symbol]
    
    # 컬럼명 소문자화 및 공백 제거
    df.columns = [col.strip().lower() for col in df.columns]

    # 다양한 변형을 표준 영문명으로 통일
    rename_map = {}
    for col in df.columns:
        if col in ['종가', 'close', 'close_price', 'c'] and col != 'close':
            rename_map[col] = 'close'
        if col in ['거래량', 'volume', 'vol', 'v'] and col != 'volume':
            rename_map[col] = 'volume'
        if col in ['시가', 'open', 'o'] and col != 'open':
            rename_map[col] = 'open'
        if col in ['고가', 'high', 'h'] and col != 'high':
            rename_map[col] = 'high'
        if col in ['저가', 'low', 'l'] and col != 'low':
            rename_map[col] = 'low'
        if col in ['일자', '날짜', 'datetime', 'dt'] and col != 'date':
            rename_map[col] = 'date'
    df = df.rename(columns=rename_map)

    # 필수 컬럼 체크 및 디버깅 출력
    required_cols = ['date', 'close', 'open', 'high', 'low', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"데이터에 {missing_cols} 컬럼이 없습니다. 실제 컬럼: {df.columns.tolist()}")
        return

    # TA-Lib 지표 계산
    with st.spinner("기술적 지표를 계산하는 중..."):
        df = calculate_ta_indicators(df)
    
    # 최신 정보 표시
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    # 메트릭 카드들
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        price_change = latest['close'] - prev['close']
        price_change_pct = (price_change / prev['close']) * 100
        
        st.metric(
            label="현재가",
            value=f"{latest['close']:,.0f}원",
            delta=f"{price_change:+.0f}원 ({price_change_pct:+.2f}%)"
        )
    
    with col2:
        volume_change = latest['volume'] - prev['volume']
        volume_change_pct = (volume_change / prev['volume']) * 100 if prev['volume'] > 0 else 0
        
        st.metric(
            label="거래량",
            value=f"{latest['volume']:,.0f}",
            delta=f"{volume_change_pct:+.1f}%"
        )
    
    with col3:
        if 'RSI' in df.columns and not pd.isna(latest['RSI']):
            rsi_value = latest['RSI']
            rsi_status = "과매수" if rsi_value > 70 else "과매도" if rsi_value < 30 else "중립"
            st.metric(
                label="RSI (14)",
                value=f"{rsi_value:.1f}",
                delta=rsi_status
            )
        else:
            st.metric("RSI (14)", "N/A")
    
    with col4:
        if 'MACD' in df.columns and not pd.isna(latest['MACD']):
            macd_signal = "상승" if latest['MACD'] > latest['MACD_signal'] else "하락"
            st.metric(
                label="MACD 신호",
                value=f"{latest['MACD']:.3f}",
                delta=macd_signal
            )
        else:
            st.metric("MACD 신호", "N/A")
    
    # 차트 표시
    st.subheader("📊 기술적 분석 차트")
    chart = create_candlestick_chart(df, f"{selected_symbol} ({symbol_names.get(selected_symbol, '')})")
    st.plotly_chart(chart, use_container_width=True)
    
    # 상세 정보 테이블
    st.subheader("📋 최근 데이터")
    recent_data = df.tail(10).copy()
    recent_data = recent_data.round(2)
    # date 컬럼을 안전하게 datetime으로 변환 후 포맷팅
    recent_data['date'] = pd.to_datetime(recent_data['date'], errors='coerce')
    recent_data = recent_data.dropna(subset=['date'])
    recent_data['date'] = recent_data['date'].dt.strftime('%Y-%m-%d')
    display_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    if 'RSI' in recent_data.columns:
        display_columns.append('RSI')
    if 'MACD' in recent_data.columns:
        display_columns.append('MACD')
    st.dataframe(
        recent_data[display_columns].sort_values('date', ascending=False),
        use_container_width=True
    ) 
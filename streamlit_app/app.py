"""
TA-Lib 스윙 트레이딩 자동매매 시스템 Streamlit 앱

pykrx + TA-Lib 기반의 100만원 규모 스윙 트레이딩 웹 인터페이스
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import yaml
import os

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 페이지 설정
st.set_page_config(
    page_title="TA-Lib 스윙 트레이딩",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 설정
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
}
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 10px;
    margin: 0.5rem 0;
}
.success-metric {
    background-color: #d4edda;
    color: #155724;
}
.warning-metric {
    background-color: #fff3cd;
    color: #856404;
}
.danger-metric {
    background-color: #f8d7da;
    color: #721c24;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_config():
    """설정 파일 로드"""
    config_path = PROJECT_ROOT / 'config.yaml'
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    except Exception as e:
        st.error(f"설정 파일 로드 실패: {e}")
    
    return {
        'project': {
            'name': 'TA-Lib 스윙 트레이딩',
            'version': '1.0.0'
        }
    }

@st.cache_data
def load_stock_data(symbols: list, limit: int = 500):
    """주식 데이터 로드"""
    db_path = PROJECT_ROOT / 'data' / 'trading.db'
    
    if not db_path.exists():
        return {}
    
    data = {}
    try:
        with sqlite3.connect(db_path) as conn:
            for symbol in symbols:
                query = """
                SELECT date, open, high, low, close, volume
                FROM stock_data 
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT ?
                """
                df = pd.read_sql_query(query, conn, params=(symbol, limit))
                
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
                    df = df.sort_values('date').reset_index(drop=True)
                    data[symbol] = df
                    
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
    
    return data

@st.cache_data
def get_symbol_info():
    """종목 정보 조회"""
    db_path = PROJECT_ROOT / 'data' / 'trading.db'
    
    if not db_path.exists():
        return pd.DataFrame()
    
    try:
        with sqlite3.connect(db_path) as conn:
            query = """
            SELECT symbol, name, market
            FROM stock_info
            ORDER BY symbol
            """
            return pd.read_sql_query(query, conn)
    except Exception:
        return pd.DataFrame()

def calculate_ta_indicators(df: pd.DataFrame):
    """TA-Lib 지표 계산"""
    try:
        import talib
        
        # 기본 지표들
        df['SMA_20'] = talib.SMA(df['close'], timeperiod=20)
        df['EMA_12'] = talib.EMA(df['close'], timeperiod=12)
        df['EMA_26'] = talib.EMA(df['close'], timeperiod=26)
        
        # MACD
        df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(df['close'])
        
        # RSI
        df['RSI'] = talib.RSI(df['close'], timeperiod=14)
        
        # 볼린저 밴드
        df['BB_upper'], df['BB_middle'], df['BB_lower'] = talib.BBANDS(df['close'])
        
        # ATR
        df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        
        return df
        
    except ImportError:
        st.error("TA-Lib이 설치되지 않았습니다. 'pip install TA-Lib'로 설치해주세요.")
        return df
    except Exception as e:
        st.error(f"지표 계산 실패: {e}")
        return df

def run_backtest_ui(symbols: list, start_date: str = None, end_date: str = None, 
                    initial_capital: float = 1000000, strategy_name: str = "MACD 전략"):
    """
    Streamlit UI에서 백테스팅 실행
    
    Args:
        symbols: 테스트할 종목 리스트
        start_date: 시작날짜 (YYYY-MM-DD)
        end_date: 종료날짜 (YYYY-MM-DD)
        initial_capital: 초기 자본
        strategy_name: 전략 이름
        
    Returns:
        백테스팅 결과 또는 None
    """
    try:
        import sys
        sys.path.append(str(PROJECT_ROOT / 'src'))
        
        from strategies.macd_strategy import MACDStrategy
        from strategies.rsi_strategy import RSIStrategy
        from strategies.bollinger_band_strategy import BollingerBandStrategy
        from strategies.moving_average_strategy import MovingAverageStrategy
        from trading.backtest import BacktestEngine, BacktestConfig
        import sqlite3
        
        # 데이터 로드
        db_path = PROJECT_ROOT / 'data' / 'trading.db'
        if not db_path.exists():
            st.error("데이터베이스가 없습니다. 먼저 데이터를 업데이트하세요.")
            return None
        
        data = {}
        with sqlite3.connect(db_path) as conn:
            for symbol in symbols:
                query = """
                SELECT date, open, high, low, close, volume
                FROM stock_data 
                WHERE symbol = ?
                ORDER BY date
                """
                df = pd.read_sql_query(query, conn, params=(symbol,))
                
                if not df.empty:
                    # 날짜 형식 문제 해결: 다양한 날짜 형식을 자동으로 처리
                    df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
                    df = df.dropna(subset=['date'])  # 날짜 파싱 실패한 행 제거
                    df.set_index('date', inplace=True)
                    data[symbol] = df
        
        if not data:
            st.error("백테스팅할 데이터가 없습니다.")
            return None
        
        # 전략 선택
        if strategy_name == "MACD 전략":
            strategy = MACDStrategy()
        elif strategy_name == "RSI 전략":
            strategy = RSIStrategy()
        elif strategy_name == "볼린저 밴드 전략":
            strategy = BollingerBandStrategy()
        elif strategy_name == "이동평균 전략":
            strategy = MovingAverageStrategy()
        else:
            st.warning(f"{strategy_name}는 지원되지 않습니다. MACD 전략을 사용합니다.")
            strategy = MACDStrategy()
        
        # 백테스팅 실행
        config = BacktestConfig(initial_capital=initial_capital)
        engine = BacktestEngine(config)
        
        results = engine.run_backtest(strategy, data, start_date, end_date)
        
        return results
        
    except Exception as e:
        st.error(f"백테스팅 실행 중 오류: {str(e)}")
        return None

def create_candlestick_chart(df: pd.DataFrame, symbol: str, indicators: list = None):
    """캔들스틱 차트 생성"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=('가격', 'MACD', 'RSI'),
        row_width=[0.2, 0.1, 0.1]
    )
    
    # 캔들스틱
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=symbol,
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ),
        row=1, col=1
    )
    
    # 이동평균선
    if 'SMA_20' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['SMA_20'],
                name='SMA 20',
                line=dict(color='orange', width=1)
            ),
            row=1, col=1
        )
    
    if 'EMA_12' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['EMA_12'],
                name='EMA 12',
                line=dict(color='blue', width=1)
            ),
            row=1, col=1
        )
    
    # 볼린저 밴드
    if all(col in df.columns for col in ['BB_upper', 'BB_lower']):
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['BB_upper'],
                name='BB Upper',
                line=dict(color='gray', width=1),
                opacity=0.3
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['BB_lower'],
                name='BB Lower',
                line=dict(color='gray', width=1),
                fill='tonexty',
                opacity=0.1
            ),
            row=1, col=1
        )
    
    # MACD
    if all(col in df.columns for col in ['MACD', 'MACD_signal', 'MACD_hist']):
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['MACD'],
                name='MACD',
                line=dict(color='blue', width=1)
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['MACD_signal'],
                name='Signal',
                line=dict(color='red', width=1)
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['MACD_hist'],
                name='Histogram',
                marker_color='green',
                opacity=0.7
            ),
            row=2, col=1
        )
    
    # RSI
    if 'RSI' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['RSI'],
                name='RSI',
                line=dict(color='purple', width=2)
            ),
            row=3, col=1
        )
        
        # RSI 과매수/과매도 라인
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    
    # 레이아웃 설정
    fig.update_layout(
        title=f"{symbol} 기술적 분석",
        xaxis_rangeslider_visible=False,
        height=800,
        showlegend=True
    )
    
    return fig

def render_dashboard():
    """대시보드 페이지"""
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
    
    # 최근 10일 데이터
    recent_data = df.tail(10).copy()
    recent_data = recent_data.round(2)
    recent_data['date'] = recent_data['date'].dt.strftime('%Y-%m-%d')
    
    # 필요한 컬럼만 선택
    display_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    if 'RSI' in recent_data.columns:
        display_columns.append('RSI')
    if 'MACD' in recent_data.columns:
        display_columns.append('MACD')
    
    st.dataframe(
        recent_data[display_columns].sort_values('date', ascending=False),
        use_container_width=True
    )

def render_strategy_analysis():
    """전략 분석 페이지"""
    st.title("🎯 매매 전략 분석")
    
    st.info("현재 개발 중인 기능입니다. TA-Lib 기반의 다양한 매매 전략을 분석할 수 있습니다.")
    
    # 전략 선택
    strategy_options = ["MACD 전략", "RSI 전략", "볼린저 밴드 전략", "이동평균 전략"]
    selected_strategy = st.selectbox("전략 선택", strategy_options)
    
    st.subheader(f"📈 {selected_strategy}")
    
    if selected_strategy == "MACD 전략":
        st.markdown("""
        **MACD (Moving Average Convergence Divergence) 전략**
        
        - **매수 신호**: MACD 라인이 시그널 라인을 상향 돌파
        - **매도 신호**: MACD 라인이 시그널 라인을 하향 돌파
        - **확인 신호**: 히스토그램의 방향성 변화
        - **권장 설정**: Fast 12, Slow 26, Signal 9
        """)
    
    elif selected_strategy == "RSI 전략":
        st.markdown("""
        **RSI (Relative Strength Index) 전략**
        
        - **매수 신호**: RSI < 30 (과매도 구간)
        - **매도 신호**: RSI > 70 (과매수 구간)
        - **추가 확인**: 다이버전스 패턴
        - **권장 설정**: 14일 기간
        """)
    
    elif selected_strategy == "볼린저 밴드 전략":
        st.markdown("""
        **볼린저 밴드 (Bollinger Bands) 전략**
        
        - **매수 신호**: 가격이 하단 밴드 터치 후 반등
        - **매도 신호**: 가격이 상단 밴드 터치 후 하락
        - **주의사항**: 강한 추세에서는 밴드를 따라 움직일 수 있음
        - **권장 설정**: 20일, 2 표준편차
        """)
    
    elif selected_strategy == "이동평균 전략":
        st.markdown("""
        **이동평균 (Moving Average) 전략**
        
        - **매수 신호**: 단기 이평선이 장기 이평선 상향 돌파 (골든크로스)
        - **매도 신호**: 단기 이평선이 장기 이평선 하향 돌파 (데드크로스)
        - **추세 확인**: 가격이 이동평균선 위/아래 위치
        - **권장 설정**: 5일, 20일 이동평균
        """)

def render_optimization():
    """매개변수 최적화 페이지"""
    st.title("⚙️ 매개변수 최적화")
    
    st.info("이 페이지에서는 TA-Lib 지표의 매개변수를 최적화할 수 있습니다.")
    
    # 최적화 기능은 별도 모듈에서 import
    try:
        sys.path.append(str(PROJECT_ROOT / 'src'))
        from ui.optimization import render_optimization_ui
        render_optimization_ui()
    except ImportError:
        st.error("최적화 모듈을 로드할 수 없습니다.")
        st.code("python src/main.py optimize")

def render_backtest():
    """백테스팅 페이지"""
    st.title("📊 백테스팅")
    
    st.info("전략의 과거 성과를 분석합니다. 기간을 지정하여 백테스팅을 실행할 수 있습니다.")
    
    # 백테스팅 설정
    col1, col2, col3 = st.columns(3)
    
    with col1:
        available_symbols = ['005930', '000660', '035420', '005490', '035720']
        symbol_names = {
            '005930': '삼성전자',
            '000660': 'SK하이닉스', 
            '035420': 'NAVER',
            '005490': 'POSCO홀딩스',
            '035720': '카카오'
        }
        
        test_symbols = st.multiselect(
            "테스트 종목",
            available_symbols,
            default=['005930'],
            format_func=lambda x: f"{x} ({symbol_names.get(x, '')})"
        )
    
    with col2:
        # 날짜 범위 선택
        date_range_type = st.radio(
            "기간 선택 방식",
            ["최근 N일", "날짜 직접 지정"]
        )
        
        if date_range_type == "최근 N일":
            test_period = st.slider("테스트 기간 (일)", 30, 365, 180)
            start_date = None
            end_date = None
        else:
            # 현재 날짜 기준으로 기본값 설정
            from datetime import datetime, timedelta
            default_end = datetime.now().date()
            default_start = default_end - timedelta(days=180)
            
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                start_date = st.date_input("시작일", value=default_start)
            with date_col2:
                end_date = st.date_input("종료일", value=default_end)
            
            # 날짜 형식 변환
            start_date = start_date.strftime('%Y-%m-%d') if start_date else None
            end_date = end_date.strftime('%Y-%m-%d') if end_date else None
    
    with col3:
        # 전략 선택
        strategy_options = [
            "MACD 전략", 
            "RSI 전략", 
            "볼린저 밴드 전략", 
            "이동평균 전략"
        ]
        selected_strategy = st.selectbox("매매 전략", strategy_options)
        
        # 초기 자본 설정
        initial_capital = st.number_input(
            "초기 자본 (원)",
            min_value=100000,
            max_value=10000000,
            value=1000000,
            step=100000,
            format="%d"
        )
    
    # 백테스팅 실행
    if st.button("🚀 백테스팅 실행", type="primary"):
        if not test_symbols:
            st.warning("테스트할 종목을 선택해주세요.")
            return
            
        with st.spinner("백테스팅을 실행하는 중..."):
            try:
                # 백테스팅 실행
                results = run_backtest_ui(
                    symbols=test_symbols,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    strategy_name=selected_strategy
                )
                
                if results:
                    st.success("✅ 백테스팅이 완료되었습니다!")
                    
                    # 결과 요약
                    st.subheader("📈 백테스팅 결과")
                    
                    results_col1, results_col2, results_col3, results_col4 = st.columns(4)
                    
                    with results_col1:
                        st.metric(
                            "총 수익률", 
                            f"{results['total_return']:.2%}",
                            delta=f"{results['total_return']:.2%}"
                        )
                    with results_col2:
                        st.metric(
                            "샤프 비율", 
                            f"{results['sharpe_ratio']:.3f}",
                            delta="높을수록 좋음"
                        )
                    with results_col3:
                        st.metric(
                            "최대 낙폭", 
                            f"{results['max_drawdown']:.2%}",
                            delta="낮을수록 좋음"
                        )
                    with results_col4:
                        st.metric(
                            "승률", 
                            f"{results['win_rate']:.2%}",
                            delta=f"{results['winning_trades']}/{results['total_trades']} 승"
                        )
                    
                    # 상세 결과
                    col_left, col_right = st.columns(2)
                    
                    with col_left:
                        st.subheader("📊 거래 통계")
                        
                        stats_data = {
                            "총 거래 수": f"{results['total_trades']}회",
                            "승리 거래": f"{results['winning_trades']}회",
                            "패배 거래": f"{results['losing_trades']}회",
                            "평균 보유기간": f"{results['avg_holding_days']:.1f}일",
                            "최대 보유기간": f"{results['max_holding_days']}일",
                            "평균 거래당 수익률": f"{results['avg_return_per_trade']:.2%}",
                            "수수료 총액": f"{results['total_commission']:,.0f}원"
                        }
                        
                        for key, value in stats_data.items():
                            st.text(f"{key}: {value}")
                    
                    with col_right:
                        st.subheader("💰 수익률 분석")
                        
                        profit_data = {
                            "평균 승리 수익률": f"{results['avg_winning_return']:.2%}",
                            "평균 손실 수익률": f"{results['avg_losing_return']:.2%}",
                            "수익률 변동성": f"{results['volatility']:.2%}",
                            "최종 자산": f"{initial_capital * (1 + results['total_return']):,.0f}원"
                        }
                        
                        for key, value in profit_data.items():
                            st.text(f"{key}: {value}")
                    
                    # 자산 곡선 차트
                    if not results['equity_curve'].empty:
                        st.subheader("📈 자산 곡선")
                        
                        import plotly.graph_objects as go
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=results['equity_curve']['date'],
                            y=results['equity_curve']['total_value'],
                            mode='lines',
                            name='포트폴리오 가치',
                            line=dict(color='blue', width=2)
                        ))
                        
                        fig.update_layout(
                            title="포트폴리오 가치 변화",
                            xaxis_title="날짜",
                            yaxis_title="자산 가치 (원)",
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # 거래 내역
                    if not results['trades'].empty:
                        st.subheader("📋 거래 내역")
                        
                        trades_display = results['trades'].copy()
                        trades_display['entry_date'] = pd.to_datetime(trades_display['entry_date'], format='mixed', errors='coerce').dt.strftime('%Y-%m-%d')
                        trades_display['exit_date'] = pd.to_datetime(trades_display['exit_date'], format='mixed', errors='coerce').dt.strftime('%Y-%m-%d')
                        trades_display['return_pct'] = trades_display['return_pct'] * 100
                        trades_display['profit_loss'] = trades_display['profit_loss'].round(0)
                        
                        st.dataframe(
                            trades_display[['entry_date', 'exit_date', 'symbol', 'return_pct', 'profit_loss', 'holding_days']],
                            column_config={
                                'entry_date': '매수일',
                                'exit_date': '매도일', 
                                'symbol': '종목',
                                'return_pct': st.column_config.NumberColumn('수익률(%)', format="%.2f"),
                                'profit_loss': st.column_config.NumberColumn('손익(원)', format="%d"),
                                'holding_days': '보유일수'
                            },
                            use_container_width=True
                        )
                else:
                    st.error("❌ 백테스팅 실행에 실패했습니다.")
                    
            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {str(e)}")

def main():
    """메인 함수"""
    # 네비게이션
    st.sidebar.title("🧭 네비게이션")
    
    pages = {
        "🏠 대시보드": render_dashboard,
        "🎯 전략 분석": render_strategy_analysis,
        "⚙️ 매개변수 최적화": render_optimization,
        "📊 백테스팅": render_backtest
    }
    
    selected_page = st.sidebar.selectbox("페이지 선택", list(pages.keys()))
    
    # 시스템 정보
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 시스템 정보")
    
    # 데이터베이스 상태 확인
    db_path = PROJECT_ROOT / 'data' / 'trading.db'
    if db_path.exists():
        st.sidebar.success("✅ 데이터베이스 연결됨")
        
        # 데이터 개수 표시
        try:
            with sqlite3.connect(db_path) as conn:
                count = conn.execute("SELECT COUNT(*) FROM stock_data").fetchone()[0]
                st.sidebar.info(f"📊 데이터 건수: {count:,}")
        except:
            pass
    else:
        st.sidebar.error("❌ 데이터베이스 없음")
        st.sidebar.markdown("데이터를 먼저 업데이트하세요:")
        st.sidebar.code("python src/main.py update-data")
    
    # TA-Lib 설치 상태 확인
    try:
        import talib
        st.sidebar.success("✅ TA-Lib 설치됨")
    except ImportError:
        st.sidebar.error("❌ TA-Lib 미설치")
        st.sidebar.markdown("TA-Lib을 설치하세요:")
        st.sidebar.code("pip install TA-Lib")
    
    # 선택된 페이지 렌더링
    pages[selected_page]()
    
    # 푸터
    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; color: #666; font-size: 0.8em;">'
        '© 2024 TA-Lib 스윙 트레이딩 시스템 | Made with ❤️ using Streamlit'
        '</p>',
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main() 
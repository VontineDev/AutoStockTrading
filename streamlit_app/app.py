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

@st.cache_data
def get_available_symbols_for_backtest():
    """백테스팅용 종목 목록 조회 (데이터가 있는 종목만)"""
    db_path = PROJECT_ROOT / 'data' / 'trading.db'
    
    if not db_path.exists():
        return pd.DataFrame()
    
    try:
        with sqlite3.connect(db_path) as conn:
            # 실제 데이터가 있는 종목만 조회
            query = """
            SELECT DISTINCT si.symbol, si.name, si.market,
                   COUNT(sd.date) as data_count,
                   MAX(sd.date) as latest_date,
                   MIN(sd.date) as earliest_date
            FROM stock_info si
            INNER JOIN stock_data sd ON si.symbol = sd.symbol
            GROUP BY si.symbol, si.name, si.market
            HAVING COUNT(sd.date) >= 30  -- 최소 30일 데이터가 있는 종목만
            ORDER BY data_count DESC, si.symbol
            """
            df = pd.read_sql_query(query, conn)
            
            # 추가 정보 포맷팅
            if not df.empty:
                df['display_name'] = df.apply(
                    lambda row: f"{row['symbol']} ({row['name']}) - {row['data_count']}일", 
                    axis=1
                )
            
            return df
    except Exception as e:
        st.error(f"종목 정보 조회 실패: {e}")
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
        
        from src.strategies.macd_strategy import MACDStrategy
        from src.strategies.rsi_strategy import RSIStrategy
        from src.strategies.bollinger_band_strategy import BollingerBandStrategy
        from src.strategies.moving_average_strategy import MovingAverageStrategy
        from src.trading.backtest import BacktestEngine, BacktestConfig
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
    
    st.markdown("""
    📊 **전략 성과 분석 및 비교**  
    TA-Lib 기반 매매 전략들의 성과를 분석하고 비교합니다.
    
    📋 **분석 모드 안내:**
    - **📈 단일 전략 분석**: 하나의 전략을 상세 분석
    - **⚖️ 전략 비교**: 여러 전략의 성과 비교
    - **🎯 신호 분석**: 매매 신호의 품질과 타이밍 분석  
    - **📊 매개변수 최적화**: 전략의 최적 매개변수 탐색 (시간 소요)
    """)
    
    # 사이드바 설정
    st.sidebar.markdown("### 🔧 분석 설정")
    
    # 분석 모드 선택
    analysis_mode = st.sidebar.radio(
        "분석 모드:",
        ["📈 단일 전략 분석", "⚖️ 전략 비교", "🎯 신호 분석", "📊 매개변수 최적화"]
    )
    
    # 전략 선택
    available_strategies = {
        "MACD 전략": "MACDStrategy",
        "RSI 전략": "RSIStrategy", 
        "볼린저 밴드 전략": "BollingerBandStrategy",
        "이동평균 전략": "MovingAverageStrategy"
    }
    
    # 종목 선택
    symbols_df = get_available_symbols_for_backtest()
    if not symbols_df.empty:
        selected_symbol = st.sidebar.selectbox(
            "분석 종목:",
            symbols_df['symbol'].tolist(),
            format_func=lambda x: f"{x} ({symbols_df[symbols_df['symbol']==x]['name'].iloc[0]})"
        )
    else:
        st.error("분석할 데이터가 없습니다. 먼저 데이터를 수집하세요.")
        return
    
    # 분석 기간
    analysis_period = st.sidebar.selectbox(
        "분석 기간:",
        ["1개월", "3개월", "6개월", "1년", "2년"],
        index=2
    )
    
    period_map = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "2년": 730}
    days = period_map[analysis_period]
    
    if analysis_mode == "📈 단일 전략 분석":
        render_single_strategy_analysis(available_strategies, selected_symbol, days)
    elif analysis_mode == "⚖️ 전략 비교":
        render_strategy_comparison(available_strategies, selected_symbol, days)
    elif analysis_mode == "🎯 신호 분석":
        render_signal_analysis(available_strategies, selected_symbol, days)
    elif analysis_mode == "📊 매개변수 최적화":
        render_parameter_optimization(available_strategies, selected_symbol, days)

def render_single_strategy_analysis(strategies: dict, symbol: str, days: int):
    """단일 전략 분석"""
    st.subheader("📈 단일 전략 분석")
    
    selected_strategy = st.selectbox("분석할 전략 선택:", list(strategies.keys()))
    
    # 데이터 로드
    data = load_symbol_data_for_analysis(symbol, days)
    if data is None:
        st.error("데이터를 로드할 수 없습니다.")
        return
    
    try:
        # 전략 실행
        strategy_instance = create_strategy_instance(strategies[selected_strategy])
        signals = strategy_instance.run_strategy(data, symbol)
        data_with_indicators = strategy_instance.calculate_indicators(data)
        
        # 성과 분석
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 전략 성과")
            if signals:
                performance = analyze_strategy_performance(signals, data)
                
                # 주요 지표 표시
                metrics_col1, metrics_col2 = st.columns(2)
                with metrics_col1:
                    st.metric("총 신호 수", len(signals))
                    st.metric("매수 신호", len([s for s in signals if s.signal_type == "BUY"]))
                    st.metric("매도 신호", len([s for s in signals if s.signal_type == "SELL"]))
                
                with metrics_col2:
                    avg_confidence = np.mean([s.confidence for s in signals])
                    st.metric("평균 신뢰도", f"{avg_confidence:.2f}")
                    st.metric("고신뢰 신호 비율", 
                             f"{len([s for s in signals if s.confidence > 0.7]) / len(signals) * 100:.1f}%")
                
                # 상세 성과 표시
                if performance:
                    st.markdown("**📈 수익률 분석**")
                    perf_data = {
                        "총 수익률": f"{performance.get('total_return', 0):.2%}",
                        "평균 수익률": f"{performance.get('avg_return', 0):.2%}",
                        "승률": f"{performance.get('win_rate', 0):.2%}",
                        "샤프 비율": f"{performance.get('sharpe_ratio', 0):.3f}",
                        "최대 낙폭": f"{performance.get('max_drawdown', 0):.2%}"
                    }
                    
                    for key, value in perf_data.items():
                        st.text(f"{key}: {value}")
            else:
                st.warning("분석 기간 동안 신호가 생성되지 않았습니다.")
        
        with col2:
            st.markdown("#### 🎯 신호 분포")
            if signals:
                # 신호 타입별 분포
                signal_types = [s.signal_type for s in signals]
                signal_counts = pd.Series(signal_types).value_counts()
                
                import plotly.express as px
                fig_pie = px.pie(
                    values=signal_counts.values,
                    names=signal_counts.index,
                    title="신호 타입별 분포"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # 신뢰도 분포
                confidences = [s.confidence for s in signals]
                fig_hist = px.histogram(
                    x=confidences,
                    nbins=10,
                    title="신호 신뢰도 분포",
                    labels={'x': '신뢰도', 'y': '빈도'}
                )
                st.plotly_chart(fig_hist, use_container_width=True)
        
        # 차트 시각화
        st.markdown("#### 📈 가격 차트 및 신호")
        render_strategy_chart(data_with_indicators, signals, selected_strategy)
        
        # 신호 상세 내역
        if signals:
            st.markdown("#### 📋 신호 상세 내역")
            render_signals_table(signals)
            
    except Exception as e:
        st.error(f"전략 분석 중 오류 발생: {e}")

def render_strategy_comparison(strategies: dict, symbol: str, days: int):
    """전략 비교 분석"""
    st.subheader("⚖️ 전략 비교 분석")
    
    # 비교할 전략들 선택
    selected_strategies = st.multiselect(
        "비교할 전략들을 선택하세요:",
        list(strategies.keys()),
        default=list(strategies.keys())[:2]
    )
    
    if len(selected_strategies) < 2:
        st.warning("최소 2개 전략을 선택해주세요.")
        return
    
    # 데이터 로드
    data = load_symbol_data_for_analysis(symbol, days)
    if data is None:
        st.error("데이터를 로드할 수 없습니다.")
        return
    
    # 각 전략 실행 및 결과 수집
    strategy_results = {}
    
    with st.spinner("전략들을 실행하고 있습니다..."):
        for strategy_name in selected_strategies:
            try:
                strategy_instance = create_strategy_instance(strategies[strategy_name])
                signals = strategy_instance.run_strategy(data, symbol)
                performance = analyze_strategy_performance(signals, data)
                
                strategy_results[strategy_name] = {
                    'signals': signals,
                    'performance': performance,
                    'signal_count': len(signals)
                }
            except Exception as e:
                st.warning(f"{strategy_name} 실행 중 오류: {e}")
    
    if not strategy_results:
        st.error("실행 가능한 전략이 없습니다.")
        return
    
    # 비교 결과 표시
    st.markdown("#### 📊 전략별 성과 비교")
    
    # 성과 비교 테이블
    comparison_data = []
    for strategy_name, result in strategy_results.items():
        perf = result['performance'] or {}
        comparison_data.append({
            '전략': strategy_name,
            '신호 수': result['signal_count'],
            '총 수익률': f"{perf.get('total_return', 0):.2%}",
            '승률': f"{perf.get('win_rate', 0):.2%}",
            '샤프 비율': f"{perf.get('sharpe_ratio', 0):.3f}",
            '최대 낙폭': f"{perf.get('max_drawdown', 0):.2%}",
            '평균 신뢰도': f"{np.mean([s.confidence for s in result['signals']]) if result['signals'] else 0:.2f}"
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True)
    
    # 시각화
    col1, col2 = st.columns(2)
    
    with col1:
        # 수익률 비교 차트
        if comparison_data:
            returns_data = [float(row['총 수익률'].rstrip('%')) for row in comparison_data]
            strategy_names = [row['전략'] for row in comparison_data]
            
            fig_bar = px.bar(
                x=strategy_names,
                y=returns_data,
                title="전략별 총 수익률 비교",
                labels={'x': '전략', 'y': '수익률 (%)'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        # 신호 수 비교
        signal_counts = [result['signal_count'] for result in strategy_results.values()]
        
        fig_signals = px.bar(
            x=list(strategy_results.keys()),
            y=signal_counts,
            title="전략별 신호 생성 수",
            labels={'x': '전략', 'y': '신호 수'}
        )
        st.plotly_chart(fig_signals, use_container_width=True)

def render_signal_analysis(strategies: dict, symbol: str, days: int):
    """신호 분석"""
    st.subheader("🎯 신호 분석")
    
    selected_strategy = st.selectbox("분석할 전략:", list(strategies.keys()))
    
    # 데이터 로드 및 전략 실행
    data = load_symbol_data_for_analysis(symbol, days)
    if data is None:
        st.error("데이터를 로드할 수 없습니다.")
        return
    
    try:
        strategy_instance = create_strategy_instance(strategies[selected_strategy])
        signals = strategy_instance.run_strategy(data, symbol)
        
        if not signals:
            st.warning("분석 기간 동안 신호가 생성되지 않았습니다.")
            return
        
        # 신호 시계열 분석
        st.markdown("#### 📅 신호 발생 패턴")
        
        # 월별 신호 분포
        signal_dates = [s.timestamp for s in signals]
        signal_df = pd.DataFrame({
            'date': signal_dates,
            'type': [s.signal_type for s in signals],
            'confidence': [s.confidence for s in signals]
        })
        
        signal_df['month'] = signal_df['date'].dt.to_period('M')
        monthly_signals = signal_df.groupby(['month', 'type']).size().unstack(fill_value=0)
        
        fig_monthly = px.bar(
            monthly_signals,
            title="월별 신호 발생 현황",
            labels={'value': '신호 수', 'index': '월'}
        )
        st.plotly_chart(fig_monthly, use_container_width=True)
        
        # 신호 신뢰도 분석
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🎯 신뢰도별 성과 분석")
            
            # 신뢰도 구간별 분석
            high_conf_signals = [s for s in signals if s.confidence > 0.7]
            medium_conf_signals = [s for s in signals if 0.4 <= s.confidence <= 0.7]
            low_conf_signals = [s for s in signals if s.confidence < 0.4]
            
            conf_analysis = {
                '고신뢰도 (>0.7)': len(high_conf_signals),
                '중신뢰도 (0.4-0.7)': len(medium_conf_signals),
                '저신뢰도 (<0.4)': len(low_conf_signals)
            }
            
            for level, count in conf_analysis.items():
                st.metric(level, f"{count}개", f"{count/len(signals)*100:.1f}%")
        
        with col2:
            st.markdown("#### 📊 신호 발생 이유 분석")
            
            # 신호 발생 이유별 분석
            reasons = [s.reason for s in signals]
            reason_counts = pd.Series(reasons).value_counts().head(5)
            
            if not reason_counts.empty:
                fig_reasons = px.pie(
                    values=reason_counts.values,
                    names=reason_counts.index,
                    title="주요 신호 발생 이유"
                )
                st.plotly_chart(fig_reasons, use_container_width=True)
        
    except Exception as e:
        st.error(f"신호 분석 중 오류 발생: {e}")

def render_parameter_optimization(strategies: dict, symbol: str, days: int):
    """매개변수 최적화"""
    st.subheader("📊 매개변수 최적화")
    
    st.markdown("""
    🎯 **전략 매개변수 최적화**  
    선택한 전략의 최적 매개변수를 찾아 성과를 극대화합니다.
    """)
    
    selected_strategy = st.selectbox("최적화할 전략:", list(strategies.keys()))
    
    st.info("⚠️ 매개변수 최적화는 시간이 오래 걸릴 수 있습니다. 간단한 범위로 시작하는 것을 권장합니다.")
    
    # 현재 선택된 종목과 기간 정보 표시
    st.markdown(f"**분석 대상:** {symbol} | **기간:** {days}일")
    
    # 전략별 매개변수 설정
    if selected_strategy == "MACD 전략":
        render_macd_optimization(symbol, days)
    elif selected_strategy == "RSI 전략":
        render_rsi_optimization(symbol, days)
    else:
        st.warning(f"{selected_strategy}의 매개변수 최적화는 아직 지원되지 않습니다.")

def render_macd_optimization(symbol: str, days: int):
    """MACD 전략 매개변수 최적화"""
    st.markdown("#### ⚙️ MACD 매개변수 최적화")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fast_range = st.slider("Fast Period 범위", 5, 20, (8, 15))
    with col2:
        slow_range = st.slider("Slow Period 범위", 20, 40, (22, 30))
    with col3:
        signal_range = st.slider("Signal Period 범위", 5, 15, (7, 11))
    
    if st.button("🚀 최적화 실행"):
        with st.spinner("매개변수 최적화를 실행하고 있습니다..."):
            results = run_macd_optimization(symbol, days, fast_range, slow_range, signal_range)
            
            if results:
                st.success("✅ 최적화 완료!")
                
                # 최적 매개변수 표시
                best_params = results['best_params']
                best_performance = results['best_performance']
                
                st.markdown("#### 🏆 최적 매개변수")
                opt_col1, opt_col2, opt_col3, opt_col4 = st.columns(4)
                
                with opt_col1:
                    st.metric("Fast Period", best_params['fast'])
                with opt_col2:
                    st.metric("Slow Period", best_params['slow'])
                with opt_col3:
                    st.metric("Signal Period", best_params['signal'])
                with opt_col4:
                    st.metric("예상 수익률", f"{best_performance:.2%}")
                
                # 최적화 결과 히트맵
                if 'heatmap_data' in results:
                    st.markdown("#### 📊 매개변수별 성과 히트맵")
                    fig_heatmap = px.imshow(
                        results['heatmap_data'],
                        title="Fast vs Slow Period 성과 매트릭스",
                        labels={'x': 'Slow Period', 'y': 'Fast Period', 'color': '수익률'}
                    )
                    st.plotly_chart(fig_heatmap, use_container_width=True)

def render_rsi_optimization(symbol: str, days: int):
    """RSI 전략 매개변수 최적화"""
    st.markdown("#### ⚙️ RSI 매개변수 최적화")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        period_range = st.slider("RSI Period 범위", 10, 25, (12, 16))
    with col2:
        oversold_range = st.slider("과매도 임계값 범위", 20, 40, (25, 35))
    with col3:
        overbought_range = st.slider("과매수 임계값 범위", 60, 80, (65, 75))
    
    if st.button("🚀 RSI 최적화 실행"):
        st.info("RSI 최적화 기능은 개발 중입니다.")

# 헬퍼 함수들
def load_symbol_data_for_analysis(symbol: str, days: int) -> pd.DataFrame:
    """분석용 종목 데이터 로드"""
    try:
        db_path = PROJECT_ROOT / 'data' / 'trading.db'
        
        with sqlite3.connect(db_path) as conn:
            query = """
            SELECT date, open, high, low, close, volume
            FROM stock_data 
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(symbol, days))
            
            if df.empty:
                return None
            
            df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
            df = df.sort_values('date').reset_index(drop=True)
            return df
            
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None

def create_strategy_instance(strategy_class_name: str):
    """전략 인스턴스 생성"""
    try:
        import sys
        sys.path.append(str(PROJECT_ROOT / 'src'))
        
        if strategy_class_name == "MACDStrategy":
            from src.strategies.macd_strategy import MACDStrategy
            return MACDStrategy()
        elif strategy_class_name == "RSIStrategy":
            from src.strategies.rsi_strategy import RSIStrategy
            return RSIStrategy()
        elif strategy_class_name == "BollingerBandStrategy":
            from src.strategies.bollinger_band_strategy import BollingerBandStrategy
            return BollingerBandStrategy()
        elif strategy_class_name == "MovingAverageStrategy":
            from src.strategies.moving_average_strategy import MovingAverageStrategy
            return MovingAverageStrategy()
        else:
            raise ValueError(f"지원되지 않는 전략: {strategy_class_name}")
            
    except Exception as e:
        st.error(f"전략 인스턴스 생성 실패: {e}")
        raise

def analyze_strategy_performance(signals, data):
    """전략 성과 분석"""
    if not signals:
        return None
    
    try:
        # 간단한 매수-매도 수익률 계산
        buy_signals = [s for s in signals if s.signal_type == "BUY"]
        sell_signals = [s for s in signals if s.signal_type == "SELL"]
        
        if len(buy_signals) == 0 or len(sell_signals) == 0:
            return {
                'total_return': 0,
                'avg_return': 0,
                'win_rate': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
        
        # 매수-매도 페어링 및 수익률 계산
        returns = []
        for buy_signal in buy_signals:
            # 매수 후 첫 번째 매도 신호 찾기
            next_sells = [s for s in sell_signals if s.timestamp > buy_signal.timestamp]
            if next_sells:
                sell_signal = min(next_sells, key=lambda x: x.timestamp)
                ret = (sell_signal.price - buy_signal.price) / buy_signal.price
                returns.append(ret)
        
        if not returns:
            return None
        
        returns_series = pd.Series(returns)
        
        return {
            'total_return': returns_series.sum(),
            'avg_return': returns_series.mean(),
            'win_rate': (returns_series > 0).mean(),
            'sharpe_ratio': returns_series.mean() / returns_series.std() if returns_series.std() > 0 else 0,
            'max_drawdown': returns_series.cumsum().expanding().max().subtract(returns_series.cumsum()).max()
        }
        
    except Exception:
        return None

def render_strategy_chart(data_with_indicators, signals, strategy_name):
    """전략 차트 렌더링"""
    try:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=('가격 차트 & 신호', '기술적 지표'),
            row_heights=[0.7, 0.3]
        )
        
        # 가격 차트
        fig.add_trace(
            go.Candlestick(
                x=data_with_indicators.index,
                open=data_with_indicators['open'],
                high=data_with_indicators['high'],
                low=data_with_indicators['low'],
                close=data_with_indicators['close'],
                name="Price"
            ),
            row=1, col=1
        )
        
        # 매매 신호 표시
        buy_signals = [s for s in signals if s.signal_type == "BUY"]
        sell_signals = [s for s in signals if s.signal_type == "SELL"]
        
        if buy_signals:
            buy_dates = [s.timestamp for s in buy_signals]
            buy_prices = [s.price for s in buy_signals]
            fig.add_trace(
                go.Scatter(
                    x=buy_dates,
                    y=buy_prices,
                    mode='markers',
                    marker=dict(symbol='triangle-up', size=12, color='green'),
                    name='Buy Signal'
                ),
                row=1, col=1
            )
        
        if sell_signals:
            sell_dates = [s.timestamp for s in sell_signals]
            sell_prices = [s.price for s in sell_signals]
            fig.add_trace(
                go.Scatter(
                    x=sell_dates,
                    y=sell_prices,
                    mode='markers',
                    marker=dict(symbol='triangle-down', size=12, color='red'),
                    name='Sell Signal'
                ),
                row=1, col=1
            )
        
        # 전략별 지표 추가
        if strategy_name == "MACD 전략" and 'MACD' in data_with_indicators.columns:
            fig.add_trace(
                go.Scatter(
                    x=data_with_indicators.index,
                    y=data_with_indicators['MACD'],
                    name='MACD',
                    line=dict(color='blue')
                ),
                row=2, col=1
            )
            
            if 'MACD_signal' in data_with_indicators.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data_with_indicators.index,
                        y=data_with_indicators['MACD_signal'],
                        name='Signal',
                        line=dict(color='red')
                    ),
                    row=2, col=1
                )
        
        elif strategy_name == "RSI 전략" and 'RSI' in data_with_indicators.columns:
            fig.add_trace(
                go.Scatter(
                    x=data_with_indicators.index,
                    y=data_with_indicators['RSI'],
                    name='RSI',
                    line=dict(color='purple')
                ),
                row=2, col=1
            )
            # RSI 과매수/과매도 라인
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        fig.update_layout(
            title=f"{strategy_name} 분석 차트",
            xaxis_title="Date",
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"차트 렌더링 실패: {e}")

def render_signals_table(signals):
    """신호 테이블 렌더링"""
    if not signals:
        return
    
    # 신호를 DataFrame으로 변환
    signal_data = []
    for signal in signals[-20:]:  # 최근 20개만 표시
        signal_data.append({
            '날짜': signal.timestamp.strftime('%Y-%m-%d') if hasattr(signal.timestamp, 'strftime') else str(signal.timestamp),
            '신호': signal.signal_type,
            '가격': f"{signal.price:,.0f}",
            '신뢰도': f"{signal.confidence:.2f}",
            '발생 이유': signal.reason,
            '리스크': signal.risk_level
        })
    
    signals_df = pd.DataFrame(signal_data)
    
    # 신호 타입에 따른 색상 적용
    def color_signal_type(val):
        if val == 'BUY':
            return 'background-color: lightgreen'
        elif val == 'SELL':
            return 'background-color: lightcoral'
        return ''
    
    styled_df = signals_df.style.applymap(color_signal_type, subset=['신호'])
    st.dataframe(styled_df, use_container_width=True)

def run_macd_optimization(symbol: str, days: int, fast_range, slow_range, signal_range):
    """MACD 매개변수 최적화 실행"""
    try:
        data = load_symbol_data_for_analysis(symbol, days)
        if data is None:
            return None
        
        best_performance = -float('inf')
        best_params = {}
        results_matrix = []
        
        # 그리드 서치
        for fast in range(fast_range[0], fast_range[1] + 1):
            row = []
            for slow in range(slow_range[0], slow_range[1] + 1):
                if fast >= slow:  # fast는 slow보다 작아야 함
                    row.append(0)
                    continue
                
                for signal in range(signal_range[0], signal_range[1] + 1):
                    try:
                        # 커스텀 MACD 전략 생성
                        from src.strategies.macd_strategy import create_macd_strategy
                        strategy = create_macd_strategy(fast=fast, slow=slow, signal=signal)
                        
                        signals = strategy.run_strategy(data, symbol)
                        performance = analyze_strategy_performance(signals, data)
                        
                        if performance and performance['total_return'] > best_performance:
                            best_performance = performance['total_return']
                            best_params = {
                                'fast': fast,
                                'slow': slow,
                                'signal': signal
                            }
                        
                        row.append(performance['total_return'] if performance else 0)
                        
                    except Exception:
                        row.append(0)
            
            results_matrix.append(row)
        
        return {
            'best_params': best_params,
            'best_performance': best_performance,
            'heatmap_data': np.array(results_matrix)
        }
        
    except Exception as e:
        st.error(f"최적화 실행 중 오류: {e}")
        return None

def render_data_collection():
    """데이터 수집 페이지"""
    st.title("📥 데이터 수집")
    
    st.markdown("""
    📊 **주식 데이터 수집 및 관리**  \n    pykrx를 통한 국내 주식 데이터 수집 및 데이터베이스 관리\n    """)
    
    # 데이터 상태 확인
    db_path = PROJECT_ROOT / 'data' / 'trading.db'
    
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                # 전체 데이터 건수
                total_count = conn.execute("SELECT COUNT(*) FROM stock_data").fetchone()[0]
                
                # 종목 수
                symbol_count = conn.execute("SELECT COUNT(DISTINCT symbol) FROM stock_data").fetchone()[0]
                
                # 최신 데이터 날짜
                latest_date = conn.execute("SELECT MAX(date) FROM stock_data").fetchone()[0]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("총 데이터 건수", f"{total_count:,}")
                with col2:
                    st.metric("수집된 종목 수", f"{symbol_count:,}")
                with col3:
                    st.metric("최신 데이터", latest_date if latest_date else "없음")
                   
        except Exception as e:
            st.error(f"데이터베이스 오류: {e}")
    else:
        st.warning("데이터베이스가 없습니다.")
    
    st.markdown("---")
    
    # 데이터 업데이트 안내
    st.subheader("🔄 데이터 업데이트")
    st.markdown("""
    데이터를 업데이트하려면 터미널에서 다음 명령어를 실행하세요:
    """)
    st.code("python src/main.py update-data", language="bash")
    
    st.markdown("""
    **업데이트 옵션:**
    - `--symbols SYMBOL1,SYMBOL2`: 특정 종목만 업데이트
    - `--days N`: 최근 N일 데이터만 수집
    - `--force`: 기존 데이터 덮어쓰기
    """)
    
    # 수집된 데이터 미리보기
    if db_path.exists():
        st.subheader("📋 수집된 데이터 미리보기")
        try:
            with sqlite3.connect(db_path) as conn:
                # 최근 업데이트된 종목 10개 표시
                query = """
                SELECT si.symbol, si.name, si.market, 
                       COUNT(*) as data_count,
                       MAX(sd.date) as latest_date,
                       MIN(sd.date) as earliest_date
                FROM stock_info si
                JOIN stock_data sd ON si.symbol = sd.symbol
                GROUP BY si.symbol, si.name, si.market
                ORDER BY latest_date DESC
                LIMIT 10
                """
                df = pd.read_sql_query(query, conn)
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"데이터 조회 실패: {e}")



def render_backtest():
    """백테스팅 페이지"""
    st.title("📊 백테스팅")
    
    st.markdown("""
    📈 **전략 백테스팅**  
    매매 전략의 과거 성과를 실제 매매처럼 시뮬레이션하여 검증합니다.
    
    💡 **전략 분석 vs 백테스팅 차이:**
    - **전략 분석**: 신호 생성, 지표 분석, 매개변수 최적화 (분석 중심)
    - **백테스팅**: 실제 매매 시뮬레이션, 자본 관리, 수익률 계산 (실전 중심)
    """)
    
    # 백테스팅 설정
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("⚙️ 백테스팅 설정")
        
        # 종목 선택
        symbols_df = get_available_symbols_for_backtest()
        if not symbols_df.empty:
            selected_symbols = st.multiselect(
                "백테스팅 종목:",
                symbols_df['symbol'].tolist(),
                default=symbols_df['symbol'].head(3).tolist(),
                help="여러 종목을 선택할 수 있습니다"
            )
        else:
            st.warning("백테스팅할 수 있는 종목이 없습니다.")
            selected_symbols = []
        
        # 기간 설정
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
        
        # 전략 선택
        strategy = st.selectbox(
            "매매 전략:",
            ["MACD 전략", "RSI 전략", "볼린저 밴드 전략", "이동평균 전략"]
        )
        
        # 초기 자본
        initial_capital = st.number_input(
            "초기 자본 (원):",
            min_value=100000,
            max_value=100000000,
            value=1000000,
            step=100000
        )
        
        # 백테스팅 실행 버튼
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
                    # 결과 표시
                    st.success("✅ 백테스팅 완료!")
                    
                    # 핵심 지표
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
                   
                    # 상세 결과 표시
                    if 'detailed_results' in results:
                        st.subheader("📋 종목별 상세 결과")
                        detailed_df = pd.DataFrame(results['detailed_results'])
                        st.dataframe(detailed_df, use_container_width=True)
                   
                    # 거래 내역
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

def main():
    """메인 함수"""
    # 네비게이션
    st.sidebar.title("🧭 네비게이션")
    
    pages = {
        "🏠 대시보드": render_dashboard,
        "📥 데이터 수집": render_data_collection,
        "🎯 전략 분석": render_strategy_analysis,
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
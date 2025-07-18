"""
TA-Lib 스윙 트레이딩 자동매매 시스템 Streamlit 앱

pykrx + TA-Lib 기반의 100만원 규모 스윙 트레이딩 웹 인터페이스
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd

# 프로젝트 루트를 sys.path에 추가
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# PROJECT_ROOT 가져오기
from src.config_loader import get_project_root
PROJECT_ROOT = get_project_root()

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from src.data.stock_data_manager import StockDataManager

# 데이터베이스 경로 설정
DB_PATH = str(PROJECT_ROOT / "data" / "trading.db")

@st.cache_data
def get_data_manager():
    """StockDataManager 인스턴스를 반환합니다."""
    return StockDataManager(db_path=DB_PATH)

@st.cache_data
def load_stock_data(symbols: list, limit: int = 500) -> Dict[str, pd.DataFrame]:
    """주식 데이터 로드"""
    dm = get_data_manager()
    data = {}
    today = datetime.now()
    start_date = today - timedelta(days=limit * 1.5) # 데이터 여유있게 가져오기
    
    for symbol in symbols:
        df = dm.get_stock_data(symbol, start_date.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))
        if not df.empty:
            data[symbol] = df.tail(limit) # 마지막 limit 개수만큼만 사용
    return data





def calculate_ta_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    TA-Lib 지표 계산
    Args:
        df: OHLCV 데이터프레임
    Returns:
        지표가 추가된 DataFrame
    """
    try:
        import talib

        # 기본 지표들
        df["SMA_20"] = talib.SMA(df["close"], timeperiod=20)
        df["EMA_12"] = talib.EMA(df["close"], timeperiod=12)
        df["EMA_26"] = talib.EMA(df["close"], timeperiod=26)

        # MACD
        df["MACD"], df["MACD_signal"], df["MACD_hist"] = talib.MACD(df["close"])

        # RSI
        df["RSI"] = talib.RSI(df["close"], timeperiod=14)

        # 볼린저 밴드
        df["BB_upper"], df["BB_middle"], df["BB_lower"] = talib.BBANDS(df["close"])

        # ATR
        df["ATR"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)

        return df

    except ImportError:
        st.error("TA-Lib이 설치되지 않았습니다. 'pip install TA-Lib'로 설치해주세요.")
        return df
    except Exception as e:
        st.error(f"지표 계산 실패: {e}")
        return df


def run_backtest_ui(
    symbols: list,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_capital: float = 1000000,
    strategy_name: str = "MACD 전략",
) -> Optional[dict]:
    """
    Streamlit UI에서 백테스팅 실행
    """
    try:
        from src.strategies.macd_strategy import MACDStrategy
        from src.strategies.rsi_strategy import RSIStrategy
        from src.strategies.bollinger_band_strategy import BollingerBandStrategy
        from src.strategies.moving_average_strategy import MovingAverageStrategy
        from src.trading.backtest import BacktestEngine, BacktestConfig

        dm = get_data_manager()
        data = {}
        for symbol in symbols:
            df = dm.get_stock_data(symbol, start_date, end_date)
            if not df.empty:
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


def create_candlestick_chart(
    df: pd.DataFrame, symbol: str, indicators: Optional[list] = None
) -> Any:
    """
    캔들스틱 차트 생성
    Args:
        df: OHLCV 데이터프레임
        symbol: 종목명
        indicators: 추가 지표 리스트
    Returns:
        plotly Figure 객체
    """
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("가격", "MACD", "RSI"),
        row_width=[0.2, 0.1, 0.1],
    )

    # 캔들스틱
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=symbol,
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )

    # 이동평균선
    if "SMA_20" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["SMA_20"],
                name="SMA 20",
                line=dict(color="orange", width=1),
            ),
            row=1,
            col=1,
        )

    if "EMA_12" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["EMA_12"],
                name="EMA 12",
                line=dict(color="blue", width=1),
            ),
            row=1,
            col=1,
        )

    # 볼린저 밴드
    if all(col in df.columns for col in ["BB_upper", "BB_lower"]):
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["BB_upper"],
                name="BB Upper",
                line=dict(color="gray", width=1),
                opacity=0.3,
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["BB_lower"],
                name="BB Lower",
                line=dict(color="gray", width=1),
                fill="tonexty",
                opacity=0.1,
            ),
            row=1,
            col=1,
        )

    # MACD
    if all(col in df.columns for col in ["MACD", "MACD_signal", "MACD_hist"]):
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["MACD"],
                name="MACD",
                line=dict(color="blue", width=1),
            ),
            row=2,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["MACD_signal"],
                name="Signal",
                line=dict(color="red", width=1),
            ),
            row=2,
            col=1,
        )

        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["MACD_hist"],
                name="Histogram",
                marker_color="green",
                opacity=0.7,
            ),
            row=2,
            col=1,
        )

    # RSI
    if "RSI" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["RSI"],
                name="RSI",
                line=dict(color="purple", width=2),
            ),
            row=3,
            col=1,
        )

        # RSI 과매수/과매도 라인
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

    # 레이아웃 설정
    fig.update_layout(
        title=f"{symbol} 기술적 분석",
        xaxis_rangeslider_visible=False,
        height=800,
        showlegend=True,
    )

    return fig


from src.ui.dashboard import render_dashboard
from src.ui.data_collection import render_data_collection
from src.ui.backtest import render_backtest


def main() -> None:
    """
    Streamlit 앱의 메인 엔트리포인트 함수.
    """
    # 네비게이션
    pages = {
        "📊 대시보드": render_dashboard,
        "📥 데이터 수집": render_data_collection,
        "📊 백테스팅": render_backtest,
    }

    selected_page = st.sidebar.selectbox("페이지 선택", list(pages.keys()))

    # 시스템 정보
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 시스템 정보")

    # 데이터베이스 상태 확인
    db_path = PROJECT_ROOT / "data" / "trading.db"
    if db_path.exists():
        st.sidebar.success("✅ 데이터베이스 연결됨")
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
        "© 2024 TA-Lib 스윙 트레이딩 시스템 | Made with ❤️ using Streamlit"
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

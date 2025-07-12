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
from typing import Optional, Tuple, Dict, Any
from src.utils.constants import PROJECT_ROOT
from src.utils.logging_utils import setup_logging

setup_logging()

# 프로젝트 루트 경로 설정
sys.path.insert(0, str(PROJECT_ROOT))

# 페이지 설정
st.set_page_config(page_title="AutoStockTrading", layout="wide")

# 스타일 설정
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# --- Kiwoom API 연동 관련 import ---
sys.path.append(str(PROJECT_ROOT / "src"))
from src.api.auth import get_kiwoom_env, get_access_token
from src.api.kiwoom_client import KiwoomApiClient

# --- 항상 먼저 최신 환경정보를 가져온다 ---
kiwoom_env = get_kiwoom_env()


@st.cache_data(show_spinner=False)
def get_account_info_cached() -> Tuple[Optional[dict], str]:
    """
    키움 API를 통해 계좌 정보를 조회합니다.
    Returns:
        (계좌정보 dict 또는 None, 상태 메시지)
    """
    try:
        token = get_access_token(
            kiwoom_env["api_key"],
            kiwoom_env["api_secret"],
            base_url=kiwoom_env["base_url"],
        )
        if not token:
            return None, "토큰 발급 실패"
        client = KiwoomApiClient(kiwoom_env["api_key"], kiwoom_env["api_secret"])
        info = client.get_account_info(token)
        if info and info.get("return_code") == 0:
            return info, "성공"
        else:
            return None, (
                info.get("return_msg", "계좌정보 조회 실패")
                if info
                else "계좌정보 조회 실패"
            )
    except Exception as e:
        return None, str(e)


# --- 사이드바 최상단에 이름 추가 (중복 방지) ---
if "sidebar_title_shown" not in st.session_state:
    st.sidebar.markdown("**TA-Lib 스윙 트레이딩 설정 & 네비게이션**")
    st.sidebar.markdown("---")
    st.session_state["sidebar_title_shown"] = True

# --- 투자 환경 및 계좌정보 섹션 (간소화) ---
with st.sidebar:
    # 1. 프로젝트 타이틀
    st.markdown("## 📈 TA-Lib 스윙 트레이딩")
    st.markdown("---")

    # 2. 투자 환경/계좌정보
    st.markdown("#### 투자 환경")
    env_options = {"모의투자": True, "실전투자": False}
    kiwoom_env = get_kiwoom_env()
    selected_env = st.radio(
        "키움 투자 환경 선택",
        list(env_options.keys()),
        index=0 if kiwoom_env["env_type"] == "모의투자" else 1,
    )
    if (
        "USE_KIWOOM_MOCK" not in st.session_state
        or st.session_state["USE_KIWOOM_MOCK"] != env_options[selected_env]
    ):
        st.session_state["USE_KIWOOM_MOCK"] = env_options[selected_env]
        st.cache_data.clear()
        st.info("투자 환경이 변경되었습니다. 계좌정보가 새로고침됩니다.")

    account_info, account_status = get_account_info_cached()
    if account_info:
        st.success(f"계좌명: {account_info.get('acnt_nm', '-')}")
    st.markdown("---")

    # 4. 네비게이션(페이지 선택 등) - 필요시 여기에 추가


@st.cache_data
def load_config() -> Dict[str, Any]:
    """
    설정 파일(config.yaml) 로드
    Returns:
        설정 딕셔너리
    """
    config_path = PROJECT_ROOT / "config.yaml"
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    except Exception as e:
        st.error(f"설정 파일 로드 실패: {e}")

    return {"project": {"name": "TA-Lib 스윙 트레이딩", "version": "1.0.0"}}


@st.cache_data
def load_stock_data(symbols: list, limit: int = 500) -> Dict[str, pd.DataFrame]:
    """
    주식 데이터 로드
    Args:
        symbols: 종목 리스트
        limit: 데이터 개수
    Returns:
        {symbol: DataFrame} 딕셔너리
    """
    db_path = PROJECT_ROOT / "data" / "trading.db"

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
                    df["date"] = pd.to_datetime(
                        df["date"], format="mixed", errors="coerce"
                    )
                    df = df.sort_values("date").reset_index(drop=True)
                    data[symbol] = df

    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")

    return data


@st.cache_data
def get_symbol_info() -> pd.DataFrame:
    """
    종목 정보 조회
    Returns:
        종목 정보 DataFrame
    """
    db_path = PROJECT_ROOT / "data" / "trading.db"

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
def get_available_symbols_for_backtest() -> pd.DataFrame:
    """
    백테스팅용 종목 목록 조회 (데이터가 있는 종목만)
    Returns:
        종목 정보 DataFrame
    """
    db_path = PROJECT_ROOT / "data" / "trading.db"

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
                df["display_name"] = df.apply(
                    lambda row: f"{row['symbol']} ({row['name']}) - {row['data_count']}일",
                    axis=1,
                )

            return df
    except Exception as e:
        st.error(f"종목 정보 조회 실패: {e}")
        return pd.DataFrame()


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
    Args:
        symbols: 테스트할 종목 리스트
        start_date: 시작날짜 (YYYY-MM-DD)
        end_date: 종료날짜 (YYYY-MM-DD)
        initial_capital: 초기 자본
        strategy_name: 전략 이름
    Returns:
        백테스팅 결과 dict 또는 None
    """
    try:
        import sys

        sys.path.append(str(PROJECT_ROOT / "src"))

        from src.strategies.macd_strategy import MACDStrategy
        from src.strategies.rsi_strategy import RSIStrategy
        from src.strategies.bollinger_band_strategy import BollingerBandStrategy
        from src.strategies.moving_average_strategy import MovingAverageStrategy
        from src.trading.backtest import BacktestEngine, BacktestConfig
        import sqlite3

        # 데이터 로드
        db_path = PROJECT_ROOT / "data" / "trading.db"
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
                    df["date"] = pd.to_datetime(
                        df["date"], format="mixed", errors="coerce"
                    )
                    df = df.dropna(subset=["date"])  # 날짜 파싱 실패한 행 제거
                    df.set_index("date", inplace=True)
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

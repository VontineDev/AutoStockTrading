"""
데이터 수집 UI 모듈
- pykrx 데이터 수집, 미리보기 등
"""

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from src.utils.constants import PROJECT_ROOT
from src.data.database import DatabaseManager


def render_data_collection() -> None:
    """
    데이터 수집 페이지 UI 렌더링
    """
    st.title("📥 데이터 수집")
    st.markdown(
        """
    📊 **주식 데이터 수집 및 관리**  \n    pykrx를 통한 국내 주식 데이터 수집 및 데이터베이스 관리\n    """
    )
    db_path = PROJECT_ROOT / "data" / "trading.db"
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                total_count = conn.execute(
                    "SELECT COUNT(*) FROM stock_ohlcv"
                ).fetchone()[0]
                symbol_count = conn.execute(
                    "SELECT COUNT(DISTINCT symbol) FROM stock_ohlcv"
                ).fetchone()[0]
                latest_date = conn.execute(
                    "SELECT MAX(date) FROM stock_ohlcv"
                ).fetchone()[0]
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
    st.subheader("🔄 데이터 업데이트")
    st.markdown(
        """
    데이터를 업데이트하려면 터미널에서 다음 명령어를 실행하세요:
    """
    )
    st.code("python src/main.py update-data", language="bash")
    st.markdown(
        """
    **업데이트 옵션:**
    - `--symbols SYMBOL1,SYMBOL2`: 특정 종목만 업데이트
    - `--days N`: 최근 N일 데이터만 수집
    - `--force`: 기존 데이터 덮어쓰기
    """
    )
    if db_path.exists():
        st.subheader("📋 수집된 데이터 미리보기")
        try:
            with sqlite3.connect(db_path) as conn:
                query = """
                SELECT si.symbol, si.name, si.market, 
                       COUNT(*) as data_count,
                       MAX(so.date) as latest_date,
                       MIN(so.date) as earliest_date
                FROM stock_info si
                JOIN stock_ohlcv so ON si.symbol = so.symbol
                GROUP BY si.symbol, si.name, si.market
                ORDER BY latest_date DESC
                LIMIT 10
                """
                dm = DatabaseManager(db_path=str(db_path))
                df = dm.fetchdf(query)
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"데이터 조회 실패: {e}")

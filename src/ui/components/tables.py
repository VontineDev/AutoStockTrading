"""
테이블 UI 컴포넌트
데이터 테이블 렌더링 관련 컴포넌트
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
import logging


class TableComponent:
    """테이블 관련 UI 컴포넌트"""
    
    @staticmethod
    def render_dataframe(
        data: pd.DataFrame,
        title: Optional[str] = None,
        height: int = 400,
        use_container_width: bool = True
    ) -> None:
        """데이터프레임 테이블 렌더링"""
        try:
            if data.empty:
                st.warning("표시할 데이터가 없습니다.")
                return
            
            if title:
                st.subheader(title)
            
            st.dataframe(
                data,
                height=height,
                use_container_width=use_container_width
            )
            
        except Exception as e:
            logging.error(f"데이터프레임 렌더링 실패: {e}")
            st.error(f"테이블 렌더링 실패: {e}")
    
    @staticmethod
    def render_performance_table(
        metrics: Dict[str, Any],
        title: str = "성과 지표"
    ) -> None:
        """성과 지표 테이블 렌더링"""
        try:
            if not metrics:
                st.warning("표시할 성과 지표가 없습니다.")
                return
            
            if title:
                st.subheader(title)
            
            # 딕셔너리를 DataFrame으로 변환
            df = pd.DataFrame(list(metrics.items()))
            df.columns = ['지표', '값']
            
            # 값 포맷팅
            def format_value(value):
                if isinstance(value, (int, float)):
                    if abs(value) >= 1000000:
                        return f"{value/1000000:.2f}M"
                    elif abs(value) >= 1000:
                        return f"{value/1000:.2f}K"
                    else:
                        return f"{value:.2f}"
                return str(value)
            
            df['값'] = df['값'].apply(format_value)
            
            st.table(df)
            
        except Exception as e:
            logging.error(f"성과 테이블 렌더링 실패: {e}")
            st.error(f"성과 테이블 렌더링 실패: {e}")


class FormComponent:
    """폼 관련 UI 컴포넌트"""
    
    @staticmethod
    def render_search_form(key: str = "search") -> str:
        """검색 폼 렌더링"""
        try:
            search_query = st.text_input(
                "종목 검색",
                placeholder="종목코드 또는 종목명을 입력하세요",
                key=key
            )
            return search_query
            
        except Exception as e:
            logging.error(f"검색 폼 렌더링 실패: {e}")
            st.error(f"검색 폼 오류: {e}")
            return "" 
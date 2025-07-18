"""
폼 UI 컴포넌트
입력 폼 관련 컴포넌트
"""

import streamlit as st
from typing import Dict, Any
import logging


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
    
    @staticmethod
    def render_login_form(key: str = "login") -> Dict[str, Any]:
        """로그인 폼 렌더링"""
        try:
            with st.form(key=key):
                username = st.text_input("사용자명")
                password = st.text_input("비밀번호", type="password")
                submitted = st.form_submit_button("로그인")
                
                return {
                    'username': username,
                    'password': password,
                    'submitted': submitted
                }
                
        except Exception as e:
            logging.error(f"로그인 폼 렌더링 실패: {e}")
            st.error(f"로그인 폼 오류: {e}")
            return {}
    
    @staticmethod
    def render_add_stock_form(key: str = "add_stock") -> Dict[str, Any]:
        """종목 추가 폼 렌더링"""
        try:
            with st.form(key=key):
                st.subheader("종목 추가")
                
                stock_code = st.text_input(
                    "종목코드",
                    placeholder="예: 005930",
                    help="6자리 종목코드를 입력하세요"
                )
                
                submitted = st.form_submit_button("종목 추가")
                
                return {
                    'stock_code': stock_code,
                    'submitted': submitted
                }
                
        except Exception as e:
            logging.error(f"종목 추가 폼 렌더링 실패: {e}")
            st.error(f"종목 추가 폼 오류: {e}")
            return {} 
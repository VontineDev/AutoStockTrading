"""
위젯 UI 컴포넌트
선택기, 입력 폼, 디스플레이 등의 위젯 컴포넌트
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging


class WidgetComponent:
    """위젯 관련 UI 컴포넌트"""
    
    @staticmethod
    def render_stock_selector(
        available_symbols: pd.DataFrame,
        key: str = "stock_selector",
        multi: bool = False,
        max_selections: int = 5
    ) -> Any:
        """종목 선택 위젯"""
        try:
            if available_symbols.empty:
                st.warning("사용 가능한 종목이 없습니다.")
                return None if not multi else []
            
            # 종목 목록 준비
            if 'display_name' in available_symbols.columns:
                options = available_symbols['display_name'].tolist()
                symbols = available_symbols['symbol'].tolist()
                format_func = lambda x: x  # 이미 포맷된 이름 사용
            else:
                options = available_symbols['symbol'].tolist()
                symbols = options
                format_func = lambda x: f"{x}"
            
            if multi:
                selected = st.multiselect(
                    "종목 선택",
                    options=options,
                    key=key,
                    max_selections=max_selections,
                    help=f"최대 {max_selections}개 종목까지 선택 가능"
                )
                
                # 실제 심볼 코드 반환
                if selected and 'display_name' in available_symbols.columns:
                    return [symbols[options.index(item)] for item in selected]
                return selected
            else:
                selected = st.selectbox(
                    "종목 선택",
                    options=options,
                    key=key,
                    format_func=format_func
                )
                
                # 실제 심볼 코드 반환
                if selected and 'display_name' in available_symbols.columns:
                    return symbols[options.index(selected)]
                return selected
            
        except Exception as e:
            logging.error(f"종목 선택기 렌더링 실패: {e}")
            st.error(f"종목 선택기 오류: {e}")
            return None if not multi else []
    
    @staticmethod
    def render_date_range_selector(
        key: str = "date_range",
        default_days: int = 365,
        max_days: int = 1000
    ) -> Tuple[str, str]:
        """날짜 범위 선택 위젯"""
        try:
            col1, col2 = st.columns(2)
            
            # 기본 날짜 설정
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=default_days)
            
            with col1:
                start = st.date_input(
                    "시작 날짜",
                    value=start_date,
                    max_value=end_date,
                    key=f"{key}_start"
                )
            
            with col2:
                end = st.date_input(
                    "종료 날짜",
                    value=end_date,
                    min_value=start,
                    max_value=end_date,
                    key=f"{key}_end"
                )
            
            # 날짜 차이 체크
            date_diff = (end - start).days
            if date_diff > max_days:
                st.warning(f"선택한 기간이 너무 깁니다. 최대 {max_days}일까지 가능합니다.")
                end = start + timedelta(days=max_days)
            
            return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
            
        except Exception as e:
            logging.error(f"날짜 범위 선택기 렌더링 실패: {e}")
            st.error(f"날짜 선택기 오류: {e}")
            return "", ""
    
    @staticmethod
    def render_strategy_selector(
        strategies: List[str],
        key: str = "strategy_selector"
    ) -> str:
        """전략 선택 위젯"""
        try:
            if not strategies:
                st.warning("사용 가능한 전략이 없습니다.")
                return ""
            
            selected_strategy = st.selectbox(
                "매매 전략 선택",
                options=strategies,
                key=key,
                help="백테스팅에 사용할 매매 전략을 선택하세요"
            )
            
            return selected_strategy
            
        except Exception as e:
            logging.error(f"전략 선택기 렌더링 실패: {e}")
            st.error(f"전략 선택기 오류: {e}")
            return ""
    
    @staticmethod
    def render_parameter_inputs(
        strategy_info: Dict[str, Any],
        key_prefix: str = "param"
    ) -> Dict[str, Any]:
        """매개변수 입력 위젯"""
        try:
            parameters = {}
            
            if 'parameters' not in strategy_info:
                return parameters
            
            st.subheader("전략 매개변수")
            
            param_config = strategy_info['parameters']
            
            for param_name, param_info in param_config.items():
                param_type = param_info.get('type', 'float')
                default_value = param_info.get('default', 0)
                min_value = param_info.get('min')
                max_value = param_info.get('max')
                
                key = f"{key_prefix}_{param_name}"
                
                if param_type == 'int':
                    value = st.number_input(
                        param_name,
                        value=int(default_value),
                        min_value=int(min_value) if min_value is not None else None,
                        max_value=int(max_value) if max_value is not None else None,
                        step=1,
                        key=key
                    )
                elif param_type == 'float':
                    value = st.number_input(
                        param_name,
                        value=float(default_value),
                        min_value=float(min_value) if min_value is not None else None,
                        max_value=float(max_value) if max_value is not None else None,
                        step=0.01,
                        key=key
                    )
                else:
                    value = st.text_input(
                        param_name,
                        value=str(default_value),
                        key=key
                    )
                
                parameters[param_name] = value
            
            return parameters
            
        except Exception as e:
            logging.error(f"매개변수 입력 위젯 렌더링 실패: {e}")
            st.error(f"매개변수 입력 오류: {e}")
            return {}
    
    @staticmethod
    def render_portfolio_settings(
        key_prefix: str = "portfolio"
    ) -> Dict[str, Any]:
        """포트폴리오 설정 위젯"""
        try:
            st.subheader("포트폴리오 설정")
            
            col1, col2 = st.columns(2)
            
            with col1:
                initial_capital = st.number_input(
                    "초기 자본 (원)",
                    value=1000000,
                    min_value=100000,
                    max_value=10000000,
                    step=100000,
                    key=f"{key_prefix}_capital"
                )
                
                max_positions = st.number_input(
                    "최대 포지션 수",
                    value=5,
                    min_value=1,
                    max_value=10,
                    step=1,
                    key=f"{key_prefix}_positions"
                )
            
            with col2:
                commission_rate = st.number_input(
                    "수수료율 (%)",
                    value=0.015,
                    min_value=0.0,
                    max_value=1.0,
                    step=0.001,
                    format="%.3f",
                    key=f"{key_prefix}_commission"
                )
                
                risk_per_trade = st.number_input(
                    "거래당 리스크 (%)",
                    value=2.0,
                    min_value=0.5,
                    max_value=10.0,
                    step=0.5,
                    key=f"{key_prefix}_risk"
                )
            
            return {
                'initial_capital': initial_capital,
                'max_positions': max_positions,
                'commission_rate': commission_rate / 100,  # 퍼센트를 소수로 변환
                'risk_per_trade': risk_per_trade / 100
            }
            
        except Exception as e:
            logging.error(f"포트폴리오 설정 위젯 렌더링 실패: {e}")
            st.error(f"포트폴리오 설정 오류: {e}")
            return {}
    
    @staticmethod
    def render_metric_cards(
        metrics: Dict[str, Any],
        title: str = "성과 지표"
    ) -> None:
        """지표 카드 위젯"""
        try:
            if not metrics:
                st.warning("표시할 지표가 없습니다.")
                return
            
            st.subheader(title)
            
            # 4열로 지표 표시
            num_cols = 4
            metric_items = list(metrics.items())
            
            for i in range(0, len(metric_items), num_cols):
                cols = st.columns(num_cols)
                
                for j in range(num_cols):
                    if i + j < len(metric_items):
                        metric_name, metric_value = metric_items[i + j]
                        
                        with cols[j]:
                            # 값 포맷팅
                            if isinstance(metric_value, (int, float)):
                                if metric_name.endswith('(%)'):
                                    formatted_value = f"{metric_value:.2f}%"
                                    delta_color = "normal" if metric_value >= 0 else "inverse"
                                elif metric_name.endswith('(원)'):
                                    formatted_value = f"{metric_value:,.0f}원"
                                    delta_color = "normal"
                                else:
                                    formatted_value = f"{metric_value:,.2f}"
                                    delta_color = "normal"
                            else:
                                formatted_value = str(metric_value)
                                delta_color = "normal"
                            
                            st.metric(
                                label=metric_name,
                                value=formatted_value
                            )
            
        except Exception as e:
            logging.error(f"지표 카드 렌더링 실패: {e}")
            st.error(f"지표 카드 오류: {e}")
    
    @staticmethod
    def render_progress_indicator(
        current: int,
        total: int,
        text: str = "진행률"
    ) -> None:
        """진행률 표시 위젯"""
        try:
            if total <= 0:
                return
            
            progress = min(current / total, 1.0)
            st.progress(progress, text=f"{text}: {current}/{total} ({progress*100:.1f}%)")
            
        except Exception as e:
            logging.error(f"진행률 표시 실패: {e}")
            st.error(f"진행률 표시 오류: {e}")
    
    @staticmethod
    def render_info_box(
        message: str,
        box_type: str = "info"
    ) -> None:
        """정보 박스 위젯"""
        try:
            if box_type == "info":
                st.info(message)
            elif box_type == "success":
                st.success(message)
            elif box_type == "warning":
                st.warning(message)
            elif box_type == "error":
                st.error(message)
            else:
                st.write(message)
                
        except Exception as e:
            logging.error(f"정보 박스 렌더링 실패: {e}")
            st.error(f"정보 박스 오류: {e}") 
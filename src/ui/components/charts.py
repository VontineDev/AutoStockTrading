"""
차트 UI 컴포넌트
주식 차트, 지표 차트 등을 렌더링하는 컴포넌트
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Optional, Dict, List, Any
import logging


class ChartComponent:
    """차트 관련 UI 컴포넌트"""
    
    @staticmethod
    def render_candlestick_chart(
        data: pd.DataFrame,
        title: str = "주식 차트",
        height: int = 600,
        volume: bool = True,
        indicators: Optional[Dict[str, pd.Series]] = None
    ) -> None:
        """캔들스틱 차트 렌더링"""
        try:
            if data.empty:
                st.warning("표시할 데이터가 없습니다.")
                return
            
            # 서브플롯 생성 (볼륨 차트 포함)
            if volume:
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.03,
                    subplot_titles=(title, '거래량'),
                    row_width=[0.7, 0.3]
                )
            else:
                fig = go.Figure()
            
            # 캔들스틱 차트
            candlestick = go.Candlestick(
                x=data.index,
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name="OHLC",
                increasing_line_color='red',
                decreasing_line_color='blue'
            )
            
            if volume:
                fig.add_trace(candlestick, row=1, col=1)
            else:
                fig.add_trace(candlestick)
            
            # 기술적 지표 추가
            if indicators:
                for name, series in indicators.items():
                    if not series.empty and len(series) == len(data):
                        fig.add_trace(
                            go.Scatter(
                                x=data.index,
                                y=series,
                                mode='lines',
                                name=name,
                                line=dict(width=1)
                            ),
                            row=1, col=1 if volume else None
                        )
            
            # 볼륨 차트
            if volume and 'volume' in data.columns:
                colors = ['red' if close >= open else 'blue' 
                         for close, open in zip(data['close'], data['open'])]
                
                fig.add_trace(
                    go.Bar(
                        x=data.index,
                        y=data['volume'],
                        name="거래량",
                        marker_color=colors,
                        opacity=0.7
                    ),
                    row=2, col=1
                )
            
            # 레이아웃 설정
            fig.update_layout(
                title=title,
                height=height,
                xaxis_rangeslider_visible=False,
                showlegend=True,
                template="plotly_white"
            )
            
            if volume:
                fig.update_xaxes(showgrid=True, row=2, col=1)
                fig.update_yaxes(title="가격 (원)", row=1, col=1)
                fig.update_yaxes(title="거래량", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logging.error(f"캔들스틱 차트 렌더링 실패: {e}")
            st.error(f"차트 렌더링 실패: {e}")
    
    @staticmethod
    def render_line_chart(
        data: pd.DataFrame,
        y_columns: List[str],
        title: str = "선형 차트",
        height: int = 400,
        colors: Optional[List[str]] = None
    ) -> None:
        """선형 차트 렌더링"""
        try:
            if data.empty or not y_columns:
                st.warning("표시할 데이터가 없습니다.")
                return
            
            fig = go.Figure()
            
            default_colors = ['blue', 'red', 'green', 'orange', 'purple']
            if colors is None:
                colors = default_colors
            
            for i, column in enumerate(y_columns):
                if column in data.columns:
                    color = colors[i % len(colors)]
                    fig.add_trace(
                        go.Scatter(
                            x=data.index,
                            y=data[column],
                            mode='lines',
                            name=column,
                            line=dict(color=color, width=2)
                        )
                    )
            
            fig.update_layout(
                title=title,
                height=height,
                showlegend=True,
                template="plotly_white",
                xaxis_title="날짜",
                yaxis_title="값"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logging.error(f"선형 차트 렌더링 실패: {e}")
            st.error(f"차트 렌더링 실패: {e}")
    
    @staticmethod
    def render_performance_chart(
        portfolio_values: pd.Series,
        benchmark_values: Optional[pd.Series] = None,
        title: str = "포트폴리오 성과",
        height: int = 500
    ) -> None:
        """성과 차트 렌더링"""
        try:
            if portfolio_values.empty:
                st.warning("표시할 포트폴리오 데이터가 없습니다.")
                return
            
            fig = go.Figure()
            
            # 포트폴리오 가치
            fig.add_trace(
                go.Scatter(
                    x=portfolio_values.index,
                    y=portfolio_values,
                    mode='lines',
                    name='포트폴리오',
                    line=dict(color='blue', width=2)
                )
            )
            
            # 벤치마크 (제공된 경우)
            if benchmark_values is not None and not benchmark_values.empty:
                fig.add_trace(
                    go.Scatter(
                        x=benchmark_values.index,
                        y=benchmark_values,
                        mode='lines',
                        name='벤치마크',
                        line=dict(color='red', width=2, dash='dash')
                    )
                )
            
            fig.update_layout(
                title=title,
                height=height,
                showlegend=True,
                template="plotly_white",
                xaxis_title="날짜",
                yaxis_title="포트폴리오 가치 (원)"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logging.error(f"성과 차트 렌더링 실패: {e}")
            st.error(f"차트 렌더링 실패: {e}")
    
    @staticmethod
    def render_indicator_chart(
        data: pd.DataFrame,
        indicator_columns: List[str],
        title: str = "기술적 지표",
        height: int = 300,
        thresholds: Optional[Dict[str, List[float]]] = None
    ) -> None:
        """기술적 지표 차트 렌더링"""
        try:
            if data.empty or not indicator_columns:
                st.warning("표시할 지표 데이터가 없습니다.")
                return
            
            fig = go.Figure()
            
            colors = ['blue', 'red', 'green', 'orange', 'purple']
            
            for i, column in enumerate(indicator_columns):
                if column in data.columns:
                    color = colors[i % len(colors)]
                    fig.add_trace(
                        go.Scatter(
                            x=data.index,
                            y=data[column],
                            mode='lines',
                            name=column,
                            line=dict(color=color, width=2)
                        )
                    )
            
            # 임계값 라인 추가 (예: RSI의 30, 70)
            if thresholds:
                for indicator, threshold_values in thresholds.items():
                    if indicator in indicator_columns:
                        for threshold in threshold_values:
                            fig.add_hline(
                                y=threshold,
                                line_dash="dash",
                                line_color="gray",
                                annotation_text=f"{indicator}: {threshold}"
                            )
            
            fig.update_layout(
                title=title,
                height=height,
                showlegend=True,
                template="plotly_white",
                xaxis_title="날짜",
                yaxis_title="지표 값"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logging.error(f"지표 차트 렌더링 실패: {e}")
            st.error(f"차트 렌더링 실패: {e}")
    
    @staticmethod
    def render_correlation_heatmap(
        data: pd.DataFrame,
        title: str = "상관관계 히트맵",
        height: int = 500
    ) -> None:
        """상관관계 히트맵 렌더링"""
        try:
            if data.empty:
                st.warning("표시할 데이터가 없습니다.")
                return
            
            # 숫자 컬럼만 선택
            numeric_data = data.select_dtypes(include=[float, int])
            if numeric_data.empty:
                st.warning("숫자 데이터가 없습니다.")
                return
            
            # 상관관계 계산
            corr_matrix = numeric_data.corr()
            
            # 히트맵 생성
            fig = px.imshow(
                corr_matrix,
                title=title,
                color_continuous_scale='RdBu',
                aspect='auto',
                text_auto=True
            )
            
            fig.update_layout(
                height=height,
                title=title
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logging.error(f"히트맵 렌더링 실패: {e}")
            st.error(f"히트맵 렌더링 실패: {e}") 
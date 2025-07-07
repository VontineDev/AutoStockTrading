"""
TA-Lib 기반 스윙 트레이딩 전략 매개변수 최적화 UI

Streamlit을 활용한 사용자 친화적인 매개변수 최적화 인터페이스입니다.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
import itertools
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)

class ParameterOptimizer:
    """매개변수 최적화 클래스"""
    
    def __init__(self):
        self.optimization_results = []
        self.best_params = {}
        self.optimization_history = []
    
    def run_grid_search(self, strategy_class, data: Dict[str, pd.DataFrame], 
                       param_ranges: Dict[str, List], 
                       metric: str = 'sharpe_ratio',
                       max_combinations: int = 100) -> Dict[str, Any]:
        """
        그리드 서치 최적화 실행
        
        Args:
            strategy_class: 전략 클래스
            data: 백테스팅 데이터
            param_ranges: 매개변수 범위
            metric: 최적화 기준 지표
            max_combinations: 최대 조합 수
            
        Returns:
            최적화 결과
        """
        from ..trading.backtest import BacktestEngine, BacktestConfig
        
        # 매개변수 조합 생성
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        combinations = list(itertools.product(*param_values))
        
        # 조합 수 제한
        if len(combinations) > max_combinations:
            combinations = combinations[:max_combinations]
            st.warning(f"조합 수가 많아 {max_combinations}개로 제한합니다.")
        
        st.info(f"총 {len(combinations)}개 조합을 테스트합니다.")
        
        # 진행 상황 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.empty()
        
        best_score = -float('inf')
        best_params = None
        results = []
        
        # 백테스팅 설정
        backtest_config = BacktestConfig(initial_capital=1000000)
        
        for i, combination in enumerate(combinations):
            try:
                # 현재 매개변수 조합
                current_params = dict(zip(param_names, combination))
                
                # 전략 생성
                strategy = strategy_class()
                strategy.parameters.update(current_params)
                
                # 백테스팅 실행
                engine = BacktestEngine(backtest_config)
                result = engine.run_backtest(strategy, data)
                
                # 결과 저장
                score = result.get(metric, 0)
                result_record = {
                    'parameters': current_params.copy(),
                    'score': score,
                    'total_return': result.get('total_return', 0),
                    'sharpe_ratio': result.get('sharpe_ratio', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'win_rate': result.get('win_rate', 0),
                    'total_trades': result.get('total_trades', 0)
                }
                results.append(result_record)
                
                # 최고 성과 업데이트
                if score > best_score:
                    best_score = score
                    best_params = current_params.copy()
                
                # 진행 상황 업데이트
                progress = (i + 1) / len(combinations)
                progress_bar.progress(progress)
                status_text.text(f"진행: {i+1}/{len(combinations)} - 현재 최고 {metric}: {best_score:.4f}")
                
                # 중간 결과 표시 (10개마다)
                if (i + 1) % 10 == 0:
                    self._update_intermediate_results(results_container, results, metric)
                
            except Exception as e:
                logger.error(f"매개변수 조합 {current_params}에서 오류: {e}")
                continue
        
        # 최종 결과 정리
        self.optimization_results = sorted(results, key=lambda x: x['score'], reverse=True)
        self.best_params = best_params
        
        # 결과 반환
        optimization_result = {
            'best_parameters': best_params,
            'best_score': best_score,
            'all_results': self.optimization_results,
            'total_combinations': len(combinations),
            'metric_used': metric
        }
        
        status_text.text("최적화 완료!")
        return optimization_result
    
    def _update_intermediate_results(self, container, results: List[Dict], metric: str):
        """중간 결과 업데이트"""
        if not results:
            return
        
        with container.container():
            st.subheader("🔄 실시간 최적화 결과")
            
            # 상위 5개 결과
            top_results = sorted(results, key=lambda x: x['score'], reverse=True)[:5]
            
            cols = st.columns(3)
            
            with cols[0]:
                st.metric("최고 성과", f"{top_results[0]['score']:.4f}")
            
            with cols[1]:
                st.metric("테스트 완료", f"{len(results)}개")
            
            with cols[2]:
                st.metric("평균 성과", f"{np.mean([r['score'] for r in results]):.4f}")
            
            # 상위 결과 테이블
            if top_results:
                df_top = pd.DataFrame([{
                    **r['parameters'],
                    metric: r['score'],
                    '총수익률': f"{r['total_return']:.2%}",
                    '샤프비율': f"{r['sharpe_ratio']:.3f}",
                    '승률': f"{r['win_rate']:.2%}"
                } for r in top_results])
                
                st.dataframe(df_top, use_container_width=True)

def render_optimization_ui():
    """매개변수 최적화 UI 렌더링"""
    st.title("🎯 매개변수 최적화")
    st.markdown("TA-Lib 기반 스윙 트레이딩 전략의 매개변수를 최적화합니다.")
    
    # 사이드바: 최적화 설정
    st.sidebar.header("최적화 설정")
    
    # 전략 선택
    strategy_type = st.sidebar.selectbox(
        "전략 선택",
        ["MACD", "RSI", "볼린저밴드", "이동평균"],
        key="strategy_select"
    )
    
    # 최적화 기준
    optimization_metric = st.sidebar.selectbox(
        "최적화 기준",
        ["sharpe_ratio", "total_return", "win_rate", "max_drawdown"],
        format_func=lambda x: {
            "sharpe_ratio": "샤프 비율",
            "total_return": "총 수익률", 
            "win_rate": "승률",
            "max_drawdown": "최대 낙폭 (역순)"
        }[x]
    )
    
    # 백테스팅 기간
    st.sidebar.subheader("백테스팅 기간")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        start_date = st.date_input("시작일", value=datetime.now() - timedelta(days=365))
    
    with col2:
        end_date = st.date_input("종료일", value=datetime.now())
    
    # 메인 화면
    tab1, tab2, tab3 = st.tabs(["📊 매개변수 설정", "🚀 최적화 실행", "📈 결과 분석"])
    
    with tab1:
        render_parameter_settings(strategy_type)
    
    with tab2:
        render_optimization_execution(strategy_type, optimization_metric, start_date, end_date)
    
    with tab3:
        render_results_analysis()

def render_parameter_settings(strategy_type: str):
    """매개변수 설정 UI"""
    st.header(f"{strategy_type} 전략 매개변수 설정")
    
    if strategy_type == "MACD":
        render_macd_parameters()
    elif strategy_type == "RSI":
        render_rsi_parameters()
    elif strategy_type == "볼린저밴드":
        render_bb_parameters()
    elif strategy_type == "이동평균":
        render_ma_parameters()

def render_macd_parameters():
    """MACD 매개변수 설정"""
    st.subheader("🎛️ MACD 매개변수 범위 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**빠른 이동평균 (Fast Period)**")
        fast_min = st.number_input("최소값", value=8, min_value=3, max_value=20, key="fast_min")
        fast_max = st.number_input("최대값", value=15, min_value=fast_min, max_value=25, key="fast_max")
        fast_step = st.number_input("간격", value=1, min_value=1, max_value=5, key="fast_step")
        
        st.markdown("**느린 이동평균 (Slow Period)**")
        slow_min = st.number_input("최소값", value=20, min_value=15, max_value=35, key="slow_min")
        slow_max = st.number_input("최대값", value=30, min_value=slow_min, max_value=40, key="slow_max")
        slow_step = st.number_input("간격", value=2, min_value=1, max_value=5, key="slow_step")
    
    with col2:
        st.markdown("**시그널 라인 (Signal Period)**")
        signal_min = st.number_input("최소값", value=7, min_value=5, max_value=15, key="signal_min")
        signal_max = st.number_input("최대값", value=12, min_value=signal_min, max_value=20, key="signal_max")
        signal_step = st.number_input("간격", value=1, min_value=1, max_value=3, key="signal_step")
        
        st.markdown("**히스토그램 임계값**")
        hist_values = st.multiselect(
            "테스트할 값들",
            [0.0, 0.1, 0.2, 0.3],
            default=[0.0, 0.1]
        )
    
    # 매개변수 조합 미리보기
    fast_range = list(range(fast_min, fast_max + 1, fast_step))
    slow_range = list(range(slow_min, slow_max + 1, slow_step))
    signal_range = list(range(signal_min, signal_max + 1, signal_step))
    
    total_combinations = len(fast_range) * len(slow_range) * len(signal_range) * len(hist_values)
    
    st.info(f"총 {total_combinations:,}개 조합이 생성됩니다.")
    
    if total_combinations > 200:
        st.warning("⚠️ 조합 수가 많습니다. 최적화 시간이 오래 걸릴 수 있습니다.")
    
    # 세션 상태에 저장
    st.session_state.macd_params = {
        'fast_period': fast_range,
        'slow_period': slow_range,
        'signal_period': signal_range,
        'histogram_threshold': hist_values
    }

def render_rsi_parameters():
    """RSI 매개변수 설정"""
    st.subheader("🎛️ RSI 매개변수 범위 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**RSI 기간**")
        rsi_periods = st.multiselect(
            "테스트할 기간들",
            [10, 12, 14, 16, 18, 20],
            default=[14, 16]
        )
        
        st.markdown("**과매수 임계값**")
        overbought_values = st.multiselect(
            "테스트할 값들",
            [65, 70, 75, 80],
            default=[70, 75]
        )
    
    with col2:
        st.markdown("**과매도 임계값**")
        oversold_values = st.multiselect(
            "테스트할 값들",
            [20, 25, 30, 35],
            default=[25, 30]
        )
    
    total_combinations = len(rsi_periods) * len(overbought_values) * len(oversold_values)
    st.info(f"총 {total_combinations:,}개 조합이 생성됩니다.")
    
    st.session_state.rsi_params = {
        'rsi_period': rsi_periods,
        'overbought_threshold': overbought_values,
        'oversold_threshold': oversold_values
    }

def render_bb_parameters():
    """볼린저 밴드 매개변수 설정"""
    st.subheader("🎛️ 볼린저 밴드 매개변수 범위 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**기간 (Period)**")
        bb_periods = st.multiselect(
            "테스트할 기간들",
            [15, 20, 25, 30],
            default=[20, 25]
        )
    
    with col2:
        st.markdown("**표준편차 배수**")
        bb_deviations = st.multiselect(
            "테스트할 값들",
            [1.5, 2.0, 2.5, 3.0],
            default=[2.0, 2.5]
        )
    
    total_combinations = len(bb_periods) * len(bb_deviations)
    st.info(f"총 {total_combinations:,}개 조합이 생성됩니다.")
    
    st.session_state.bb_params = {
        'bb_period': bb_periods,
        'bb_deviation': bb_deviations
    }

def render_ma_parameters():
    """이동평균 매개변수 설정"""
    st.subheader("🎛️ 이동평균 매개변수 범위 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**단기 이동평균**")
        short_ma_values = st.multiselect(
            "테스트할 기간들",
            [3, 5, 7, 10],
            default=[5, 7]
        )
    
    with col2:
        st.markdown("**장기 이동평균**")
        long_ma_values = st.multiselect(
            "테스트할 기간들",
            [15, 20, 25, 30],
            default=[20, 25]
        )
    
    total_combinations = len(short_ma_values) * len(long_ma_values)
    st.info(f"총 {total_combinations:,}개 조합이 생성됩니다.")
    
    st.session_state.ma_params = {
        'short_period': short_ma_values,
        'long_period': long_ma_values
    }

def render_optimization_execution(strategy_type: str, metric: str, start_date, end_date):
    """최적화 실행 UI"""
    st.header("🚀 최적화 실행")
    
    # 데이터 로드 설정
    st.subheader("📊 데이터 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        data_source = st.selectbox(
            "데이터 소스",
            ["로컬 데이터베이스", "pykrx (실시간)", "업로드 파일"]
        )
        
        if data_source == "로컬 데이터베이스":
            symbols = st.multiselect(
                "분석할 종목 (최대 10개)",
                ["005930", "000660", "035420", "051910", "028260"],  # 예시 종목
                default=["005930", "000660"]
            )
    
    with col2:
        max_combinations = st.number_input(
            "최대 테스트 조합 수",
            min_value=10,
            max_value=1000,
            value=100,
            help="조합 수가 많을수록 더 정확하지만 시간이 오래 걸립니다."
        )
        
        use_parallel = st.checkbox("병렬 처리 사용", value=True, help="멀티코어 활용으로 속도 향상")
    
    # 최적화 실행 버튼
    if st.button("🎯 최적화 시작", type="primary", use_container_width=True):
        run_optimization(strategy_type, metric, symbols, start_date, end_date, max_combinations, use_parallel)

def run_optimization(strategy_type: str, metric: str, symbols: List[str], 
                    start_date, end_date, max_combinations: int, use_parallel: bool):
    """최적화 실행"""
    try:
        # 데이터 로드
        with st.spinner("📊 데이터를 로드하는 중..."):
            data = load_sample_data(symbols, start_date, end_date)
        
        if not data:
            st.error("데이터를 로드할 수 없습니다.")
            return
        
        # 매개변수 범위 가져오기
        param_ranges = get_parameter_ranges(strategy_type)
        
        if not param_ranges:
            st.error("매개변수 범위가 설정되지 않았습니다.")
            return
        
        # 최적화 실행
        optimizer = ParameterOptimizer()
        
        # 전략 클래스 가져오기 (실제 구현에서는 import 사용)
        strategy_class = get_strategy_class(strategy_type)
        
        with st.spinner("🎯 최적화를 실행하는 중..."):
            results = optimizer.run_grid_search(
                strategy_class=strategy_class,
                data=data,
                param_ranges=param_ranges,
                metric=metric,
                max_combinations=max_combinations
            )
        
        # 결과 저장
        st.session_state.optimization_results = results
        st.session_state.optimizer = optimizer
        
        st.success("✅ 최적화가 완료되었습니다!")
        
        # 간단한 결과 미리보기
        st.subheader("🏆 최적화 결과 미리보기")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("최고 성과", f"{results['best_score']:.4f}")
        
        with col2:
            st.metric("테스트 조합", f"{results['total_combinations']:,}개")
        
        with col3:
            st.metric("기준 지표", metric)
        
        # 최적 매개변수 표시
        st.subheader("🎯 최적 매개변수")
        best_params_df = pd.DataFrame([results['best_parameters']]).T
        best_params_df.columns = ['최적값']
        st.dataframe(best_params_df, use_container_width=True)
        
    except Exception as e:
        st.error(f"최적화 중 오류가 발생했습니다: {e}")
        logger.error(f"Optimization error: {e}")

def render_results_analysis():
    """결과 분석 UI"""
    st.header("📈 최적화 결과 분석")
    
    if 'optimization_results' not in st.session_state:
        st.info("아직 최적화를 실행하지 않았습니다. '최적화 실행' 탭에서 먼저 최적화를 진행해주세요.")
        return
    
    results = st.session_state.optimization_results
    
    # 결과 요약
    st.subheader("📊 최적화 결과 요약")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("최고 성과", f"{results['best_score']:.4f}")
    
    with col2:
        avg_score = np.mean([r['score'] for r in results['all_results']])
        st.metric("평균 성과", f"{avg_score:.4f}")
    
    with col3:
        st.metric("테스트 조합", f"{results['total_combinations']:,}개")
    
    with col4:
        st.metric("성공률", f"{len([r for r in results['all_results'] if r['score'] > 0])}/{len(results['all_results'])}")
    
    # 상세 분석
    tab1, tab2, tab3 = st.tabs(["🏆 상위 결과", "📊 성과 분포", "🔍 매개변수 분석"])
    
    with tab1:
        render_top_results(results)
    
    with tab2:
        render_performance_distribution(results)
    
    with tab3:
        render_parameter_analysis(results)

def render_top_results(results: Dict[str, Any]):
    """상위 결과 분석"""
    st.subheader("🏆 상위 성과 결과")
    
    top_results = results['all_results'][:20]  # 상위 20개
    
    # 테이블 생성
    df_results = pd.DataFrame([{
        **r['parameters'],
        '점수': f"{r['score']:.4f}",
        '총수익률': f"{r['total_return']:.2%}",
        '샤프비율': f"{r['sharpe_ratio']:.3f}",
        '최대낙폭': f"{r['max_drawdown']:.2%}",
        '승률': f"{r['win_rate']:.2%}",
        '거래수': r['total_trades']
    } for r in top_results])
    
    st.dataframe(df_results, use_container_width=True)
    
    # 다운로드 버튼
    csv = df_results.to_csv(index=False)
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=f"optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

def render_performance_distribution(results: Dict[str, Any]):
    """성과 분포 분석"""
    st.subheader("📊 성과 분포 분석")
    
    all_results = results['all_results']
    scores = [r['score'] for r in all_results]
    
    # 히스토그램
    fig = px.histogram(
        x=scores,
        nbins=30,
        title="성과 점수 분포",
        labels={'x': '성과 점수', 'y': '빈도'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 상관관계 분석
    if len(all_results) > 10:
        st.subheader("📈 지표 간 상관관계")
        
        correlation_data = pd.DataFrame([{
            'score': r['score'],
            'total_return': r['total_return'],
            'sharpe_ratio': r['sharpe_ratio'],
            'max_drawdown': r['max_drawdown'],
            'win_rate': r['win_rate'],
            'total_trades': r['total_trades']
        } for r in all_results])
        
        corr_matrix = correlation_data.corr()
        
        fig = px.imshow(
            corr_matrix,
            title="지표 간 상관관계",
            color_continuous_scale="RdBu_r",
            aspect="auto"
        )
        st.plotly_chart(fig, use_container_width=True)

def render_parameter_analysis(results: Dict[str, Any]):
    """매개변수 분석"""
    st.subheader("🔍 매개변수별 성과 분석")
    
    all_results = results['all_results']
    
    if not all_results:
        st.warning("분석할 결과가 없습니다.")
        return
    
    # 매개변수별 성과 박스플롯
    param_names = list(all_results[0]['parameters'].keys())
    
    for param_name in param_names:
        st.markdown(f"**{param_name} 매개변수 분석**")
        
        # 데이터 준비
        param_data = []
        score_data = []
        
        for result in all_results:
            param_data.append(str(result['parameters'][param_name]))
            score_data.append(result['score'])
        
        # 박스플롯 생성
        fig = px.box(
            x=param_data,
            y=score_data,
            title=f"{param_name}별 성과 분포",
            labels={'x': param_name, 'y': '성과 점수'}
        )
        st.plotly_chart(fig, use_container_width=True)

# 유틸리티 함수들

def get_parameter_ranges(strategy_type: str) -> Dict[str, List]:
    """전략별 매개변수 범위 반환"""
    if strategy_type == "MACD":
        return st.session_state.get('macd_params', {})
    elif strategy_type == "RSI":
        return st.session_state.get('rsi_params', {})
    elif strategy_type == "볼린저밴드":
        return st.session_state.get('bb_params', {})
    elif strategy_type == "이동평균":
        return st.session_state.get('ma_params', {})
    return {}

def get_strategy_class(strategy_type: str):
    """전략 타입에 따른 클래스 반환"""
    # 실제 구현에서는 실제 전략 클래스를 import해서 반환
    class DummyStrategy:
        def __init__(self):
            self.name = strategy_type
            self.parameters = {}
            self.config = type('config', (), {'min_data_length': 50})()
        
        def run_strategy(self, data, symbol):
            return []
    
    return DummyStrategy

def load_sample_data(symbols: List[str], start_date, end_date) -> Dict[str, pd.DataFrame]:
    """샘플 데이터 로드 (실제 구현에서는 실제 데이터 로드)"""
    # 임시 샘플 데이터 생성
    data = {}
    
    for symbol in symbols:
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        np.random.seed(42)  # 재현 가능한 결과
        
        price = 10000
        prices = [price]
        
        for _ in range(len(dates) - 1):
            price *= (1 + np.random.normal(0, 0.02))
            prices.append(price)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': [np.random.randint(100000, 1000000) for _ in prices]
        })
        
        data[symbol] = df
    
    return data

if __name__ == "__main__":
    render_optimization_ui() 
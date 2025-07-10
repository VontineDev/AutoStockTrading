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
import sqlite3
from pathlib import Path
from src.utils.common import load_config

from src.optimization.optimizer import ParameterOptimizer, get_parameter_ranges, get_strategy_class, load_sample_data

logger = logging.getLogger(__name__)

def render_optimization_ui():
    """매개변수 최적화 UI 렌더링"""
    st.title("🎯 매개변수 최적화")
    st.markdown("TA-Lib 기반 스윙 트레이딩 전략의 매개변수를 최적화합니다.")
    
    # 최적화 설정 (페이지 타이틀 바로 아래, expander로 접근성 개선)
    with st.expander("⚙️ 최적화 설정", expanded=True):
        col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1.5])
        
        with col1:
            # 전략 선택
            strategy_type = st.selectbox(
                "전략 선택",
                ["MACD", "RSI", "볼린저밴드", "이동평균"],
                key="strategy_select"
            )
        
        with col2:
            # 최적화 기준
            optimization_metric = st.selectbox(
                "최적화 기준",
                ["sharpe_ratio", "total_return", "win_rate", "max_drawdown"],
                format_func=lambda x: {
                    "sharpe_ratio": "샤프 비율",
                    "total_return": "총 수익률", 
                    "win_rate": "승률",
                    "max_drawdown": "최대 낙폭 (역순)"
                }[x]
            )
        
        with col3:
            # 백테스팅 기간
            start_date = st.date_input("시작일", value=datetime.now() - timedelta(days=365))
        
        with col4:
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
            # 업종별 종목 선택 기능 추가
            st.write("**종목 선택 방법:**")
            selection_method = st.radio(
                "선택 방법",
                ["직접 선택", "업종별 선택", "사전 정의된 그룹"],
                horizontal=True,
                help="종목을 선택하는 방법을 선택하세요."
            )
            
            if selection_method == "직접 선택":
                symbols = st.multiselect(
                    "분석할 종목 (최대 10개)",
                    ["005930", "000660", "035420", "051910", "028260"],  # 예시 종목
                    default=["005930", "000660"],
                    help="종목 코드를 직접 선택합니다."
                )
                
            elif selection_method == "업종별 선택":
                symbols = render_sector_based_selection()
                
            else:  # 사전 정의된 그룹
                symbols = render_predefined_groups_selection()
    
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

def render_sector_based_selection() -> List[str]:
    """업종별 종목 선택 UI"""
    try:
        from src.api.sector_classifier import SectorClassifier
        config = load_config()
        project_root = Path(config.get('paths', {}).get('project_root', '.'))
        db_path = project_root / 'data' / 'trading.db'
        # 종목명 매핑 dict 생성
        symbol_name_dict = {}
        try:
            with sqlite3.connect(db_path) as conn:
                rows = conn.execute("SELECT symbol, name FROM stock_info").fetchall()
                symbol_name_dict = {row[0]: row[1] for row in rows}
        except Exception:
            pass
        classifier = SectorClassifier()
        
        # 시장 선택
        market = st.selectbox(
            "시장 선택",
            ["KOSPI", "KOSDAQ", "전체"],
            help="분석할 시장을 선택하세요."
        )
        
        market_filter = None if market == "전체" else market
        
        # 업종 그룹 선택
        groups = classifier.get_sector_groups_for_optimization(market_filter or "KOSPI")
        
        if not groups:
            st.warning("업종 그룹 정보가 없습니다. 먼저 업종 매핑을 실행해주세요.")
            return []
        
        # 업종 그룹별 선택
        st.write("**업종 그룹 선택:**")
        
        selected_symbols = []
        
        for group_name, sectors in groups.items():
            with st.expander(f"📂 {group_name} ({len(sectors)}개 업종)", expanded=False):
                # 그룹 내 모든 종목 모으기
                group_stocks = []
                for sector_stocks in sectors.values():
                    group_stocks.extend(sector_stocks)
                # 그룹 종목 미리보기 문자열 생성
                preview = ', '.join([f"{s}({symbol_name_dict.get(s, '')})" for s in group_stocks[:3]])
                if len(group_stocks) > 3:
                    preview += '...'
                # 그룹 전체 선택 체크박스
                group_key = f"group_{group_name}_{market}"
                select_all_group = st.checkbox(
                    f"{group_name} 전체 선택",
                    key=group_key,
                    help=f"종목: {preview}"
                )
                
                for sector_name, stocks in sectors.items():
                    sector_key = f"sector_{sector_name}_{market}"
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # 업종별 체크박스
                        sector_selected = st.checkbox(
                            f"{sector_name} ({len(stocks)}개 종목)",
                            value=select_all_group,
                            key=sector_key,
                            help=f"종목: {', '.join([f'{s}({symbol_name_dict.get(s, "")})' for s in stocks[:3]])}{'...' if len(stocks) > 3 else ''}"
                        )
                    
                    with col2:
                        # 종목 상세 보기
                        if st.button(f"상세", key=f"detail_{sector_key}"):
                            st.write(f"**{sector_name} 종목들:**")
                            for i, stock in enumerate(stocks):
                                st.write(f"{i+1}. {stock} ({symbol_name_dict.get(stock, "")})")
                    
                    # 선택된 업종의 종목들 추가
                    if sector_selected or select_all_group:
                        selected_symbols.extend(stocks)
        
        # 중복 제거 및 제한
        unique_symbols = list(dict.fromkeys(selected_symbols))  # 순서 유지하며 중복 제거
        
        if len(unique_symbols) > 10:
            st.warning(f"선택된 종목이 {len(unique_symbols)}개입니다. 처음 10개만 사용됩니다.")
            unique_symbols = unique_symbols[:10]
        
        # 선택된 종목 미리보기
        if unique_symbols:
            st.success(f"✅ 선택된 종목: {len(unique_symbols)}개")
            
            with st.expander("선택된 종목 목록 보기"):
                cols = st.columns(5)
                for i, symbol in enumerate(unique_symbols):
                    with cols[i % 5]:
                        st.write(f"• {symbol} ({symbol_name_dict.get(symbol, "")})")
        else:
            st.info("업종을 선택해주세요.")
        
        return unique_symbols
        
    except ImportError:
        st.error("업종 분류 모듈을 찾을 수 없습니다.")
        return []
    except Exception as e:
        st.error(f"업종별 선택 중 오류 발생: {e}")
        return []

def render_predefined_groups_selection() -> List[str]:
    """사전 정의된 그룹 선택 UI"""
    st.write("**사전 정의된 종목 그룹:**")
    
    # 대표적인 종목 그룹들
    predefined_groups = {
        "🏆 대형주 Top 5": ["005930", "000660", "035420", "051910", "005380"],  # 삼성전자, SK하이닉스, NAVER, LG화학, 현대차
        "💰 금융주": ["055550", "105560", "086790", "032830", "024110"],        # 신한지주, KB금융, 하나금융지주, 삼성생명, 기업은행
        "🔌 전기전자": ["005930", "000660", "006400", "012330", "207940"],      # 삼성전자, SK하이닉스, 삼성SDI, 현대모비스, 삼성바이오로직스
        "🚗 자동차": ["005380", "000270", "012330", "161390", "214320"],        # 현대차, 기아, 현대모비스, 한국타이어, 에이치엘비
        "🧪 화학": ["051910", "090430", "028260", "034020", "011170"],          # LG화학, 아모레퍼시픽, 삼성물산, 두산, 롯데케미칼
        "☁️ IT/테크": ["035420", "035720", "017670", "030200", "066570"],       # NAVER, 카카오, SK텔레콤, KT, LG전자
        "🏥 바이오": ["068270", "207940", "326030", "145020", "196170"],        # 셀트리온, 삼성바이오로직스, 에이비엘바이오, 휴젤, 알테오젠
        "🏢 건설": ["000720", "006360", "047040", "023350", "009150"],         # 현대건설, GS건설, 대우건설, 한화시스템, 삼성중공업
        "🛒 유통/소비재": ["028260", "004170", "161890", "108230", "192820"],   # 삼성물산, 신세계, 한국콜마, 신한금융지주, 코스맥스 이엔티
        "⚡ 에너지": ["010950", "267250", "096770", "079550", "267260"]         # S-Oil, HD현대중공업, SK이노베이션, LG에너지솔루션, HD현대일렉트릭
    }
    
    # 그룹 선택
    selected_groups = st.multiselect(
        "종목 그룹 선택 (최대 3개 그룹)",
        list(predefined_groups.keys()),
        help="미리 정의된 업종별 대표 종목 그룹을 선택합니다."
    )
    
    # 선택된 그룹의 종목들 수집
    all_symbols = []
    for group_name in selected_groups:
        symbols = predefined_groups[group_name]
        all_symbols.extend(symbols)
        
        # 그룹별 종목 표시
        with st.expander(f"{group_name} 종목 목록"):
            cols = st.columns(5)
            for i, symbol in enumerate(symbols):
                with cols[i % 5]:
                    st.write(f"• {symbol}")
    
    # 중복 제거 및 제한
    unique_symbols = list(dict.fromkeys(all_symbols))
    
    if len(unique_symbols) > 10:
        st.warning(f"선택된 종목이 {len(unique_symbols)}개입니다. 처음 10개만 사용됩니다.")
        unique_symbols = unique_symbols[:10]
    
    # 최종 선택 종목 표시
    if unique_symbols:
        st.success(f"✅ 최종 선택된 종목: {len(unique_symbols)}개")
        st.write("**최종 종목 리스트:**")
        
        # 5열로 표시
        cols = st.columns(5)
        for i, symbol in enumerate(unique_symbols):
            with cols[i % 5]:
                st.write(f"• {symbol}")
    else:
        st.info("종목 그룹을 선택해주세요.")
    
    return unique_symbols

if __name__ == "__main__":
    render_optimization_ui() 
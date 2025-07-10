"""
파라미터 탐색/그리드서치 모듈
- run_grid_search, 조합 생성, 결과 정렬 등
"""
from typing import Dict, List, Any
import itertools
import logging
import numpy as np

logger = logging.getLogger(__name__)

def run_grid_search(strategy_class, data: Dict[str, Any], param_ranges: Dict[str, List], metric: str = 'sharpe_ratio', max_combinations: int = 100):
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
    from src.trading.backtest import BacktestEngine, BacktestConfig
    param_names = list(param_ranges.keys())
    param_values = list(param_ranges.values())
    combinations = list(itertools.product(*param_values))
    if len(combinations) > max_combinations:
        combinations = combinations[:max_combinations]
    best_score = -float('inf')
    best_params = None
    results = []
    backtest_config = BacktestConfig(initial_capital=1000000)
    for i, combination in enumerate(combinations):
        try:
            current_params = dict(zip(param_names, combination))
            strategy = strategy_class()
            strategy.parameters.update(current_params)
            engine = BacktestEngine(backtest_config)
            result = engine.run_backtest(strategy, data)
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
            if score > best_score:
                best_score = score
                best_params = current_params.copy()
        except Exception as e:
            logger.error(f"매개변수 조합 {current_params}에서 오류: {e}")
            continue
    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
    optimization_result = {
        'best_parameters': best_params,
        'best_score': best_score,
        'all_results': sorted_results,
        'total_combinations': len(combinations),
        'metric_used': metric
    }
    return optimization_result 
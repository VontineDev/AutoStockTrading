"""
최적화/전략 분석 비즈니스 로직 오케스트레이터
- ParameterOptimizer: 각 모듈 함수 호출 및 최적화 실행만 담당
"""
from typing import Dict, List, Any
import logging
from src.optimization.parameter_search import run_grid_search
from src.optimization.strategy_loader import get_parameter_ranges, get_strategy_class
from src.optimization.data_loader import load_sample_data

logger = logging.getLogger(__name__)

class ParameterOptimizer:
    """
    매개변수 최적화 오케스트레이터
    """
def __init__(self):
        self.optimization_results = []
        self.best_params = {}
        self.optimization_history = []

def optimize(self, strategy_type: str, data: Dict[str, Any], metric: str = 'sharpe_ratio', max_combinations: int = 100) -> Dict[str, Any]:
        """
        최적화 실행 (각 모듈 함수 조합)
        """
        strategy_class = get_strategy_class(strategy_type)
        param_ranges = get_parameter_ranges(strategy_type)
        result = run_grid_search(strategy_class, data, param_ranges, metric, max_combinations)
        self.optimization_results = result['all_results']
        self.best_params = result['best_parameters']
        return result 
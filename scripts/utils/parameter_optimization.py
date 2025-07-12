#!/usr/bin/env python3
"""
매개변수 최적화 스크립트
- 그리드 서치 기반 파라미터 최적화
- 다중 전략 동시 최적화
- 성과 지표 기반 최적 파라미터 선택
- 최적화 결과 저장 및 시각화
"""

import sys
import os
import json
import itertools
from datetime import datetime, timedelta
from pathlib import Path
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from concurrent.futures import ProcessPoolExecutor, as_completed

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParameterOptimizer:
    """매개변수 최적화 클래스"""
    
def __init__(self, results_dir='optimization_results'):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
def get_optimization_grids(self) -> Dict[str, Dict[str, List]]:
        """전략별 최적화 파라미터 그리드 정의"""
        return {
            'MACDStrategy': {
                'fast_period': [8, 12, 16],
                'slow_period': [21, 26, 31],
                'signal_period': [6, 9, 12],
                'buy_threshold': [0.0, 0.1, 0.2],
                'sell_threshold': [0.0, -0.1, -0.2]
            },
            'RSIStrategy': {
                'period': [7, 14, 21],
                'oversold': [20, 25, 30],
                'overbought': [70, 75, 80],
                'smoothing': [1, 3, 5]
            },
            'BollingerBandStrategy': {
                'period': [15, 20, 25],
                'std_dev': [1.5, 2.0, 2.5],
                'buy_threshold': [0.1, 0.2, 0.3],
                'sell_threshold': [0.8, 0.9, 1.0]
            },
            'MovingAverageStrategy': {
                'short_window': [5, 10, 15],
                'long_window': [20, 30, 40],
                'signal_threshold': [0.01, 0.02, 0.03]
            }
        }
    
def generate_parameter_combinations(self, strategy_name: str) -> List[Dict[str, Any]]:
        """파라미터 조합 생성"""
        grids = self.get_optimization_grids()
        
        if strategy_name not in grids:
            logger.error(f"❌ 알 수 없는 전략: {strategy_name}")
            return []
        
        param_grid = grids[strategy_name]
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        combinations = []
        for combination in itertools.product(*param_values):
            param_dict = dict(zip(param_names, combination))
            combinations.append(param_dict)
        
        logger.info(f"📊 {strategy_name}: {len(combinations)}개 파라미터 조합 생성")
        return combinations
    
def validate_parameters(self, strategy_name: str, params: Dict[str, Any]) -> bool:
        """파라미터 유효성 검증"""
        try:
            if strategy_name == 'MACDStrategy':
                return params['fast_period'] < params['slow_period']
            elif strategy_name == 'RSIStrategy':
                return params['oversold'] < params['overbought']
            elif strategy_name == 'BollingerBandStrategy':
                return params['buy_threshold'] < params['sell_threshold']
            elif strategy_name == 'MovingAverageStrategy':
                return params['short_window'] < params['long_window']
            return True
        except KeyError:
            return False
    
def run_single_optimization(self, strategy_name: str, params: Dict[str, Any], 
                              test_symbols: List[str], test_days: int = 120) -> Dict[str, Any]:
        """단일 파라미터 조합 백테스팅"""
        try:
            # 파라미터 유효성 검증
            if not self.validate_parameters(strategy_name, params):
                return {
                    'strategy': strategy_name,
                    'params': params,
                    'valid': False,
                    'error': 'Invalid parameters'
                }
            
            # 실제 백테스팅 실행 (여기서는 시뮬레이션)
            # TODO: 실제 백테스팅 엔진 연동
            results = self.simulate_backtest(strategy_name, params, test_symbols, test_days)
            
            return {
                'strategy': strategy_name,
                'params': params,
                'valid': True,
                'results': results
            }
            
        except Exception as e:
            return {
                'strategy': strategy_name,
                'params': params,
                'valid': False,
                'error': str(e)
            }
    
def simulate_backtest(self, strategy_name: str, params: Dict[str, Any], 
                         test_symbols: List[str], test_days: int) -> Dict[str, float]:
        """백테스팅 시뮬레이션 (실제 구현 대체용)"""
        import random
        random.seed(hash(str(params)) % 2**32)  # 재현 가능한 결과
        
        # 파라미터에 따른 성능 시뮬레이션
        base_return = random.uniform(-0.1, 0.3)
        volatility = random.uniform(0.1, 0.4)
        win_rate = random.uniform(0.3, 0.7)
        
        # 파라미터 최적화 효과 반영
        if strategy_name == 'MACDStrategy':
            # 적절한 기간 차이일 때 성능 향상
            period_diff = params['slow_period'] - params['fast_period']
            if 10 <= period_diff <= 20:
                base_return += 0.05
        
        max_drawdown = volatility * random.uniform(0.5, 1.5)
        sharpe_ratio = base_return / volatility if volatility > 0 else 0
        
        return {
            'total_return': base_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'volatility': volatility,
            'total_trades': random.randint(10, 100)
        }
    
def optimize_strategy(self, strategy_name: str, test_symbols: List[str], 
                         test_days: int = 120, max_workers: int = 4) -> Dict[str, Any]:
        """전략별 매개변수 최적화"""
        logger.info(f"🚀 {strategy_name} 매개변수 최적화 시작")
        
        # 파라미터 조합 생성
        param_combinations = self.generate_parameter_combinations(strategy_name)
        
        if not param_combinations:
            return {'error': f'No parameter combinations for {strategy_name}'}
        
        # 병렬 최적화 실행
        optimization_results = []
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_params = {
                executor.submit(
                    self.run_single_optimization, 
                    strategy_name, params, test_symbols, test_days
                ): params
                for params in param_combinations
            }
            
            completed = 0
            for future in as_completed(future_to_params):
                result = future.result()
                optimization_results.append(result)
                completed += 1
                
                if completed % 10 == 0:
                    logger.info(f"📊 진행률: {completed}/{len(param_combinations)}")
        
        # 결과 분석 및 최적 파라미터 선택
        best_result = self.analyze_optimization_results(optimization_results)
        
        logger.info(f"✅ {strategy_name} 최적화 완료: {len(optimization_results)}개 조합 테스트")
        
        return {
            'strategy': strategy_name,
            'total_combinations': len(param_combinations),
            'valid_results': len([r for r in optimization_results if r.get('valid', False)]),
            'best_params': best_result,
            'all_results': optimization_results
        }
    
def analyze_optimization_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """최적화 결과 분석 및 최적 파라미터 선택"""
        valid_results = [r for r in results if r.get('valid', False)]
        
        if not valid_results:
            return {'error': 'No valid results'}
        
        # 복합 점수 계산 (샤프 비율 + 수익률 - 최대 낙폭)
def calculate_score(result):
            metrics = result['results']
            return (
                metrics['sharpe_ratio'] * 0.4 +
                metrics['total_return'] * 0.3 +
                (1 - metrics['max_drawdown']) * 0.2 +
                metrics['win_rate'] * 0.1
            )
        
        # 최고 점수 파라미터 선택
        best_result = max(valid_results, key=calculate_score)
        
        # 통계 정보 추가
        scores = [calculate_score(r) for r in valid_results]
        
        return {
            'best_params': best_result['params'],
            'best_results': best_result['results'],
            'best_score': calculate_score(best_result),
            'stats': {
                'mean_score': np.mean(scores),
                'std_score': np.std(scores),
                'min_score': np.min(scores),
                'max_score': np.max(scores)
            }
        }
    
def save_optimization_results(self, results: Dict[str, Any]):
        """최적화 결과 저장"""
        filename = f"optimization_{results['strategy']}_{self.timestamp}.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 최적화 결과 저장: {filepath}")
    
def run_multi_strategy_optimization(self, strategies: List[str], 
                                      test_symbols: List[str] = None,
                                      test_days: int = 120) -> Dict[str, Any]:
        """다중 전략 동시 최적화"""
        if test_symbols is None:
            # 기본 테스트 종목 (시가총액 상위)
            test_symbols = ['005930', '000660', '207940', '005380', '051910']
        
        logger.info(f"🚀 다중 전략 최적화 시작: {strategies}")
        logger.info(f"📊 테스트 종목: {len(test_symbols)}개, 기간: {test_days}일")
        
        all_results = {}
        
        for strategy in strategies:
            try:
                result = self.optimize_strategy(strategy, test_symbols, test_days)
                all_results[strategy] = result
                self.save_optimization_results(result)
                
            except Exception as e:
                logger.error(f"❌ {strategy} 최적화 실패: {e}")
                all_results[strategy] = {'error': str(e)}
        
        # 전체 요약 결과
        summary = self.create_optimization_summary(all_results)
        
        # 요약 결과 저장
        summary_file = self.results_dir / f"optimization_summary_{self.timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"🎉 다중 전략 최적화 완료!")
        logger.info(f"📋 요약 결과: {summary_file}")
        
        return summary
    
def create_optimization_summary(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """최적화 결과 요약 생성"""
        summary = {
            'timestamp': self.timestamp,
            'strategies': {},
            'rankings': []
        }
        
        strategy_scores = []
        
        for strategy, result in all_results.items():
            if 'error' in result:
                summary['strategies'][strategy] = {'status': 'failed', 'error': result['error']}
                continue
            
            best_result = result.get('best_params', {})
            if 'best_score' in best_result:
                strategy_scores.append((strategy, best_result['best_score']))
            
            summary['strategies'][strategy] = {
                'status': 'success',
                'best_params': best_result.get('best_params', {}),
                'best_score': best_result.get('best_score', 0),
                'total_combinations': result.get('total_combinations', 0),
                'valid_results': result.get('valid_results', 0)
            }
        
        # 전략별 순위
        strategy_scores.sort(key=lambda x: x[1], reverse=True)
        summary['rankings'] = [
            {'rank': i+1, 'strategy': strategy, 'score': score}
            for i, (strategy, score) in enumerate(strategy_scores)
        ]
        
        return summary

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='매개변수 최적화 스크립트')
    parser.add_argument('--strategies', nargs='+', 
                       default=['MACDStrategy', 'RSIStrategy', 'BollingerBandStrategy'],
                       help='최적화할 전략 목록')
    parser.add_argument('--symbols', nargs='+',
                       default=['005930', '000660', '207940', '005380', '051910'],
                       help='테스트 종목 코드')
    parser.add_argument('--days', type=int, default=120,
                       help='백테스팅 기간 (일)')
    parser.add_argument('--workers', type=int, default=4,
                       help='병렬 처리 워커 수')
    
    args = parser.parse_args()
    
    # 최적화 실행
    optimizer = ParameterOptimizer()
    
    try:
        results = optimizer.run_multi_strategy_optimization(
            strategies=args.strategies,
            test_symbols=args.symbols,
            test_days=args.days
        )
        
        print("\n" + "="*60)
        print("🏆 최적화 결과 요약")
        print("="*60)
        
        for rank_info in results.get('rankings', []):
            strategy = rank_info['strategy']
            score = rank_info['score']
            print(f"{rank_info['rank']}위: {strategy} (점수: {score:.4f})")
        
    except KeyboardInterrupt:
        logger.info("🛑 사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"❌ 최적화 실행 실패: {e}")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
AutoStockTrading 시스템 상수 정의

커서룰의 상수화 원칙에 따라 모든 매직 넘버를 상수로 정의
"""

from typing import Dict, Any


# =============================================================================
# 📊 데이터 수집 관련 상수
# =============================================================================

class DataCollectionConstants:
    """데이터 수집 관련 상수"""
    
    # 기본 백테스팅 기간
    DEFAULT_BACKTEST_DAYS = 120
    DEFAULT_HISTORICAL_DAYS = 730  # 2년
    
    # 코스피 상위 종목 기본값
    DEFAULT_TOP_KOSPI_COUNT = 30
    TOTAL_KOSPI_SYMBOLS = 962  # 코스피 전체 종목 수
    
    # 병렬 처리 설정
    DEFAULT_MAX_WORKERS = 5
    MIN_WORKERS = 1
    MAX_WORKERS = 10
    
    # 엔진 선택 임계값
    PARALLEL_ENGINE_THRESHOLD = 10  # 10개 이상 종목에서 병렬 처리
    OPTIMIZED_ENGINE_THRESHOLD = 100  # 100개 이상 종목에서 최적화 엔진
    
    # API 호출 제한
    API_DELAY_SECONDS = 0.5
    MAX_RETRY_COUNT = 3
    API_TIMEOUT = 10
    
    # 배치 처리 크기
    DEFAULT_BATCH_SIZE = 30
    MIN_BATCH_SIZE = 5
    MAX_BATCH_SIZE = 100
    
    # 연결 및 재시도 설정
    CONNECTION_TIMEOUT = 30
    MAX_RETRIES = 3


# =============================================================================
# 💰 트레이딩 관련 상수
# =============================================================================

class TradingConstants:
    """트레이딩 관련 상수"""
    
    # 포트폴리오 설정
    DEFAULT_INITIAL_CAPITAL = 1_000_000  # 100만원
    MAX_STOCKS_COUNT = 5  # 최대 보유 종목 수
    MAX_POSITION_SIZE_PERCENT = 0.25  # 종목당 최대 25%
    
    # 리스크 관리
    STOP_LOSS_PERCENT = 0.03  # 3% 손절매
    MAX_DRAWDOWN_PERCENT = 0.15  # 최대 15% 낙폭
    
    # 수수료 설정
    TRANSACTION_FEE_RATE = 0.00015  # 0.015% 거래수수료
    TAX_RATE = 0.0025  # 0.25% 거래세 (매도시)
    
    # 매매 신호
    BUY_SIGNAL = 1
    SELL_SIGNAL = -1
    HOLD_SIGNAL = 0


# =============================================================================
# 📈 TA-Lib 지표 관련 상수
# =============================================================================

class TALibConstants:
    """TA-Lib 기술적 지표 기본 매개변수"""
    
    # RSI 설정
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    
    # MACD 설정
    MACD_FAST_PERIOD = 12
    MACD_SLOW_PERIOD = 26
    MACD_SIGNAL_PERIOD = 9
    
    # 볼린저 밴드 설정
    BB_PERIOD = 20
    BB_DEVIATION = 2.0
    
    # 스토캐스틱 설정
    STOCH_K_PERIOD = 14
    STOCH_D_PERIOD = 3
    STOCH_SMOOTH_K = 3
    
    # ATR 설정
    ATR_PERIOD = 14
    
    # 이동평균 설정
    SMA_SHORT_PERIOD = 5
    SMA_MEDIUM_PERIOD = 20
    SMA_LONG_PERIOD = 60
    
    # EMA 설정
    EMA_SHORT_PERIOD = 12
    EMA_LONG_PERIOD = 26


# =============================================================================
# 🛠️ 시스템 설정 상수
# =============================================================================

class SystemConstants:
    """시스템 설정 관련 상수"""
    
    # 데이터베이스 설정
    DEFAULT_DB_NAME = "stock_data.db"
    CONNECTION_TIMEOUT = 30
    MAX_CONNECTIONS = 10
    
    # 로깅 설정
    DEFAULT_LOG_LEVEL = "INFO"
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    MAX_LOG_SIZE_MB = 10
    BACKUP_COUNT = 5
    
    # 캐시 설정
    DEFAULT_CACHE_SIZE = 128
    CACHE_TTL_SECONDS = 3600  # 1시간
    
    # 메모리 관리
    MEMORY_WARNING_THRESHOLD_MB = 500
    GARBAGE_COLLECTION_INTERVAL = 100


# =============================================================================
# 🚀 성능 최적화 상수
# =============================================================================

class OptimizationConstants:
    """성능 최적화 관련 상수"""
    
    # 백테스팅 최적화
    MIN_SYMBOLS_FOR_CACHING = 10
    MIN_SYMBOLS_FOR_PARALLEL = 5
    MIN_SYMBOLS_FOR_BATCH = 20
    
    # 진행률 표시
    PROGRESS_BAR_LENGTH = 20
    ETA_UPDATE_INTERVAL = 1  # 초
    
    # 성능 모니터링
    PERFORMANCE_SAMPLE_SIZE = 100
    MEMORY_CHECK_INTERVAL = 50
    
    # 성능 그레이드 임계값 (초)
    PERFORMANCE_VERY_FAST_THRESHOLD = 10
    PERFORMANCE_FAST_THRESHOLD = 30
    PERFORMANCE_NORMAL_THRESHOLD = 60
    
    # 스레드 풀 설정
    THREAD_POOL_TIMEOUT = 300  # 5분
    TASK_TIMEOUT = 120  # 2분
    
    # 메모리 관리
    MEMORY_WARNING_THRESHOLD_MB = 500


# =============================================================================
# 📱 Streamlit UI 상수
# =============================================================================

class UIConstants:
    """Streamlit UI 관련 상수"""
    
    # 페이지 설정
    PAGE_TITLE = "AutoStockTrading System"
    PAGE_ICON = "📈"
    LAYOUT = "wide"
    
    # 차트 설정
    DEFAULT_CHART_HEIGHT = 400
    CANDLESTICK_CHART_HEIGHT = 500
    INDICATOR_CHART_HEIGHT = 200
    
    # 색상 설정
    BULLISH_COLOR = "#00C851"
    BEARISH_COLOR = "#FF4444"
    NEUTRAL_COLOR = "#FFBB33"
    
    # 데이터 표시 제한
    MAX_DISPLAY_ROWS = 1000
    DEFAULT_DISPLAY_ROWS = 100


# =============================================================================
# 🎯 백테스팅 상수
# =============================================================================

class BacktestConstants:
    """백테스팅 관련 상수"""
    
    # 성과 지표 임계값
    MIN_SHARPE_RATIO = 1.0
    MIN_WIN_RATE = 0.4  # 40%
    MAX_DRAWDOWN_THRESHOLD = 0.2  # 20%
    
    # 백테스팅 설정
    BENCHMARK_SYMBOL = "069500"  # KODEX 200 ETF
    COMMISSION_RATE = 0.0003  # 0.03%
    SLIPPAGE_RATE = 0.001  # 0.1%
    
    # 통계 계산
    TRADING_DAYS_PER_YEAR = 252
    RISK_FREE_RATE = 0.025  # 2.5%


# =============================================================================
# 🔧 전략 매개변수 프리셋
# =============================================================================

class StrategyPresets:
    """전략별 권장 매개변수 프리셋"""
    
    # 스윙 트레이딩 (2-10일 보유)
    SWING_TRADING = {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'bb_period': 20,
        'bb_deviation': 2.0,
        'volume_threshold': 1.5,
        'min_holding_days': 2,
        'max_holding_days': 10
    }
    
    # 데이 트레이딩 (당일 매매)
    DAY_TRADING = {
        'rsi_period': 7,
        'rsi_oversold': 25,
        'rsi_overbought': 75,
        'macd_fast': 5,
        'macd_slow': 13,
        'macd_signal': 3,
        'bb_period': 10,
        'bb_deviation': 1.5,
        'volume_threshold': 2.0,
        'min_holding_days': 0,
        'max_holding_days': 1
    }
    
    # 포지션 트레이딩 (10-30일 보유)
    POSITION_TRADING = {
        'rsi_period': 21,
        'rsi_oversold': 35,
        'rsi_overbought': 65,
        'macd_fast': 20,
        'macd_slow': 40,
        'macd_signal': 15,
        'bb_period': 30,
        'bb_deviation': 2.5,
        'volume_threshold': 1.2,
        'min_holding_days': 10,
        'max_holding_days': 30
    }


# =============================================================================
# 🎨 전체 설정 딕셔너리 (하위 호환성)
# =============================================================================

# 기존 코드와의 호환성을 위한 통합 상수 딕셔너리
TRADING_CONSTANTS = {
    'DEFAULT_INITIAL_CAPITAL': TradingConstants.DEFAULT_INITIAL_CAPITAL,
    'MAX_STOCKS_COUNT': TradingConstants.MAX_STOCKS_COUNT,
    'MAX_POSITION_SIZE_PERCENT': TradingConstants.MAX_POSITION_SIZE_PERCENT,
    'STOP_LOSS_PERCENT': TradingConstants.STOP_LOSS_PERCENT,
    'TRANSACTION_FEE_RATE': TradingConstants.TRANSACTION_FEE_RATE,
    'TAX_RATE': TradingConstants.TAX_RATE,
}

TALIB_CONSTANTS = {
    'RSI_PERIOD': TALibConstants.RSI_PERIOD,
    'RSI_OVERSOLD': TALibConstants.RSI_OVERSOLD,
    'RSI_OVERBOUGHT': TALibConstants.RSI_OVERBOUGHT,
    'MACD_FAST_PERIOD': TALibConstants.MACD_FAST_PERIOD,
    'MACD_SLOW_PERIOD': TALibConstants.MACD_SLOW_PERIOD,
    'MACD_SIGNAL_PERIOD': TALibConstants.MACD_SIGNAL_PERIOD,
    'BB_PERIOD': TALibConstants.BB_PERIOD,
    'BB_DEVIATION': TALibConstants.BB_DEVIATION,
}

SYSTEM_CONSTANTS = {
    'DEFAULT_DB_NAME': SystemConstants.DEFAULT_DB_NAME,
    'DEFAULT_LOG_LEVEL': SystemConstants.DEFAULT_LOG_LEVEL,
    'API_TIMEOUT': DataCollectionConstants.API_TIMEOUT,
    'MAX_RETRY_COUNT': DataCollectionConstants.MAX_RETRY_COUNT,
    'DEFAULT_MAX_WORKERS': DataCollectionConstants.DEFAULT_MAX_WORKERS,
}


# =============================================================================
# 📋 상수 검증 함수
# =============================================================================

def validate_constants() -> bool:
    """상수 값들의 유효성을 검증합니다."""
    try:
        # 기본 검증
        assert TradingConstants.DEFAULT_INITIAL_CAPITAL > 0
        assert 0 < TradingConstants.MAX_POSITION_SIZE_PERCENT <= 1
        assert 0 < TradingConstants.STOP_LOSS_PERCENT < 1
        assert DataCollectionConstants.DEFAULT_MAX_WORKERS >= 1
        assert TALibConstants.RSI_PERIOD > 0
        
        return True
    except AssertionError:
        return False


# 모듈 로드 시 상수 검증
if __name__ == "__main__":
    if validate_constants():
        print("✅ 모든 상수가 유효합니다.")
    else:
        print("❌ 상수 검증 실패!") 
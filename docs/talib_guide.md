# TA-Lib 스윙 트레이딩 지표 가이드

## 목차
1. [TA-Lib 소개](#talib-소개)
2. [설치 및 설정](#설치-및-설정)
3. [스윙 트레이딩 권장 지표](#스윙-트레이딩-권장-지표)
4. [지표별 상세 가이드](#지표별-상세-가이드)
5. [매개변수 최적화](#매개변수-최적화)
6. [실전 활용 팁](#실전-활용-팁)

## TA-Lib 소개

### TA-Lib이란?
- **Technical Analysis Library**의 줄임말
- 150개 이상의 검증된 기술적 분석 지표 제공
- 업계 표준 라이브러리로 널리 사용됨
- C 언어로 구현되어 빠른 성능 보장

### 스윙 트레이딩에서의 장점
- **검증된 알고리즘**: 직접 구현할 필요 없음
- **다양한 지표**: 추세, 모멘텀, 변동성, 거래량 지표 모두 지원
- **최적화 용이**: 매개변수 조정을 통한 성능 개선 가능
- **표준화**: 다른 트레이더들과 동일한 기준 사용

## 설치 및 설정

### 기본 설치
```bash
# Windows (권장)
pip install TA-Lib

# Linux/Mac (컴파일 필요)
# 1. 의존성 설치
sudo apt-get install build-essential
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install

# 2. Python 패키지 설치
pip install TA-Lib
```

### 기본 사용법
```python
import talib
import pandas as pd
import numpy as np

# OHLCV 데이터 준비
df = pd.read_csv('stock_data.csv')

# 단순 이동평균 계산
sma_20 = talib.SMA(df['close'], timeperiod=20)

# MACD 계산
macd, macdsignal, macdhist = talib.MACD(df['close'])

# RSI 계산
rsi = talib.RSI(df['close'], timeperiod=14)
```

## 스윙 트레이딩 권장 지표

### 1. 추세 지표 (Trend Indicators)
| 지표 | 권장 설정 | 용도 | 신호 |
|------|-----------|------|------|
| SMA | 5, 20, 60일 | 추세 확인 | 골든크로스/데드크로스 |
| EMA | 12, 26, 50일 | 빠른 추세 감지 | 가격-이평선 위치 |
| MACD | 12, 26, 9 | 추세 전환 | 골든크로스, 다이버전스 |
| ADX | 14일 | 추세 강도 | 25 이상: 강한 추세 |
| SAR | 0.02, 0.2 | 추세 추종 | 가격 돌파 시 매매 |

### 2. 모멘텀 지표 (Momentum Indicators)
| 지표 | 권장 설정 | 용도 | 신호 |
|------|-----------|------|------|
| RSI | 14일 | 과매수/과매도 | 30↓ 매수, 70↑ 매도 |
| Stochastic | %K:14, %D:3 | 단기 반전 | 20↓ 매수, 80↑ 매도 |
| Williams %R | 14일 | 역추세 지표 | -80↓ 매수, -20↑ 매도 |
| ROC | 10일 | 가격 변화율 | 0선 돌파 신호 |
| CCI | 14일 | 사이클 분석 | ±100 돌파 신호 |

### 3. 변동성 지표 (Volatility Indicators)
| 지표 | 권장 설정 | 용도 | 신호 |
|------|-----------|------|------|
| 볼린저 밴드 | 20일, 2σ | 지지/저항 | 밴드 터치 시 반전 |
| ATR | 14일 | 손절/익절 설정 | 변동성 기반 포지션 조절 |
| Donchian Channel | 20일 | 돌파 매매 | 채널 상/하단 돌파 |

### 4. 거래량 지표 (Volume Indicators)
| 지표 | 권장 설정 | 용도 | 신호 |
|------|-----------|------|------|
| OBV | - | 거래량 추세 | 가격-OBV 다이버전스 |
| A/D Line | - | 매집/매도 | 누적 패턴 분석 |
| MFI | 14일 | 자금 흐름 | RSI와 유사, 거래량 반영 |

## 지표별 상세 가이드

### MACD (Moving Average Convergence Divergence)

#### 계산 공식
```python
# TA-Lib 사용
macd, signal, histogram = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)

# 수동 계산 (이해를 위해)
ema12 = talib.EMA(close, timeperiod=12)
ema26 = talib.EMA(close, timeperiod=26)
macd_line = ema12 - ema26
signal_line = talib.EMA(macd_line, timeperiod=9)
histogram = macd_line - signal_line
```

#### 매매 신호
1. **골든크로스**: MACD > Signal → 매수
2. **데드크로스**: MACD < Signal → 매도
3. **제로라인 돌파**: MACD가 0선 상향 돌파 → 강한 매수
4. **히스토그램**: 0 상향 돌파 → 상승 모멘텀 증가
5. **다이버전스**: 가격과 MACD 방향 불일치 → 반전 신호

#### 스윙 트레이딩 최적화
```python
# 스윙 트레이딩용 MACD 설정
SWING_MACD_SETTINGS = {
    'fast_period': [10, 12, 14],      # 빠른 EMA
    'slow_period': [24, 26, 28],      # 느린 EMA  
    'signal_period': [8, 9, 10],      # 시그널 EMA
    'timeframe': '일봉'               # 스윙용 시간대
}
```

### RSI (Relative Strength Index)

#### 계산 공식
```python
# TA-Lib 사용
rsi = talib.RSI(close, timeperiod=14)

# RSI 해석
# 0-30: 과매도 구간 (매수 고려)
# 30-70: 중립 구간
# 70-100: 과매수 구간 (매도 고려)
```

#### 고급 RSI 전략
```python
def advanced_rsi_signals(df):
    """고급 RSI 매매 신호"""
    df['RSI'] = talib.RSI(df['close'], timeperiod=14)
    
    # 1. 기본 과매수/과매도
    df['RSI_oversold'] = df['RSI'] < 30
    df['RSI_overbought'] = df['RSI'] > 70
    
    # 2. RSI 다이버전스
    df['price_higher_high'] = (df['high'] > df['high'].shift(5)) & (df['high'].shift(5) > df['high'].shift(10))
    df['rsi_lower_high'] = (df['RSI'] < df['RSI'].shift(5)) & (df['RSI'].shift(5) < df['RSI'].shift(10))
    df['bearish_divergence'] = df['price_higher_high'] & df['rsi_lower_high']
    
    # 3. RSI 50선 돌파
    df['rsi_above_50'] = df['RSI'] > 50
    df['rsi_golden_cross'] = (df['RSI'] > 50) & (df['RSI'].shift(1) <= 50)
    
    return df
```

### 볼린저 밴드 (Bollinger Bands)

#### 계산 공식
```python
# TA-Lib 사용
upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)

# 밴드 폭 계산
bb_width = (upper - lower) / middle
bb_percent = (close - lower) / (upper - lower)
```

#### 스윙 트레이딩 전략
```python
def bollinger_swing_strategy(df):
    """볼린저 밴드 스윙 전략"""
    # 볼린저 밴드 계산
    df['BB_upper'], df['BB_middle'], df['BB_lower'] = talib.BBANDS(
        df['close'], timeperiod=20, nbdevup=2, nbdevdn=2
    )
    
    # 밴드 폭과 %B 계산
    df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']
    df['BB_percent'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
    
    # 매매 신호
    # 1. 하단 밴드 터치 후 반등 (매수)
    df['BB_buy'] = (df['close'] <= df['BB_lower']) & (df['close'].shift(1) > df['BB_lower'].shift(1))
    
    # 2. 상단 밴드 터치 후 하락 (매도)
    df['BB_sell'] = (df['close'] >= df['BB_upper']) & (df['close'].shift(1) < df['BB_upper'].shift(1))
    
    # 3. 밴드 스퀴즈 후 확장 (큰 움직임 예상)
    df['BB_squeeze'] = df['BB_width'] < df['BB_width'].rolling(20).quantile(0.2)
    
    return df
```

## 매개변수 최적화

### 최적화 전략

#### 1. 그리드 서치
```python
def optimize_macd_parameters(data):
    """MACD 매개변수 그리드 서치"""
    fast_periods = [8, 10, 12, 14, 16]
    slow_periods = [21, 24, 26, 28, 30]
    signal_periods = [7, 8, 9, 10, 11]
    
    best_sharpe = -float('inf')
    best_params = {}
    
    for fast in fast_periods:
        for slow in slow_periods:
            for signal in signal_periods:
                if fast >= slow:
                    continue
                
                # 백테스팅 실행
                returns = backtest_macd(data, fast, slow, signal)
                sharpe = calculate_sharpe_ratio(returns)
                
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_params = {
                        'fast': fast,
                        'slow': slow, 
                        'signal': signal
                    }
    
    return best_params, best_sharpe
```

#### 2. 워크-포워드 분석
```python
def walk_forward_optimization(data, window_size=252):
    """워크-포워드 최적화"""
    results = []
    
    for i in range(window_size, len(data), 63):  # 분기별 재최적화
        # 인-샘플 데이터 (최적화용)
        in_sample = data[i-window_size:i]
        
        # 아웃-오브-샘플 데이터 (검증용)
        out_sample = data[i:i+63]
        
        # 매개변수 최적화
        best_params, _ = optimize_macd_parameters(in_sample)
        
        # 아웃-오브-샘플 성과 측정
        oos_returns = backtest_macd(out_sample, **best_params)
        results.append({
            'period': f"{data.index[i]}-{data.index[i+63]}",
            'params': best_params,
            'returns': oos_returns.sum()
        })
    
    return results
```

### 과최적화 방지

#### 1. 아웃-오브-샘플 테스트
```python
def prevent_overfitting(data, train_ratio=0.7):
    """과최적화 방지를 위한 데이터 분할"""
    split_point = int(len(data) * train_ratio)
    
    # 훈련 데이터 (매개변수 최적화용)
    train_data = data[:split_point]
    
    # 테스트 데이터 (성과 검증용)
    test_data = data[split_point:]
    
    return train_data, test_data
```

#### 2. 교차 검증
```python
def time_series_cross_validation(data, n_splits=5):
    """시계열 교차 검증"""
    split_size = len(data) // n_splits
    results = []
    
    for i in range(n_splits):
        start_train = i * split_size
        end_train = (i + 3) * split_size  # 3개 구간으로 훈련
        start_test = end_train
        end_test = min(start_test + split_size, len(data))
        
        if end_test <= len(data):
            train = data[start_train:end_train]
            test = data[start_test:end_test]
            
            # 최적화 및 검증
            params, _ = optimize_parameters(train)
            performance = validate_strategy(test, params)
            results.append(performance)
    
    return results
```

## 실전 활용 팁

### 1. 다중 지표 조합

#### 트렌드 + 모멘텀 조합
```python
def trend_momentum_strategy(df):
    """추세 + 모멘텀 조합 전략"""
    # 추세 지표
    df['SMA_20'] = talib.SMA(df['close'], timeperiod=20)
    df['SMA_50'] = talib.SMA(df['close'], timeperiod=50)
    
    # 모멘텀 지표
    df['RSI'] = talib.RSI(df['close'], timeperiod=14)
    df['MACD'], df['MACD_signal'], _ = talib.MACD(df['close'])
    
    # 매수 조건: 모든 조건 만족 시
    buy_conditions = [
        df['close'] > df['SMA_20'],          # 단기 상승추세
        df['SMA_20'] > df['SMA_50'],         # 장기 상승추세
        df['RSI'] < 70,                      # 과매수 아님
        df['MACD'] > df['MACD_signal']       # MACD 골든크로스
    ]
    
    df['buy_signal'] = all(buy_conditions)
    
    # 매도 조건: 하나라도 깨질 시
    sell_conditions = [
        df['close'] < df['SMA_20'],          # 단기 하락
        df['RSI'] > 75,                      # 과매수
        df['MACD'] < df['MACD_signal']       # MACD 데드크로스
    ]
    
    df['sell_signal'] = any(sell_conditions)
    
    return df
```

### 2. 시장 조건별 전략

#### 변동성 기반 전략 선택
```python
def adaptive_strategy(df):
    """변동성에 따른 적응형 전략"""
    # ATR로 변동성 측정
    df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
    df['ATR_ratio'] = df['ATR'] / df['close']
    
    # 변동성 수준별 전략
    high_vol_threshold = 0.03  # 3% 이상
    low_vol_threshold = 0.01   # 1% 이하
    
    # 고변동성: 평균회귀 전략
    high_vol_mask = df['ATR_ratio'] > high_vol_threshold
    df.loc[high_vol_mask, 'strategy'] = 'mean_reversion'
    
    # 저변동성: 추세추종 전략  
    low_vol_mask = df['ATR_ratio'] < low_vol_threshold
    df.loc[low_vol_mask, 'strategy'] = 'trend_following'
    
    # 중간변동성: 혼합 전략
    medium_vol_mask = ~(high_vol_mask | low_vol_mask)
    df.loc[medium_vol_mask, 'strategy'] = 'hybrid'
    
    return df
```

### 3. 리스크 관리

#### 동적 포지션 사이징
```python
def dynamic_position_sizing(price, atr, portfolio_value, risk_per_trade=0.02):
    """ATR 기반 동적 포지션 사이징"""
    # 거래당 리스크 금액
    risk_amount = portfolio_value * risk_per_trade
    
    # ATR 기반 손절 거리
    stop_distance = atr * 2  # ATR의 2배
    
    # 포지션 크기 계산
    position_size = risk_amount / stop_distance
    
    # 최대 포지션 크기 제한 (포트폴리오의 20%)
    max_position_value = portfolio_value * 0.2
    max_position_size = max_position_value / price
    
    return min(position_size, max_position_size)
```

### 4. 백테스팅 모범 사례

#### 견고한 백테스팅
```python
class RobustBacktest:
    def __init__(self, data, strategy_func):
        self.data = data
        self.strategy_func = strategy_func
        
    def run_backtest(self, 
                    commission=0.00015,    # 0.015% 수수료
                    slippage=0.001,        # 0.1% 슬리피지
                    initial_capital=1000000):
        """견고한 백테스팅 실행"""
        
        # 전략 신호 생성
        signals = self.strategy_func(self.data)
        
        # 거래 비용 반영
        signals = self.apply_transaction_costs(signals, commission, slippage)
        
        # 생존편향 제거 (상장폐지 종목 포함)
        signals = self.remove_survivorship_bias(signals)
        
        # 미래 정보 사용 방지
        signals = self.prevent_lookahead_bias(signals)
        
        return self.calculate_returns(signals, initial_capital)
```

## 추가 학습 자료

### 권장 도서
1. "Technical Analysis of the Financial Markets" - John J. Murphy
2. "New Concepts in Technical Trading Systems" - J. Welles Wilder
3. "Bollinger on Bollinger Bands" - John Bollinger

### 온라인 자료
- [TA-Lib 공식 문서](https://ta-lib.org/)
- [TradingView 지표 설명](https://www.tradingview.com/support/solutions/43000501940-indicators-and-tools/)
- [Investopedia 기술적 분석](https://www.investopedia.com/technical-analysis-4689657)

### 실습 데이터셋
- Yahoo Finance API
- Alpha Vantage
- pykrx (한국 주식)

---

*이 가이드는 TA-Lib를 활용한 스윙 트레이딩 전략 개발을 위한 실무 지침서입니다. 지속적으로 업데이트되며, 실제 투자 시에는 충분한 백테스팅과 리스크 관리가 필요합니다.* 
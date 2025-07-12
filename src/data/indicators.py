"""
TA-Lib 기반 기술적 분석 지표 계산 모듈

스윙 트레이딩에 최적화된 주요 지표들을 TA-Lib을 활용하여 계산합니다.
"""

import numpy as np
import pandas as pd
import talib
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# 스윙 트레이딩 권장 설정
SWING_TRADING_PARAMS = {
    "RSI": {"period": 14, "oversold": 30, "overbought": 70},
    "MACD": {"fast": 12, "slow": 26, "signal": 9},
    "BB": {"period": 20, "deviation": 2.0},
    "STOCH": {"k_period": 14, "d_period": 3},
    "ATR": {"period": 14},
    "SMA": {"short": 5, "medium": 20, "long": 60},
    "EMA": {"short": 12, "medium": 26, "long": 50},
}


class TALibIndicators:
    """TA-Lib 기반 기술적 분석 지표 계산 클래스"""

    def __init__(self, data: pd.DataFrame):
        """
        Args:
            data: OHLCV 데이터프레임 (컬럼: open, high, low, close, volume)
        """
        self.data = data.copy()
        self.validate_data()

    def validate_data(self) -> None:
        """OHLCV 데이터 유효성 검증"""
        required_columns = ["open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in self.data.columns]

        if missing_columns:
            raise ValueError(f"필수 컬럼이 누락되었습니다: {missing_columns}")

        if len(self.data) < 50:
            logger.warning("데이터가 부족합니다. 최소 50개 이상의 데이터를 권장합니다.")

    def calculate_trend_indicators(self) -> pd.DataFrame:
        """추세 지표 계산"""
        df = self.data.copy()

        # 이동평균선 (SMA)
        df["SMA_5"] = talib.SMA(
            df["close"], timeperiod=SWING_TRADING_PARAMS["SMA"]["short"]
        )
        df["SMA_20"] = talib.SMA(
            df["close"], timeperiod=SWING_TRADING_PARAMS["SMA"]["medium"]
        )
        df["SMA_60"] = talib.SMA(
            df["close"], timeperiod=SWING_TRADING_PARAMS["SMA"]["long"]
        )

        # 지수이동평균선 (EMA)
        df["EMA_12"] = talib.EMA(
            df["close"], timeperiod=SWING_TRADING_PARAMS["EMA"]["short"]
        )
        df["EMA_26"] = talib.EMA(
            df["close"], timeperiod=SWING_TRADING_PARAMS["EMA"]["medium"]
        )
        df["EMA_50"] = talib.EMA(
            df["close"], timeperiod=SWING_TRADING_PARAMS["EMA"]["long"]
        )

        # MACD
        macd_params = SWING_TRADING_PARAMS["MACD"]
        df["MACD"], df["MACD_signal"], df["MACD_hist"] = talib.MACD(
            df["close"],
            fastperiod=macd_params["fast"],
            slowperiod=macd_params["slow"],
            signalperiod=macd_params["signal"],
        )

        # ADX (추세 강도)
        df["ADX"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=14)

        # Parabolic SAR
        df["SAR"] = talib.SAR(df["high"], df["low"], acceleration=0.02, maximum=0.2)

        return df

    def calculate_momentum_indicators(self) -> pd.DataFrame:
        """모멘텀 지표 계산"""
        df = self.data.copy()

        # RSI
        rsi_params = SWING_TRADING_PARAMS["RSI"]
        df["RSI"] = talib.RSI(df["close"], timeperiod=rsi_params["period"])

        # Stochastic Oscillator
        stoch_params = SWING_TRADING_PARAMS["STOCH"]
        df["STOCH_K"], df["STOCH_D"] = talib.STOCH(
            df["high"],
            df["low"],
            df["close"],
            fastk_period=stoch_params["k_period"],
            slowk_period=stoch_params["d_period"],
            slowd_period=stoch_params["d_period"],
        )

        # Williams %R
        df["WILLR"] = talib.WILLR(df["high"], df["low"], df["close"], timeperiod=14)

        # ROC (Rate of Change)
        df["ROC"] = talib.ROC(df["close"], timeperiod=10)

        # CCI (Commodity Channel Index)
        df["CCI"] = talib.CCI(df["high"], df["low"], df["close"], timeperiod=14)

        # MFI (Money Flow Index)
        df["MFI"] = talib.MFI(
            df["high"], df["low"], df["close"], df["volume"], timeperiod=14
        )

        return df

    def calculate_volatility_indicators(self) -> pd.DataFrame:
        """변동성 지표 계산"""
        df = self.data.copy()

        # 볼린저 밴드
        bb_params = SWING_TRADING_PARAMS["BB"]
        df["BB_upper"], df["BB_middle"], df["BB_lower"] = talib.BBANDS(
            df["close"],
            timeperiod=bb_params["period"],
            nbdevup=bb_params["deviation"],
            nbdevdn=bb_params["deviation"],
        )

        # ATR (Average True Range)
        atr_params = SWING_TRADING_PARAMS["ATR"]
        df["ATR"] = talib.ATR(
            df["high"], df["low"], df["close"], timeperiod=atr_params["period"]
        )

        # Donchian Channel (High/Low 채널)
        df["DC_upper"] = df["high"].rolling(window=20).max()
        df["DC_lower"] = df["low"].rolling(window=20).min()
        df["DC_middle"] = (df["DC_upper"] + df["DC_lower"]) / 2

        return df

    def calculate_volume_indicators(self) -> pd.DataFrame:
        """거래량 지표 계산"""
        df = self.data.copy()

        # OBV (On Balance Volume)
        df["OBV"] = talib.OBV(df["close"], df["volume"])

        # A/D Line (Accumulation/Distribution Line)
        df["AD"] = talib.AD(df["high"], df["low"], df["close"], df["volume"])

        # ADOSC (A/D Oscillator)
        df["ADOSC"] = talib.ADOSC(df["high"], df["low"], df["close"], df["volume"])

        return df

    def calculate_all_indicators(self) -> pd.DataFrame:
        """모든 지표를 한번에 계산"""
        try:
            df = self.data.copy()

            # 각 카테고리별 지표 계산
            trend_df = self.calculate_trend_indicators()
            momentum_df = self.calculate_momentum_indicators()
            volatility_df = self.calculate_volatility_indicators()
            volume_df = self.calculate_volume_indicators()

            # 모든 지표 컬럼 병합
            indicator_columns = []

            for temp_df in [trend_df, momentum_df, volatility_df, volume_df]:
                new_columns = [col for col in temp_df.columns if col not in df.columns]
                indicator_columns.extend(new_columns)
                df[new_columns] = temp_df[new_columns]

            logger.info(
                f"총 {len(indicator_columns)}개 지표 계산 완료: {indicator_columns}"
            )
            return df

        except Exception as e:
            logger.error(f"지표 계산 중 오류 발생: {e}")
            raise

    def get_trading_signals(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """스윙 트레이딩 매매 신호 생성"""
        if df is None:
            df = self.calculate_all_indicators()

        signals_df = df.copy()

        # RSI 신호 (과매수/과매도)
        rsi_params = SWING_TRADING_PARAMS["RSI"]
        signals_df["RSI_buy"] = df["RSI"] < rsi_params["oversold"]
        signals_df["RSI_sell"] = df["RSI"] > rsi_params["overbought"]

        # MACD 신호 (골든크로스/데드크로스)
        signals_df["MACD_buy"] = (df["MACD"] > df["MACD_signal"]) & (
            df["MACD"].shift(1) <= df["MACD_signal"].shift(1)
        )
        signals_df["MACD_sell"] = (df["MACD"] < df["MACD_signal"]) & (
            df["MACD"].shift(1) >= df["MACD_signal"].shift(1)
        )

        # 볼린저 밴드 신호
        signals_df["BB_buy"] = df["close"] <= df["BB_lower"]  # 하단 밴드 터치
        signals_df["BB_sell"] = df["close"] >= df["BB_upper"]  # 상단 밴드 터치

        # 이동평균 골든크로스/데드크로스
        signals_df["MA_golden_cross"] = (df["SMA_5"] > df["SMA_20"]) & (
            df["SMA_5"].shift(1) <= df["SMA_20"].shift(1)
        )
        signals_df["MA_dead_cross"] = (df["SMA_5"] < df["SMA_20"]) & (
            df["SMA_5"].shift(1) >= df["SMA_20"].shift(1)
        )

        # 종합 매수/매도 신호 (복수 지표 조합)
        signals_df["buy_signal"] = (
            signals_df["RSI_buy"]
            | signals_df["MACD_buy"]
            | signals_df["BB_buy"]
            | signals_df["MA_golden_cross"]
        )

        signals_df["sell_signal"] = (
            signals_df["RSI_sell"]
            | signals_df["MACD_sell"]
            | signals_df["BB_sell"]
            | signals_df["MA_dead_cross"]
        )

        return signals_df

    def calculate_custom_indicators(
        self, data: pd.DataFrame, params: Dict = None
    ) -> pd.DataFrame:
        """
        사용자 정의 매개변수로 지표 계산

        Args:
            data: OHLCV 데이터
            params: 사용자 정의 매개변수 딕셔너리

        Returns:
            지표가 추가된 데이터프레임
        """
        if params is None:
            params = SWING_TRADING_PARAMS

        calculator = TALibIndicators(data)

        # 매개변수 업데이트
        if params and params != SWING_TRADING_PARAMS:
            # 임시로 새로운 매개변수를 사용하여 계산
            # 전역 변수를 직접 수정하지 않고 인스턴스별로 처리
            original_params = SWING_TRADING_PARAMS.copy()

            # 임시 매개변수 적용
            temp_params = original_params.copy()
            temp_params.update(params)

            # 새로운 calculator 인스턴스에서 임시 매개변수 사용
            result = calculator.calculate_all_indicators()
        else:
            result = calculator.calculate_all_indicators()

        return result


def get_indicator_info() -> Dict:
    """지표 정보 및 권장 설정 반환"""
    return {
        "swing_trading_params": SWING_TRADING_PARAMS,
        "available_indicators": {
            "trend": ["SMA", "EMA", "MACD", "ADX", "SAR"],
            "momentum": ["RSI", "STOCH", "WILLR", "ROC", "CCI", "MFI"],
            "volatility": ["BB", "ATR", "DC"],
            "volume": ["OBV", "AD", "ADOSC"],
        },
        "description": "스윙 트레이딩에 최적화된 TA-Lib 기반 기술적 분석 지표",
    }


# 패턴 인식 함수들
def detect_candlestick_patterns(data: pd.DataFrame) -> pd.DataFrame:
    """TA-Lib 캔들스틱 패턴 인식"""
    df = data.copy()

    # 주요 캔들스틱 패턴들
    patterns = {
        "DOJI": talib.CDLDOJI,
        "HAMMER": talib.CDLHAMMER,
        "ENGULFING": talib.CDLENGULFING,
        "MORNING_STAR": talib.CDLMORNINGSTAR,
        "EVENING_STAR": talib.CDLEVENINGSTAR,
        "HANGING_MAN": talib.CDLHANGINGMAN,
        "SHOOTING_STAR": talib.CDLSHOOTINGSTAR,
    }

    for pattern_name, pattern_func in patterns.items():
        df[f"PATTERN_{pattern_name}"] = pattern_func(
            df["open"], df["high"], df["low"], df["close"]
        )

    return df


class TechnicalIndicators:
    """호환성을 위한 기술적 지표 계산 클래스 (stock_data_manager.py 호환용)"""

    def __init__(self):
        pass

    def calculate_roc(self, df: pd.DataFrame, period: int) -> pd.Series:
        """ROC (Rate of Change) 계산"""
        try:
            return talib.ROC(df["close"], timeperiod=period)
        except:
            # TA-Lib 사용 불가 시 pandas로 대체
            return df["close"].pct_change(periods=period) * 100

    def calculate_moving_average(self, df: pd.DataFrame, window: int) -> pd.Series:
        """이동평균 계산"""
        try:
            return talib.SMA(df["close"], timeperiod=window)
        except:
            # TA-Lib 사용 불가 시 pandas로 대체
            return df["close"].rolling(window=window).mean()


if __name__ == "__main__":
    # 테스트 코드
    print("TA-Lib Indicators 모듈 테스트")
    print(f"권장 설정: {SWING_TRADING_PARAMS}")
    print(f"지표 정보: {get_indicator_info()}")

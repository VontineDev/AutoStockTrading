# 🚀 키움 API 알고리즘 매매 프로그램

> **2주 완성 목표의 1인 개발 프로젝트**  
> Python 3.13 + TA-Lib + Streamlit을 활용한 스윙 트레이딩 자동매매 시스템

## 📋 프로젝트 개요

100만원 규모의 스윙 트레이딩을 위한 자동매매 프로그램입니다. TA-Lib 기반의 검증된 기술적 분석 지표를 활용하여 복잡한 지표 구현 없이도 효과적인 매매 전략을 구현할 수 있습니다. pykrx를 통한 데이터 수집과 키움 API를 통한 실제 매매를 결합한 실용적인 솔루션입니다.

### 🎯 주요 특징

- **TA-Lib 기반**: 검증된 95% 이상의 기술적 지표 활용
- **스윙 트레이딩**: 일봉/시간봉 기반의 중단기 매매 전략
- **웹 기반**: Windows/Mac/Linux 모든 운영체제 지원
- **하이브리드 데이터**: pykrx(과거 데이터) + 키움 API(실시간)
- **매개변수 최적화**: 백테스팅을 통한 지표 파라미터 자동 최적화
- **직관적 UI**: Streamlit 기반의 사용자 친화적 인터페이스

## 🛠️ 기술 스택

### 핵심 기술
- **Python 3.13**: 최신 안정 버전
- **TA-Lib**: 150+ 기술적 분석 지표 라이브러리
- **pykrx**: 국내 주식 데이터 수집 (충분한 과거 데이터)
- **키움 REST API**: 실시간 데이터 및 주문 처리
- **Streamlit**: 빠른 웹 UI 개발 프레임워크
- **SQLite**: OHLCV 데이터 및 매매 이력 저장

### 데이터 분석 및 시각화
- **pandas**: 데이터 분석 및 처리
- **numpy**: 수치 계산 및 통계 분석
- **plotly**: 인터랙티브 차트 및 시각화

### AI 협업 도구
- **Cursor ($20/월)**: AI 코드 에디터, 전체 프로젝트 맥락 이해
- **Notion (무료)**: 개발 진행상황 및 코드 스니펫 관리
- **Git + GitHub (무료)**: 버전 관리 및 코드 변경 이력 추적
- **Claude**: 코드 리뷰, 디버깅, 맥락 기반 협업

## 📁 프로젝트 구조

```
AutoStockTrading/
├── 📄 index.html                   # 프로젝트 로드맵
├── 📄 README.md                    # 프로젝트 설명
├── 📄 requirements.txt             # Python 패키지 목록
├── 📄 .env                         # 환경변수 (API 키 등)
├── 📄 .gitignore                   # Git 제외 파일 목록
├── 📄 config.yaml                  # 설정 파일
│
├── 📁 src/                         # 메인 소스 코드
│   ├── 📄 main.py                  # 프로그램 진입점
│   ├── 📁 api/                     # 키움 API 관련
│   │   ├── 📄 __init__.py
│   │   ├── 📄 kiwoom_client.py     # REST API 클라이언트
│   │   ├── 📄 auth.py              # OAuth 인증
│   │   └── 📄 websocket_client.py  # 실시간 데이터
│   ├── 📁 strategies/              # 매매 전략 (TA-Lib 기반)
│   │   ├── 📄 __init__.py
│   │   ├── 📄 base_strategy.py     # 전략 기본 클래스
│   │   ├── 📄 moving_average_strategy.py # 이동평균 전략
│   │   ├── 📄 bollinger_band_strategy.py # 볼린저 밴드 전략
│   │   ├── 📄 rsi_strategy.py      # RSI 전략
│   │   └── 📄 macd_strategy.py     # MACD 전략
│   ├── 📁 data/                    # 데이터 처리
│   │   ├── 📄 __init__.py
│   │   ├── 📄 collector.py         # pykrx 데이터 수집
│   │   ├── 📄 processor.py         # 데이터 전처리
│   │   ├── 📄 database.py          # SQLite 관리
│   │   ├── 📄 indicators.py        # TA-Lib 지표 계산
│   │   ├── 📄 indicator.py         # 지표 헬퍼 유틸리티
│   │   ├── 📄 stock_filter.py      # 종목 필터링 시스템
│   │   ├── 📄 trading_calendar.py  # 거래일 관리
│   │   └── 📄 stock_data_manager.py # 주식 데이터 관리
│   ├── 📁 trading/                 # 매매 관련
│   │   ├── 📄 __init__.py
│   │   ├── 📄 order_manager.py     # 주문 관리
│   │   ├── 📄 portfolio.py         # 포트폴리오 관리
│   │   ├── 📄 risk_manager.py      # 위험 관리
│   │   ├── 📄 backtest.py          # 백테스팅 엔진
│   │   ├── 📄 parallel_backtest.py # 병렬 백테스팅 엔진
│   │   ├── 📄 cache_manager.py     # 백테스팅 캐시 시스템
│   │   ├── 📄 batch_optimizer.py   # 배치 처리 최적화
│   │   └── 📄 optimized_backtest.py # 통합 최적화 백테스팅
│   └── 📁 ui/                      # Streamlit UI
│       ├── 📄 __init__.py
│       ├── 📄 dashboard.py         # 메인 대시보드
│       ├── 📄 components.py        # UI 컴포넌트
│       ├── 📄 charts.py            # 차트 및 시각화
│       └── 📄 optimization.py      # 매개변수 최적화 UI
├── 📁 tests/                       # 테스트 코드
├── 📁 data/                        # 데이터 파일
├── 📁 docs/                        # 문서 (TA-Lib 가이드 포함)
├── 📁 scripts/                     # 유틸리티 스크립트
│   ├── 📄 setup.py                 # 초기 설정
│   ├── 📄 backup.py                # 데이터 백업
│   ├── 📄 data_update.py           # 데이터 업데이트
│   └── 📄 parameter_optimization.py # 매개변수 최적화
└── 📁 streamlit_app/               # Streamlit 앱
```

## 🚀 설치 및 실행

### 필수 요구사항
- Python 3.13 이상
- TA-Lib 라이브러리 (Windows: whl 파일 설치 필요)
- 키움증권 계좌 (실제 매매용, 모의투자 계좌도 가능)
- 키움 REST API 개발자 계정 (선택사항)

### 설치 과정

1. **저장소 클론**
   ```bash
   git clone https://github.com/your-username/AutoStockTrading.git
   cd AutoStockTrading
   ```

2. **가상환경 생성 및 활성화**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **TA-Lib 설치 (Windows)**
   ```bash
   # Windows용 whl 파일 다운로드 후 설치
   pip install TA_Lib-0.4.25-cp313-cp313-win_amd64.whl
   ```

4. **필수 패키지 설치**
   ```bash
   pip install -r requirements.txt
   ```

5. **환경변수 설정**
   ```bash
   # .env 파일 생성 및 API 키 설정 (선택사항)
   cp .env.example .env
   # .env 파일에 키움 API 키와 시크릿 입력 (실시간 데이터용)
   ```

6. **Streamlit 앱 실행**
   ```bash
   streamlit run streamlit_app/app.py
   ```

## 📊 주요 기능

### 1. 데이터 수집 및 저장
- **pykrx 기반**: 충분한 과거 OHLCV 데이터 수집
- **자동 업데이트**: 일정 주기로 최신 데이터 자동 수집
- **SQLite 저장**: 경량화된 로컬 데이터베이스
- **데이터 검증**: 결측치 처리 및 이상치 탐지

### 2. TA-Lib 기술적 분석
- **추세 지표**: SMA, EMA, MACD, ADX, Parabolic SAR, 볼린저 밴드
- **모멘텀 지표**: RSI, Stochastic, Williams %R, ROC, CCI, MFI
- **변동성 지표**: ATR, 볼린저 밴드, Donchian Channel
- **거래량 지표**: OBV, A/D Line, ADOSC
- **패턴 인식**: 150+ 캔들스틱 패턴 자동 감지

### 3. 매개변수 최적화
- **백테스팅 기반**: 과거 데이터를 통한 최적 파라미터 탐색
- **그리드 서치**: 지표별 최적 기간 및 임계값 자동 탐색
- **성과 지표**: 수익률, 샤프 비율, 최대 낙폭 기반 평가
- **오버피팅 방지**: 아웃오브샘플 테스트로 검증

### 4. 스윙 트레이딩 전략
- **권장 설정**: 스윙 트레이딩에 최적화된 기본 파라미터
- **다중 시간프레임**: 일봉 위주, 시간봉 보조 활용
- **리스크 관리**: 100만원 규모에 적합한 포지션 사이징
- **분산투자**: 상관관계 낮은 종목 조합

### 5. 실시간 모니터링
- 실시간 시세 차트 (Plotly 인터랙티브 차트)
- 포트폴리오 현황 대시보드
- 매매 신호 실시간 알림
- 체결 내역 모니터링

## 📈 개발 로드맵

### 1주차: 데이터 기반 구축 및 TA-Lib 구현
- **1일**: 환경 설정 & TA-Lib 설치
- **2일**: pykrx 데이터 수집 모듈 구현
- **3일**: SQLite 데이터베이스 구축
- **4일**: TA-Lib 기본 지표 구현
- **5일**: 백테스팅 시스템 개발
- **6-7일**: 매개변수 최적화 시스템

### 2주차: UI 개발 및 실전 연동
- **8일**: Streamlit UI 기본 구조
- **9일**: 전략 설정 및 백테스팅 UI
- **10일**: 실시간 모니터링 UI
- **11일**: 키움 API 실전 연동 (선택)
- **12일**: 최적화 & 테스트
- **13-14일**: 실전 검증 & 런칭

## 💡 TA-Lib 활용 예시

### 기본 지표 구현
```python
import talib
import pandas as pd

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV 데이터로 모든 주요 지표 계산"""
    
    # 추세 지표
    df['SMA_20'] = talib.SMA(df['close'], timeperiod=20)
    df['EMA_12'] = talib.EMA(df['close'], timeperiod=12)
    df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(
        df['close'], fastperiod=12, slowperiod=26, signalperiod=9
    )
    
    # 모멘텀 지표
    df['RSI'] = talib.RSI(df['close'], timeperiod=14)
    df['STOCH_K'], df['STOCH_D'] = talib.STOCH(
        df['high'], df['low'], df['close'], 
        fastk_period=14, slowk_period=3, slowd_period=3
    )
    
    # 변동성 지표
    df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
    df['BB_upper'], df['BB_middle'], df['BB_lower'] = talib.BBANDS(
        df['close'], timeperiod=20, nbdevup=2, nbdevdn=2
    )
    
    return df
```

### 매개변수 최적화
```python
def optimize_rsi_strategy(data: pd.DataFrame) -> dict:
    """RSI 전략 매개변수 최적화"""
    
    best_params = {'period': 14, 'oversold': 30, 'overbought': 70}
    best_return = 0
    
    for period in range(7, 30):
        for oversold in range(20, 40, 5):
            for overbought in range(60, 80, 5):
                rsi = talib.RSI(data['close'], timeperiod=period)
                returns = backtest_rsi_strategy(data, rsi, oversold, overbought)
                
                if returns > best_return:
                    best_return = returns
                    best_params = {
                        'period': period,
                        'oversold': oversold, 
                        'overbought': overbought
                    }
    
    return best_params
```

### 스윙 트레이딩 권장 설정
```python
# 스윙 트레이딩 최적화 파라미터
SWING_TRADING_PARAMS = {
    'RSI': {'period': 14, 'oversold': 30, 'overbought': 70},
    'MACD': {'fast': 12, 'slow': 26, 'signal': 9},
    'BB': {'period': 20, 'deviation': 2.0},
    'STOCH': {'k_period': 14, 'd_period': 3},
    'ATR': {'period': 14}
}
```

## 📚 데이터 및 지표 가이드

### OHLCV 데이터로 사용 가능한 지표 (95% 이상)
- **추세 분석**: 이동평균선, MACD, ADX, Parabolic SAR
- **모멘텀 분석**: RSI, Stochastic, Williams %R, CCI
- **변동성 분석**: 볼린저 밴드, ATR, Donchian Channel
- **거래량 분석**: OBV, A/D Line, Money Flow Index
- **패턴 인식**: 150+ 캔들스틱 패턴

### 데이터 수집 전략
```python
from pykrx import stock
import pandas as pd

def collect_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """pykrx를 통한 종목별 OHLCV 데이터 수집"""
    
    df = stock.get_market_ohlcv(start_date, end_date, symbol)
    df.columns = ['open', 'high', 'low', 'close', 'volume']
    df['symbol'] = symbol
    df.reset_index(inplace=True)
    df.rename(columns={'날짜': 'date'}, inplace=True)
    
    return df
```

### SQLite 데이터베이스 스키마
```sql
CREATE TABLE stock_data (
    symbol TEXT,
    date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE indicators (
    symbol TEXT,
    date TEXT,
    rsi REAL,
    macd REAL,
    bb_upper REAL,
    bb_lower REAL,
    atr REAL,
    PRIMARY KEY (symbol, date)
);
```

## ⚠️ 스윙 트레이딩 주의사항

### 리스크 관리
- **100만원 규모**: 분산투자 3-5 종목 권장
- **손절매**: 2-3% 손실 시 자동 손절
- **포지션 사이징**: 종목당 최대 20-30만원
- **상관관계**: 서로 다른 섹터 종목 선택

### 백테스팅 중요성
- **충분한 데이터**: 최소 200-500일 과거 데이터 필요
- **아웃오브샘플**: 전체 데이터의 20-30%는 검증용으로 분리
- **과적합 방지**: 너무 복잡한 전략보다 단순한 전략 선호
- **실전 검증**: 소액으로 실전 테스트 후 본격 투자

### 개발 우선순위
1. **데이터 수집**: pykrx 기반 OHLCV 데이터 수집 시스템
2. **TA-Lib 지표**: 기본 기술적 분석 지표 구현
3. **백테스팅**: 과거 데이터 기반 성과 검증 시스템
4. **매개변수 최적화**: 그리드 서치 기반 파라미터 최적화
5. **실전 연동**: 키움 API 연동 (선택사항)

## 📚 문서

- [API 사용법](docs/api_guide.md)
- [매매 전략 가이드](docs/strategy_guide.md)
- [배포 가이드](docs/deployment.md)
- [개발 로드맵](index.html)

## 🤝 기여 방법

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## ⚠️ 면책 조항

- 이 프로그램은 교육 및 연구 목적으로 개발되었습니다.
- **100만원 규모 스윙 트레이딩**에 최적화되었으며, 대규모 투자에는 부적합할 수 있습니다.
- TA-Lib 지표는 검증된 라이브러리이지만, 시장 상황에 따라 성과가 달라질 수 있습니다.
- 실제 투자 전 충분한 백테스팅과 소액 실전 테스트를 권장합니다.
- 투자 손실에 대한 책임은 사용자에게 있습니다.

## 🙋‍♂️ 문의

- **GitHub Issues**: [Issues 페이지](https://github.com/your-username/AutoStockTrading/issues)
- **Email**: your-email@example.com
- **Blog**: [개발 블로그](https://your-blog.com)

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=your-username/AutoStockTrading&type=Date)](https://star-history.com/#your-username/AutoStockTrading&Date)

---

<div align="center">
  <strong>🚀 2주 만에 완성하는 알고리즘 매매 시스템 🚀</strong><br>
  Made with ❤️ by AI-Human Collaboration
</div>

**프로젝트 업데이트**: 2024년 7월 TA-Lib 기반 스윙 트레이딩 시스템으로 구조 개편 완료
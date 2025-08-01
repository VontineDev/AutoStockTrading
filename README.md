# 🚀 키움 API 알고리즘 매매 프로그램

> **2주 완성 목표의 1인 개발 프로젝트**  
> Python 3.10 + TA-Lib + Streamlit을 활용한 스윙 트레이딩 자동매매 시스템

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
- **Python 3.10**: 최신 안정 버전
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
├── src/
│   ├── data/              # 데이터 수집 및 관리
│   ├── strategies/        # TA-Lib 기반 매매 전략
│   ├── trading/           # 백테스팅 및 포트폴리오 관리
│   ├── ui/                # UI 아키텍처 (SOLID 원칙 기반)
│   │   ├── services/      # 서비스 계층 (비즈니스 로직)
│   │   │   ├── data_service.py      # 데이터 서비스
│   │   │   ├── strategy_service.py  # 전략 서비스
│   │   │   ├── backtest_service.py  # 백테스트 서비스
│   │   │   └── portfolio_service.py # 포트폴리오 서비스
│   │   └── components/    # UI 컴포넌트 계층
│   │       ├── charts.py     # 차트 컴포넌트 (Plotly 기반)
│   │       ├── widgets.py    # 위젯 컴포넌트 (입력/선택)
│   │       ├── tables.py     # 테이블 컴포넌트 (데이터 표시)
│   │       └── forms.py      # 폼 컴포넌트 (사용자 입력)
│   └── main.py            # CLI 메인 진입점
├── streamlit_app/         # 웹 UI 애플리케이션
│   ├── main_app.py        # Streamlit 메인 진입점
│   └── pages/             # 페이지 계층
│       ├── dashboard.py   # 주식 분석 대시보드
│       └── backtest.py    # 백테스팅 페이지
├── scripts/
│   ├── data_update.py     # 데이터 수집 스크립트
│   ├── check_data_status_legacy.py  # 레거시 데이터 확인 도구
│   └── utils/             # 유틸리티 함수들
├── data/                  # SQLite 데이터베이스
├── backtest_results/      # 백테스팅 결과 저장
├── tests/                 # 단위 테스트
└── docs/                  # 문서화
```

### 📂 주요 디렉토리 설명

#### 🏗️ **UI 아키텍처 (SOLID 원칙 기반)**
- **`src/ui/services/`**: 서비스 계층 - UI와 비즈니스 로직 분리
  - `DataService`: 데이터 관리 및 캐싱
  - `StrategyService`: 매매 전략 관리 
  - `BacktestService`: 백테스팅 및 성과 분석
  - `PortfolioService`: 포트폴리오 관리 및 리스크 계산
- **`src/ui/components/`**: 재사용 가능한 UI 컴포넌트
  - `ChartComponent`: Plotly 기반 인터랙티브 차트
  - `WidgetComponent`: 입력/선택 위젯들
  - `TableComponent`: 데이터 테이블 및 성과 지표
  - `FormComponent`: 사용자 입력 폼

#### 📱 **웹 애플리케이션**
- **`streamlit_app/main_app.py`**: 메인 진입점 및 네비게이션
- **`streamlit_app/pages/`**: 각 기능별 페이지
  - `dashboard.py`: 실시간 차트, 기술적 분석, 종목 분석
  - `backtest.py`: 전략 백테스팅, 성과 분석, 매개변수 최적화

#### 🔧 **핵심 시스템**
- **`src/data/`**: 데이터 수집, 관리, 지표 계산
- **`src/strategies/`**: TA-Lib 기반 매매 전략들
- **`src/trading/`**: 백테스팅 엔진, 포트폴리오 관리
- **`scripts/`**: 독립 실행 스크립트 및 유틸리티

## 🚀 설치 및 실행

### 필수 요구사항
- Python 3.10 이상
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
   streamlit run streamlit_app/main_app.py
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

### 3. 스윙 트레이딩 전략
- **권장 설정**: 스윙 트레이딩에 최적화된 기본 파라미터
- **다중 시간프레임**: 일봉 위주, 시간봉 보조 활용
- **리스크 관리**: 100만원 규모에 적합한 포지션 사이징
- **분산투자**: 상관관계 낮은 종목 조합

### 4. 실시간 모니터링
- 실시간 시세 차트 (Plotly 인터랙티브 차트)
- 포트폴리오 현황 대시보드
- 매매 신호 실시간 알림
- 체결 내역 모니터링

## 🏗️ UI 아키텍처 (SOLID 원칙 기반)

### 계층화된 설계
```
┌─────────────────┐
│   Pages Layer   │  ← 사용자 인터페이스 (Dashboard, Backtest)
├─────────────────┤
│ Components Layer│  ← 재사용 가능한 UI 컴포넌트
├─────────────────┤
│  Services Layer │  ← 비즈니스 로직 (Data, Strategy, Portfolio)
├─────────────────┤
│   Data Layer    │  ← 데이터 관리 (Database, Indicators)
└─────────────────┘
```

### 🔧 서비스 계층 (Services Layer)
- **DataService**: 종목 데이터 관리, 캐싱, 실시간 조회
- **StrategyService**: 매매 전략 관리, 신호 생성, 매개변수 검증
- **BacktestService**: 백테스팅 실행, 성과 분석, 최적화
- **PortfolioService**: 포트폴리오 관리, 리스크 계산, 포지션 사이징

### 🎨 컴포넌트 계층 (Components Layer)
- **ChartComponent**: Plotly 기반 인터랙티브 차트 (캔들스틱, 라인, 성과)
- **WidgetComponent**: 사용자 입력 위젯 (선택기, 슬라이더, 버튼)
- **TableComponent**: 데이터 테이블 및 성과 지표 표시
- **FormComponent**: 사용자 입력 폼 및 검증

### 📱 페이지 계층 (Pages Layer)
- **Dashboard**: 실시간 차트, 기술적 분석, 종목 분석
- **Backtest**: 전략 백테스팅, 성과 비교, 매개변수 최적화
- **Data Management**: 종목 추가, 데이터 업데이트, 상태 모니터링
- **Settings**: 시스템 설정, API 키 관리

### ✨ 아키텍처 장점
- **단일 책임 원칙**: 각 컴포넌트는 명확한 단일 책임
- **의존성 역전**: 서비스 인터페이스를 통한 느슨한 결합
- **재사용성**: 모듈화된 컴포넌트로 높은 재사용성
- **확장성**: 새로운 전략이나 기능 추가 용이
- **테스트 용이성**: 각 계층별 독립적인 단위 테스트 가능

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

## 🔧 핵심 전략

### 📊 구현된 TA-Lib 전략
1. **MACD 전략**: 추세 추종 + 모멘텀 결합
2. **RSI 전략**: 과매수/과매도 구간 활용
3. **볼린저 밴드**: 변동성 기반 평균 회귀
4. **이동평균**: 단순/지수 이동평균 교차

### 🎯 스윙 트레이딩 최적화
- **보유 기간**: 3-15일 (단기 변동성 활용)
- **포지션 크기**: 종목당 최대 25% (리스크 분산)
- **손절매**: 3% 고정 (리스크 관리)
- **분산투자**: 최대 5종목 동시 보유

## 🛡️ 리스크 관리

### 💰 100만원 규모 최적화
```python
# 포트폴리오 설정 예시
TOTAL_CAPITAL = 1_000_000     # 총 투자금
MAX_STOCKS = 5                # 최대 보유 종목
MAX_POSITION = 0.25           # 종목당 최대 25%
STOP_LOSS = 0.03              # 3% 손절매
```

### 📈 성과 지표
- **샤프 비율**: 위험 대비 수익률
- **최대낙폭(MDD)**: 최대 손실폭 추적
- **승률**: 수익 거래 비율
- **수익/손실 비율**: 평균 수익 대 평균 손실

## 🚨 주의사항

⚠️ **백테스팅 결과는 과거 데이터 기반이며, 미래 수익을 보장하지 않습니다.**

⚠️ **실거래 전 충분한 검증과 소액 테스트를 권장합니다.**

⚠️ **키움 API 연동 시 실제 계좌 정보가 필요합니다.**

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 지원 및 문의

- **GitHub Issues**: 버그 리포트 및 기능 요청
- **Wiki**: 상세 사용법 및 FAQ
- **Discussions**: 커뮤니티 질의응답

---

🎯 **100만원으로 시작하는 체계적인 알고리즘 트레이딩 여정을 응원합니다!** 🚀
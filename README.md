# 🚀 키움 API 알고리즘 매매 프로그램

> **2주 완성 목표의 1인 개발 프로젝트**  
> Python 3.13 + Streamlit + 키움 REST API를 활용한 웹 기반 자동매매 시스템

## 📋 프로젝트 개요

키움증권의 차세대 REST API를 활용하여 웹 기반 알고리즘 매매 프로그램을 개발합니다. 별도 프로그램 설치 없이 브라우저에서 실시간 시세 확인, 매매 전략 설정, 포트폴리오 관리가 가능한 올인원 솔루션을 제공합니다.

### 🎯 주요 특징

- **웹 기반**: Windows/Mac/Linux 모든 운영체제 지원
- **REST API**: JSON 기반의 간단한 데이터 처리
- **실시간 모니터링**: 웹소켓을 통한 실시간 시세 및 체결 정보
- **다양한 전략**: 이동평균, 볼린저 밴드, RSI 등 기술적 지표 활용
- **백테스팅**: 과거 데이터를 통한 전략 검증 및 최적화
- **직관적 UI**: Streamlit 기반의 사용자 친화적 인터페이스

## 🛠️ 기술 스택

### 핵심 기술
- **Python 3.13**: 최신 안정 버전 (2024.10 릴리즈)
- **키움 REST API**: 차세대 웹 기반 API (2025.3 출시)
- **Streamlit**: 빠른 웹 UI 개발 프레임워크
- **SQLite**: 매매 이력 및 설정 데이터 저장

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
│   ├── 📁 strategies/              # 매매 전략
│   │   ├── 📄 __init__.py
│   │   ├── 📄 moving_average.py    # 이동평균 전략
│   │   ├── 📄 bollinger_band.py    # 볼린저 밴드
│   │   └── 📄 rsi_strategy.py      # RSI 전략
│   ├── 📁 data/                    # 데이터 처리
│   │   ├── 📄 __init__.py
│   │   ├── 📄 collector.py         # 데이터 수집
│   │   ├── 📄 processor.py         # 데이터 전처리
│   │   └── 📄 database.py          # SQLite 관리
│   ├── 📁 trading/                 # 매매 관련
│   │   ├── 📄 __init__.py
│   │   ├── 📄 order_manager.py     # 주문 관리
│   │   ├── 📄 portfolio.py         # 포트폴리오 관리
│   │   └── 📄 risk_manager.py      # 위험 관리
│   └── 📁 ui/                      # Streamlit UI
│       ├── 📄 __init__.py
│       ├── 📄 dashboard.py         # 메인 대시보드
│       ├── 📄 components.py        # UI 컴포넌트
│       └── 📄 charts.py            # 차트 및 시각화
├── 📁 tests/                       # 테스트 코드
├── 📁 data/                        # 데이터 파일
├── 📁 docs/                        # 문서
├── 📁 scripts/                     # 유틸리티 스크립트
└── 📁 streamlit_app/               # Streamlit 앱
```

## 🚀 설치 및 실행

### 필수 요구사항
- Python 3.13 이상
- 키움증권 계좌 (모의투자 계좌 포함)
- 키움 REST API 개발자 계정

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

3. **필수 패키지 설치**
   ```bash
   pip install -r requirements.txt
   ```

4. **환경변수 설정**
   ```bash
   # .env 파일 생성 및 API 키 설정
   cp .env.example .env
   # .env 파일에 키움 API 키와 시크릿 입력
   ```

5. **Streamlit 앱 실행**
   ```bash
   streamlit run streamlit_app/app.py
   ```

## 📊 주요 기능

### 1. 실시간 모니터링
- 실시간 시세 차트 (Plotly 인터랙티브 차트)
- 포트폴리오 현황 대시보드
- 매매 신호 실시간 알림
- 체결 내역 모니터링

### 2. 매매 전략
- **이동평균**: 단기/장기 이동평균 교차 전략
- **볼린저 밴드**: 표준편차 기반 매매 신호
- **RSI**: 과매수/과매도 구간 활용
- **커스텀 전략**: 사용자 정의 전략 개발 가능

### 3. 위험 관리
- 손절/익절 자동 설정
- 포지션 사이즈 관리
- 최대 손실 한도 설정
- 일일 매매 한도 관리

### 4. 백테스팅
- 과거 데이터 기반 전략 검증
- 수익률, 최대 낙폭, 샤프 비율 계산
- 파라미터 최적화
- 성과 분석 리포트

## 📈 개발 로드맵

### 1주차: 기반 구축 및 API 연동
- **1일**: 환경 설정 & 키움 API 설치
- **2일**: API 연결 테스트
- **3일**: 데이터 수집 모듈
- **4일**: 기본 알고리즘 구현
- **5일**: 주문 관리 시스템
- **6-7일**: 백테스팅 & 검증

### 2주차: UI 개발 및 최종 완성
- **8일**: Streamlit UI 기본 구조
- **9일**: 거래 관리 UI
- **10일**: 전략 설정 UI
- **11일**: 모니터링 & 알림
- **12일**: 최적화 & 테스트
- **13-14일**: 실전 배포 & 런칭

## 🔧 코딩 규칙

### 네이밍 컨벤션
- **클래스**: PascalCase (예: `KiwoomApiClient`, `TradingStrategy`)
- **함수/변수**: snake_case (예: `get_stock_price`, `current_price`)
- **상수**: UPPER_SNAKE_CASE (예: `MAX_RETRY_COUNT`, `API_TIMEOUT`)
- **파일명**: snake_case (예: `kiwoom_client.py`, `trading_strategy.py`)

### 필수 사항
- 모든 함수에 타입 힌트 적용
- API 키 하드코딩 절대 금지 (환경변수 사용)
- 모든 API 호출에 예외 처리 및 재시도 로직
- logging 모듈 사용 (print 금지)
- 테스트 커버리지 80% 이상 목표

## 🛡️ 보안 가이드

### API 키 관리
```python
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('KIWOOM_API_KEY')
API_SECRET = os.getenv('KIWOOM_API_SECRET')
```

### 환경변수 설정 (.env)
```env
KIWOOM_API_KEY=your_api_key_here
KIWOOM_API_SECRET=your_api_secret_here
ACCOUNT_NUMBER=your_account_number_here
```

## 📝 사용법

### 기본 실행
```bash
# Streamlit 앱 실행
streamlit run streamlit_app/app.py

# 브라우저에서 http://localhost:8501 접속
```

### 매매 전략 설정
1. 사이드바에서 전략 선택
2. 파라미터 조정 (이동평균 기간, RSI 임계값 등)
3. 백테스팅으로 성과 확인
4. 자동매매 활성화

### 모니터링
- 실시간 차트에서 매매 신호 확인
- 포트폴리오 현황 실시간 업데이트
- 로그 창에서 매매 내역 모니터링

## 🧪 테스트

```bash
# 단위 테스트 실행
python -m pytest tests/

# 특정 모듈 테스트
python -m pytest tests/test_api.py

# 커버리지 확인
python -m pytest --cov=src tests/
```

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
- 실제 투자에 사용하기 전 충분한 검증과 테스트를 수행하세요.
- 투자 손실에 대한 책임은 사용자에게 있습니다.
- 키움증권 API 이용약관을 준수해주세요.

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
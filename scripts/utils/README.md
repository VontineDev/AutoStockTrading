# 유틸리티 스크립트 모음

## 📁 폴더 목적
프로젝트 관리 및 유지보수를 위한 독립 실행 스크립트들을 모아둔 폴더입니다.

## 📋 포함된 스크립트들

### 🔧 setup.py - 프로젝트 초기화
```bash
python scripts/utils/setup.py
```
- 가상환경 활성화 확인
- 필수 디렉토리 생성 (data, logs 등)
- SQLite 데이터베이스 초기화
- 기본 설정 파일 생성

### 💾 backup.py - 데이터 백업
```bash
python scripts/utils/backup.py
```
- 데이터베이스 백업 (trading.db)
- 로그 파일 백업
- 설정 파일 백업 (config.yaml, .env)
- 압축 및 날짜별 버전 관리
- 자동 정리 (30일 이상 파일 삭제)

## 🎯 사용 시나리오

### 초기 환경 설정
```bash
# 1. 프로젝트 클론 후 초기 설정
python scripts/utils/setup.py

# 2. 데이터 업데이트 (메인 스크립트)
python scripts/data_update.py --top-kospi 30

# 3. 백테스팅 실행 (메인 프로그램)
python src/main.py backtest --symbols 005930 --strategy macd
```

### 정기 유지보수
```bash
# 주기적 백업
python scripts/utils/backup.py
```

## 📝 vs 메인 스크립트들

| 구분 | 위치 | 용도 | 호출 방법 |
|------|------|------|-----------|
| **메인** | `scripts/data_update.py` | 일상 데이터 업데이트 | `main.py`에서 호출 |
| **유틸** | `scripts/utils/setup.py` | 초기 환경 설정 | 독립 실행 |
| **유틸** | `scripts/utils/backup.py` | 백업 및 유지보수 | 독립 실행 |

## ⚠️ 주의사항
- 모든 스크립트는 프로젝트 루트에서 실행해야 합니다
- 가상환경 활성화 필수
- 환경변수 설정 확인 (.env 파일) 
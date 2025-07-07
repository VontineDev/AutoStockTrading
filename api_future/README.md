# 키움 API 모듈 (향후 사용 예정)

## 📁 폴더 목적
이 폴더는 2주차 실시간 연동 단계에서 사용할 키움증권 API 모듈들을 보관합니다.

## 📋 포함된 파일들

### 🔐 인증 모듈
- `auth.py` - OAuth 토큰 발급/폐기 처리
- 환경변수 기반 API 키 관리

### 🌐 REST API 클라이언트
- `kiwoom_client.py` - 계좌 정보 조회 등 REST API 호출
- 타임아웃, 에러 처리 포함

### 📡 WebSocket 클라이언트  
- `websocket_client.py` - 실시간 시세/체결 데이터 수신
- 비동기 처리, 자동 재연결 지원

## 🎯 개발 일정
- **1주차**: pykrx 기반 과거 데이터 분석 (현재)
- **2주차**: 키움 API 실시간 연동 (이 모듈들 사용)

## 🔧 사용 시점
```bash
# 2주차 실시간 연동 시 다시 src/api/ 로 이동
Move-Item -Path "api_future\*" -Destination "src\api\" -Force
```

## ⚠️ 주의사항
- 실제 키움증권 API 키가 필요합니다
- `.env` 파일에 `KIWOOM_API_KEY`, `KIWOOM_API_SECRET` 설정 필요
- 개발/운영 환경 분리 권장 
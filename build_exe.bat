@echo off
echo ======================================
echo Auto Stock Trading 실행파일 빌드 시작
echo ======================================

REM 가상환경 활성화
IF EXIST venv (
    echo 가상환경 활성화 중...
    call .\venv\Scripts\activate
) ELSE (
    echo 경고: 가상환경을 찾을 수 없습니다.
)

REM 기존 빌드 결과 정리
IF EXIST dist (
    echo 기존 빌드 결과 삭제 중...
    rmdir /s /q dist
)

IF EXIST build (
    echo 기존 빌드 캐시 삭제 중...
    rmdir /s /q build
)

echo.
echo ======================================
echo CLI 버전 실행파일 빌드 중...
echo ======================================
pyinstaller build_exe.spec --clean --noconfirm

IF %ERRORLEVEL% NEQ 0 (
    echo CLI 빌드 실패!
    pause
    exit /b 1
)

echo.
echo ======================================
echo 웹 앱 버전 실행파일 빌드 중...
echo ======================================
pyinstaller build_webapp.spec --clean --noconfirm

IF %ERRORLEVEL% NEQ 0 (
    echo 웹앱 빌드 실패!
    pause
    exit /b 1
)

echo.
echo ======================================
echo 빌드 완료!
echo ======================================
echo CLI 실행파일: dist\AutoStockTrading.exe
echo 웹앱 실행파일: dist\AutoStockTradingWeb.exe
echo.
echo 사용법:
echo - CLI: AutoStockTrading.exe --help
echo - 웹앱: AutoStockTradingWeb.exe (브라우저에서 자동 실행)
echo ======================================

pause 
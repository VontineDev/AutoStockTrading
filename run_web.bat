@echo off
REM 가상환경 활성화 (venv 폴더가 있다면)
IF EXIST venv (
    call .\venv\Scripts\activate
)
REM 웹 서버 실행
python src\main.py web
pause 
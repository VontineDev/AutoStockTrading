#!/usr/bin/env python3
"""
AutoStockTrading Web App Launcher
실행파일에서 Streamlit 웹 앱을 시작하는 래퍼 스크립트
"""

import os
import sys
import threading
import time
import webbrowser
import subprocess
from pathlib import Path

def get_free_port():
    """사용 가능한 포트를 찾아 반환"""
    import socket
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

def open_browser(url, delay=3):
    """지정된 시간 후 브라우저 열기"""
    time.sleep(delay)
    webbrowser.open(url)

def main():
    """웹 앱 시작"""
    print("=" * 50)
    print("🚀 AutoStockTrading 웹 앱 시작 중...")
    print("=" * 50)
    
    # 현재 스크립트의 디렉토리를 기준으로 프로젝트 루트 설정
    if getattr(sys, 'frozen', False):
        # 실행파일에서 실행될 때
        application_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        os.chdir(application_path)
    else:
        # 개발 환경에서 실행될 때
        application_path = Path(__file__).parent
        os.chdir(application_path)
    
    # Streamlit 앱 파일 경로
    app_file = "streamlit_app/main_app.py"
    
    if not os.path.exists(app_file):
        print(f"❌ 오류: {app_file} 파일을 찾을 수 없습니다.")
        print(f"현재 디렉토리: {os.getcwd()}")
        input("계속하려면 Enter를 누르세요...")
        return
    
    # 사용 가능한 포트 찾기
    port = get_free_port()
    url = f"http://localhost:{port}"
    
    print(f"📍 포트: {port}")
    print(f"🌐 URL: {url}")
    print("⏳ 웹 서버 시작 중...")
    
    # 브라우저 자동 열기 스레드 시작
    browser_thread = threading.Thread(target=open_browser, args=(url,))
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        # Streamlit 실행
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            app_file,
            "--server.port", str(port),
            "--server.headless", "true",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false",
            "--browser.gatherUsageStats", "false"
        ]
        
        print(f"🚀 명령어 실행: {' '.join(cmd)}")
        print("=" * 50)
        print("🎯 웹 앱이 시작되었습니다!")
        print(f"📱 브라우저에서 {url} 주소로 접속하세요.")
        print("🛑 종료하려면 Ctrl+C를 누르세요.")
        print("=" * 50)
        
        # Streamlit 프로세스 시작
        process = subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 종료되었습니다.")
    except subprocess.CalledProcessError as e:
        print(f"❌ 오류 발생: {e}")
        print("⚠️  다음 사항을 확인해주세요:")
        print("   1. Streamlit이 설치되어 있는지 확인")
        print("   2. 필요한 모든 모듈이 설치되어 있는지 확인")
        print("   3. 포트가 사용 중인지 확인")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
    finally:
        print("\n👋 AutoStockTrading 웹 앱을 종료합니다.")
        input("계속하려면 Enter를 누르세요...")

if __name__ == "__main__":
    main() 
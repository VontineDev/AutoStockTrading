import logging
import sys
from src.config_loader import get_project_root

logger = logging.getLogger(__name__)
PROJECT_ROOT = get_project_root()

def run_streamlit():
    """Streamlit 웹 앱 실행"""
    try:
        import streamlit.web.cli as stcli

        app_file = PROJECT_ROOT / "streamlit_app" / "app.py"

        if not app_file.exists():
            logger.error(f"Streamlit 앱 파일이 없습니다: {app_file}")
            logger.info("streamlit_app/app.py를 생성해주세요.")
            return

        logger.info("Streamlit 웹 앱을 시작합니다...")
        logger.info("브라우저에서 http://localhost:8501 을 열어주세요.")

        sys.argv = ["streamlit", "run", str(app_file)]
        stcli.main()

    except Exception as e:
        logger.error(f"Streamlit 실행 실패: {e}")
        logger.info(
            "Streamlit이 설치되지 않았을 수 있습니다. 'pip install streamlit'로 설치해주세요."
        )

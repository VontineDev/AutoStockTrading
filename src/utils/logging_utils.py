import logging
import functools
import os
from pathlib import Path
from datetime import datetime

LOG_FUNCTION_TRACE = os.getenv("LOG_FUNCTION_TRACE", "0") == "1"


def log_function_trace(func):
    """함수 진입/종료를 로깅하는 데코레이터 (on/off 가능)"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if LOG_FUNCTION_TRACE:
            logger = logging.getLogger(func.__module__)
            logger.info(f"▶️ {func.__qualname__} 진입")
        result = func(*args, **kwargs)
        if LOG_FUNCTION_TRACE:
            logger = logging.getLogger(func.__module__)
            logger.info(f"⏹️ {func.__qualname__} 종료")
        return result

    return wrapper


def setup_logging(log_dir: str = None, log_level: int = logging.DEBUG):
    """
    Robust logging setup for both CLI and Streamlit.
    Creates logs directory, sets up file and stream handlers, and sets DEBUG level by default.
    Safe to call multiple times (idempotent).
    """
    if log_dir is None:
        project_root = Path(__file__).parent.parent.parent
        log_dir = project_root / "logs"
    else:
        log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"trading_{datetime.now().strftime('%Y%m%d')}.log"

    # 항상 핸들러를 생성
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    stream_handler = logging.StreamHandler()

    root_logger = logging.getLogger()
    if not root_logger.handlers or getattr(setup_logging, "_force", False):
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[file_handler, stream_handler],
            force=True
        )
        setup_logging._force = False

    # 모든 하위 로거도 DEBUG로 강제 + 핸들러 직접 추가
    for logger_name in [
        "",
        "src",
        "src.trading",
        "src.trading.backtest",
        "src.strategies",
    ]:
        lgr = logging.getLogger(logger_name)
        lgr.setLevel(logging.DEBUG)
        if not any(isinstance(h, logging.FileHandler) for h in lgr.handlers):
            lgr.addHandler(file_handler)
        if not any(isinstance(h, logging.StreamHandler) for h in lgr.handlers):
            lgr.addHandler(stream_handler)

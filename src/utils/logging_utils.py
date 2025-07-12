import logging
import functools
import os

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
#!/usr/bin/env python3
"""
TA-Lib 스윙 트레이딩 자동매매 시스템 메인 진입점
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, current_dir)

try:
    from src.cli import main as cli_main
except ImportError:
    try:
        from cli import main as cli_main
    except ImportError:
        # 실행파일 환경에서의 대안
        import importlib.util
        cli_path = os.path.join(current_dir, "cli.py")
        spec = importlib.util.spec_from_file_location("cli", cli_path)
        if spec and spec.loader:
            cli_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cli_module)
            cli_main = cli_module.main
        else:
            raise ImportError("Unable to load cli module")

if __name__ == "__main__":
    cli_main()
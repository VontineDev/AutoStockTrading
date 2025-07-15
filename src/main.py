#!/usr/bin/env python3
"""
TA-Lib 스윙 트레이딩 자동매매 시스템 메인 진입점
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from cli import main as cli_main

if __name__ == "__main__":
    cli_main()
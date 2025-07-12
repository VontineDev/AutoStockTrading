import os
import glob
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(ROOT, ".."))


def should_skip(path):
    return "venv" in path or "site-packages" in path or "__pycache__" in path


def process_file(path):
    with open(path, encoding="utf-8") as fin:
        src = fin.read()
    # 데코레이터 제거
    src = re.sub(r"^[ \t]*@log_function_trace\s*\n", "", src, flags=re.MULTILINE)
    # import 제거 (맨 앞 또는 중간에 있을 수 있음)
    src = re.sub(
        r"^[ \t]*from src\.utils\.logging_utils import log_function_trace\s*\n",
        "",
        src,
        flags=re.MULTILINE,
    )
    with open(path, "w", encoding="utf-8") as fout:
        fout.write(src)


for pyfile in glob.glob(os.path.join(PROJECT_ROOT, "**", "*.py"), recursive=True):
    if should_skip(pyfile):
        continue
    process_file(pyfile)
    print(f"Restored: {pyfile}")

print("모든 파일에서 log_function_trace 데코레이터 및 import 자동 제거 완료!")

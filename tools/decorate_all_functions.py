import os
import glob

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(ROOT, ".."))


def should_skip(path):
    return "venv" in path or "site-packages" in path or "__pycache__" in path


def process_file(path):
    with open(path, encoding="utf-8") as fin:
        lines = fin.readlines()
    new_lines = []
    imported = False
    for i, line in enumerate(lines):
        # import 추가 (맨 앞에 한 번만)
        if not imported and "log_function_trace" not in "".join(lines[:20]):
            new_lines.append("from src.utils.logging_utils import log_function_trace\n")
            imported = True
        # 함수 정의 찾기
        if line.lstrip().startswith("def ") and (
            i == 0 or not lines[i - 1].lstrip().startswith("@log_function_trace")
        ):
            indent = line[: len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}@log_function_trace\n")
        new_lines.append(line)
    with open(path, "w", encoding="utf-8") as fout:
        fout.writelines(new_lines)


for pyfile in glob.glob(os.path.join(PROJECT_ROOT, "**", "*.py"), recursive=True):
    if should_skip(pyfile):
        continue
    process_file(pyfile)
    print(f"Decorated: {pyfile}")

print("모든 함수에 log_function_trace 데코레이터 자동 적용 완료!")

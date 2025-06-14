from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

START_DATE = datetime.strptime('2025-06-14', '%Y-%m-%d')

# 1. 로드맵에서 Task, 주차, 날짜 추출
def extract_roadmap_tasks(html_path: str):
    with open(html_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    result = []
    for week_div in soup.find_all('div', class_='week'):
        # 주차 추출
        week_header = week_div.find('div', class_='week-title')
        week_text = week_header.get_text(strip=True) if week_header else ''
        week_match = re.search(r'(\d+주차)', week_text)
        week = week_match.group(1) if week_match else ''
        # 각 day-card
        for day_card in week_div.find_all('div', class_='day-card'):
            day_number_div = day_card.find('div', class_='day-number')
            day_number_text = day_number_div.get_text(strip=True) if day_number_div else ''
            # 날짜 계산
            day = ''
            if day_number_text:
                # "6-7" → 6, "13-14" → 13 등 첫 번째 숫자만 사용
                day_num_match = re.match(r'(\d+)', day_number_text)
                if day_num_match:
                    day_offset = int(day_num_match.group(1)) - 1
                    day_date = START_DATE + timedelta(days=day_offset)
                    day = day_date.strftime('%Y-%m-%d')
            # 각 task
            for task_div in day_card.find_all('div', class_='task-text'):
                task = task_div.get_text(strip=True)
                result.append({'Task': task, 'Week': week, 'Day': day})
    return result

# 2. 표 출력
def print_table(tasks):
    print(f"{'Task':<50} | {'주차':<5} | {'날짜':<10}")
    print('-'*70)
    for t in tasks:
        print(f"{t['Task']:<50} | {t['Week']:<5} | {t['Day']:<10}")

if __name__ == "__main__":
    tasks = extract_roadmap_tasks('index.html')
    print_table(tasks) 
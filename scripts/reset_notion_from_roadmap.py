import os
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import re

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
NOTION_VERSION = '2022-06-28'
START_DATE = datetime.strptime('2025-06-14', '%Y-%m-%d')

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
}

def extract_roadmap_tasks(html_path: str):
    with open(html_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    result = []
    for week_div in soup.find_all('div', class_='week'):
        week_header = week_div.find('div', class_='week-title')
        week_text = week_header.get_text(strip=True) if week_header else ''
        week_match = re.search(r'(\d+주차)', week_text)
        week = week_match.group(1) if week_match else ''
        for day_card in week_div.find_all('div', class_='day-card'):
            day_number_div = day_card.find('div', class_='day-number')
            day_number_text = day_number_div.get_text(strip=True) if day_number_div else ''
            day = ''
            if day_number_text:
                day_num_match = re.match(r'(\d+)', day_number_text)
                if day_num_match:
                    day_offset = int(day_num_match.group(1)) - 1
                    day_date = START_DATE + timedelta(days=day_offset)
                    day = day_date.strftime('%Y-%m-%d')
            for task_div in day_card.find_all('div', class_='task-text'):
                task = task_div.get_text(strip=True)
                result.append({'Task': task, 'Week': week, 'Day': day})
    return result

def fetch_all_notion_page_ids():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    page_ids = []
    has_more = True
    next_cursor = None
    while has_more:
        data = {"page_size": 100}
        if next_cursor:
            data["start_cursor"] = next_cursor
        resp = requests.post(url, headers=HEADERS, json=data)
        if resp.status_code != 200:
            print('노션 API 오류:', resp.status_code, resp.text)
            break
        res = resp.json()
        for page in res.get('results', []):
            page_ids.append(page['id'])
        has_more = res.get('has_more', False)
        next_cursor = res.get('next_cursor')
    return page_ids

def archive_notion_page(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {"archived": True}
    resp = requests.patch(url, headers=HEADERS, json=data)
    return resp.status_code == 200

def create_notion_page(task_dict):
    url = "https://api.notion.com/v1/pages"
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Task": {
                "title": [{"text": {"content": task_dict['Task']}}]
            },
            "Week": {
                "select": {"name": task_dict['Week']} if task_dict['Week'] else None
            },
            "Day": {
                "date": {"start": task_dict['Day']} if task_dict['Day'] else None
            }
        }
    }
    # None 값은 Notion API에서 허용하지 않으므로 제거
    data['properties'] = {k: v for k, v in data['properties'].items() if v and (list(v.values())[0] is not None)}
    resp = requests.post(url, headers=HEADERS, json=data)
    return resp.status_code == 200

if __name__ == "__main__":
    html_path = "index.html"
    print("로드맵에서 Task, Week, Day 추출 중...")
    tasks = extract_roadmap_tasks(html_path)
    print(f"로드맵 Task {len(tasks)}개 추출 완료.")

    print("노션 DB 기존 페이지 모두 삭제 중...")
    page_ids = fetch_all_notion_page_ids()
    for pid in page_ids:
        archive_notion_page(pid)
        time.sleep(0.2)
    print(f"{len(page_ids)}개 페이지 삭제 완료.")

    print("로드맵 Task로 노션 DB 재생성 중...")
    for t in tasks:
        create_notion_page(t)
        time.sleep(0.2)
    print(f"{len(tasks)}개 Task 생성 완료!") 
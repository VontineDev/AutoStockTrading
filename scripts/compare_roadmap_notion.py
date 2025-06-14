import re
from bs4 import BeautifulSoup
import requests
import os
import sys

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')

# 1. 로드맵(index.html)에서 Task 텍스트 추출
def extract_tasks_from_roadmap(html_path: str):
    with open(html_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    tasks = []
    for div in soup.find_all('div', class_='task-text'):
        text = div.get_text(strip=True)
        if text:
            tasks.append(text)
    return tasks

# 2. 노션 DB에서 Task 목록 추출
def fetch_notion_tasks():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = {
        "sorts": [
            {"property": "Task", "direction": "ascending"}
        ]
    }
    resp = requests.post(url, headers=headers, json=data)
    notion_tasks = []
    if resp.status_code == 200:
        for page in resp.json().get('results', []):
            prop = page['properties'].get('Task', {})
            title = ''
            if 'title' in prop and prop['title']:
                title = prop['title'][0].get('plain_text', '')
            if title:
                notion_tasks.append(title)
    else:
        print('노션 API 오류:', resp.status_code, resp.text)
    return notion_tasks

# 3. 비교 및 결과 출력
def compare_tasks(roadmap_tasks, notion_tasks):
    roadmap_set = set(roadmap_tasks)
    notion_set = set(notion_tasks)
    only_in_roadmap = roadmap_set - notion_set
    only_in_notion = notion_set - roadmap_set
    print(f"로드맵 Task 개수: {len(roadmap_tasks)}")
    print(f"노션 DB Task 개수: {len(notion_tasks)}\n")
    print("로드맵에만 있고 노션에 없는 Task:")
    for t in sorted(only_in_roadmap):
        print("-", t)
    print("\n노션에만 있고 로드맵에 없는 Task:")
    for t in sorted(only_in_notion):
        print("-", t)

if __name__ == "__main__":
    html_path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    roadmap_tasks = extract_tasks_from_roadmap(html_path)
    notion_tasks = fetch_notion_tasks()
    compare_tasks(roadmap_tasks, notion_tasks) 
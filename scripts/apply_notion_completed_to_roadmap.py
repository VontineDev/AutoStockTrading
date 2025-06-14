import os
import sys
import requests
from bs4 import BeautifulSoup
import re

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
NOTION_VERSION = '2022-06-28'

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
}

def fetch_completed_tasks_from_notion():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    completed_tasks = set()
    has_more = True
    next_cursor = None
    while has_more:
        data = {
            "filter": {
                "property": "Status",
                "status": {"equals": "완료"}
            },
            "page_size": 100
        }
        if next_cursor:
            data["start_cursor"] = next_cursor
        resp = requests.post(url, headers=HEADERS, json=data)
        if resp.status_code != 200:
            print('노션 API 오류:', resp.status_code, resp.text)
            break
        res = resp.json()
        for page in res.get('results', []):
            title = page['properties'].get('Task', {}).get('title', [])
            if title and 'plain_text' in title[0]:
                completed_tasks.add(title[0]['plain_text'])
        has_more = res.get('has_more', False)
        next_cursor = res.get('next_cursor')
    return completed_tasks

def get_all_notion_tasks() -> set:
    """노션 DB에서 전체 태스크 제목 set 반환"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    has_more = True
    next_cursor = None
    tasks = set()
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
            title = page['properties'].get('Task', {}).get('title', [])
            if title and 'plain_text' in title[0]:
                tasks.add(title[0]['plain_text'])
        has_more = res.get('has_more', False)
        next_cursor = res.get('next_cursor')
    return tasks

def get_all_roadmap_tasks(html_path: str) -> set:
    with open(html_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    all_tasks = soup.find_all('div', class_='task-text')
    tasks = set()
    for task_div in all_tasks:
        # 체크 표시(✔), 줄바꿈, 공백 등 모두 제거
        text = task_div.get_text(strip=True)
        text = re.sub(r'^✔\s*', '', text)
        text = text.replace('\n', '').strip()
        tasks.add(text)
    return tasks

def compare_tasks():
    html_path = "index.html"
    roadmap_tasks = get_all_roadmap_tasks(html_path)
    notion_tasks = get_all_notion_tasks()
    only_in_roadmap = roadmap_tasks - notion_tasks
    only_in_notion = notion_tasks - roadmap_tasks
    print("[로드맵에만 있는 태스크]")
    for t in sorted(only_in_roadmap):
        print(f"- {t}")
    print("\n[노션에만 있는 태스크]")
    for t in sorted(only_in_notion):
        print(f"- {t}")
    print(f"\n로드맵 태스크 수: {len(roadmap_tasks)}, 노션 태스크 수: {len(notion_tasks)}")

def print_notion_tasks():
    """노션 DB에서 전체 태스크(제목, 상태 등) 목록을 출력"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    has_more = True
    next_cursor = None
    print("[노션 태스크 목록]")
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
            title = page['properties'].get('Task', {}).get('title', [])
            status = page['properties'].get('Status', {}).get('status', {}).get('name', '-')
            if title and 'plain_text' in title[0]:
                print(f"- {title[0]['plain_text']} [상태: {status}]")
        has_more = res.get('has_more', False)
        next_cursor = res.get('next_cursor')

def mark_tasks_completed_and_update_progress(html_path: str, completed_tasks: set):
    with open(html_path, encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    changed = False
    all_items = soup.find_all('li', class_='task-item')
    total_tasks = len(all_items)
    completed_count = 0
    for item in all_items:
        checkbox = item.find('div', class_='task-checkbox')
        task_div = item.find('div', class_='task-text')
        if not task_div or not checkbox:
            continue
        text = task_div.get_text(strip=True)
        text = re.sub(r'^✔\s*', '', text)
        text = text.replace('\n', '').strip()
        if text in completed_tasks:
            if 'checked' not in checkbox.get('class', []):
                checkbox['class'] = checkbox.get('class', []) + ['checked']
                # 완료 스타일 적용
                task_div['style'] = task_div.get('style', '') + ';text-decoration:line-through;color:gray;'
                changed = True
        else:
            # 미완료면 checked 클래스/스타일 제거
            if 'checked' in checkbox.get('class', []):
                checkbox['class'] = [c for c in checkbox.get('class', []) if c != 'checked']
                changed = True
            # 스타일도 원복
            style = task_div.get('style', '')
            style = re.sub(r'text-decoration:line-through;color:gray;?', '', style)
            task_div['style'] = style
        if 'checked' in checkbox.get('class', []):
            completed_count += 1

    percent = int(round((completed_count / total_tasks) * 100)) if total_tasks else 0
    progress_section = soup.find('div', class_='progress-section')
    if progress_section:
        progress_text = progress_section.find('span', id='progress-percentage')
        if progress_text:
            progress_text.string = f"{percent}%"
        completed_span = progress_section.find('span', id='completed-tasks')
        total_span = progress_section.find('span', id='total-tasks')
        if completed_span:
            completed_span.string = str(completed_count)
        if total_span:
            total_span.string = str(total_tasks)
        progress_fill = progress_section.find('div', id='progress-fill')
        if progress_fill:
            progress_fill['style'] = f"width:{percent}%"

    if changed or True:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        print(f"index.html에 {completed_count}/{total_tasks}개 완료 Task 및 진행률 {percent}% 반영 완료.")
    else:
        print("변경된 Task가 없습니다.")

if __name__ == "__main__":
    if '--compare-tasks' in sys.argv:
        compare_tasks()
        sys.exit(0)
    if '--list-tasks' in sys.argv:
        print_notion_tasks()
        sys.exit(0)
    html_path = "index.html"
    print("노션에서 완료 Task 불러오는 중...")
    completed_tasks = fetch_completed_tasks_from_notion()
    print(f"완료 Task {len(completed_tasks)}개 불러옴.")
    print("index.html에 완료 Task 및 진행률 반영 중...")
    mark_tasks_completed_and_update_progress(html_path, completed_tasks) 
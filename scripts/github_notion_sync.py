#!/usr/bin/env python3
"""
키움 API 프로젝트용 GitHub-Notion 자동 연동 스크립트
- GitHub 커밋/이슈와 Notion 데이터베이스 동기화
- 개발 진행률 자동 업데이트
"""

import os
from dotenv import load_dotenv
load_dotenv()
import json
import requests
from datetime import datetime
from typing import Dict, List
import time
import sys

class GitHubNotionSync:
    def __init__(self):
        # 환경변수에서 API 키 로드
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.notion_database_id = os.getenv('NOTION_DATABASE_ID')
        self.github_repo = os.getenv('GITHUB_REPO')  # "username/repo-name"
        
        # API 헤더 설정
        self.notion_headers = {
            'Authorization': f'Bearer {self.notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        
        self.github_headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

    def get_github_commits(self, since_date: str = None) -> List[Dict]:
        """최근 GitHub 커밋 조회"""
        url = f"https://api.github.com/repos/{self.github_repo}/commits"
        params = {}
        if since_date:
            params['since'] = since_date
            
        response = requests.get(url, headers=self.github_headers, params=params)
        return response.json() if response.status_code == 200 else []

    def get_github_issues(self, state: str = 'all') -> List[Dict]:
        """GitHub 이슈 조회"""
        url = f"https://api.github.com/repos/{self.github_repo}/issues"
        params = {'state': state, 'per_page': 100}
        
        response = requests.get(url, headers=self.github_headers, params=params)
        return response.json() if response.status_code == 200 else []

    def query_notion_database(self) -> List[Dict]:
        """Notion 데이터베이스 조회 (Task 오름차순 정렬)"""
        url = f"https://api.notion.com/v1/databases/{self.notion_database_id}/query"
        data = {
            "sorts": [
                {
                    "property": "Task",
                    "direction": "ascending"
                }
            ]
        }
        response = requests.post(url, headers=self.notion_headers, json=data)
        if response.status_code == 200:
            return response.json().get('results', [])
        return []

    def create_notion_page(self, task_data: Dict) -> bool:
        """Notion 페이지 생성"""
        url = "https://api.notion.com/v1/pages"
        
        data = {
            "parent": {"database_id": self.notion_database_id},
            "properties": {
                "Task": {
                    "title": [{"text": {"content": task_data['title']}}]
                },
                "Status": {
                    "select": {"name": task_data.get('status', 'Todo')}
                },
                "Priority": {
                    "select": {"name": task_data.get('priority', 'Medium')}
                },
                "GitHubIssue": {
                    "url": task_data.get('github_url', '')
                },
                "Week": {
                    "select": {"name": task_data.get('week', '1주차')}
                },
                "Memo": {
                    "rich_text": [{"text": {"content": task_data.get('memo', '')}}]
                }
            }
        }
        
        response = requests.post(url, headers=self.notion_headers, json=data)
        return response.status_code == 200

    def update_notion_page(self, page_id: str, updates: Dict) -> bool:
        """Notion 페이지 업데이트"""
        url = f"https://api.notion.com/v1/pages/{page_id}"
        data = {"properties": updates}
        response = requests.patch(url, headers=self.notion_headers, json=data)
        return response.status_code == 200

    def sync_commits_to_notion(self):
        """GitHub 커밋을 Notion에 동기화"""
        print("🔄 GitHub 커밋을 Notion과 동기화 중...")
        
        # 최근 24시간 커밋 조회
        yesterday = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        commits = self.get_github_commits(since_date=yesterday)
        
        for commit in commits[:10]:  # 최근 10개만 처리
            commit_msg = commit['commit']['message']
            commit_url = commit['html_url']
            author = commit['commit']['author']['name']
            
            # 키움 API 관련 커밋인지 확인
            keywords = ['키움', 'kiwoom', 'api', '매매', 'trading', 'algorithm']
            if any(keyword in commit_msg.lower() for keyword in keywords):
                
                task_data = {
                    'title': f"[커밋] {commit_msg[:50]}...",
                    'status': 'Done',
                    'priority': 'Medium',
                    'github_url': commit_url,
                    'week': self.determine_week_from_commit(commit_msg)
                }
                
                if self.create_notion_page(task_data):
                    print(f"✅ 커밋 동기화 완료: {commit_msg[:30]}...")

    def sync_issues_to_notion(self):
        """GitHub 이슈를 Notion에 동기화"""
        print("🔄 GitHub 이슈를 Notion과 동기화 중...")
        
        issues = self.get_github_issues()
        
        for issue in issues:
            if not issue.get('pull_request'):  # PR 제외
                issue_title = issue['title']
                issue_url = issue['html_url']
                issue_state = 'Done' if issue['state'] == 'closed' else 'In Progress'
                
                # 라벨 기반 우선순위 결정
                priority = 'Medium'
                for label in issue.get('labels', []):
                    if label['name'] in ['high priority', 'urgent']:
                        priority = 'High'
                    elif label['name'] in ['low priority', 'enhancement']:
                        priority = 'Low'
                
                task_data = {
                    'title': f"[이슈] {issue_title}",
                    'status': issue_state,
                    'priority': priority,
                    'github_url': issue_url,
                    'week': self.determine_week_from_issue(issue_title)
                }
                
                if self.create_notion_page(task_data):
                    print(f"✅ 이슈 동기화 완료: {issue_title[:30]}...")

    def determine_week_from_commit(self, commit_msg: str) -> str:
        """커밋 메시지에서 주차 결정"""
        if any(word in commit_msg.lower() for word in ['api', '연동', 'setup', 'auth']):
            return '1주차'
        elif any(word in commit_msg.lower() for word in ['ui', 'streamlit', 'dashboard']):
            return '2주차'
        return '1주차'

    def determine_week_from_issue(self, issue_title: str) -> str:
        """이슈 제목에서 주차 결정"""
        if any(word in issue_title.lower() for word in ['ui', 'frontend', 'dashboard']):
            return '2주차'
        return '1주차'

    def update_progress(self):
        """전체 진행률 업데이트"""
        print("📊 프로젝트 진행률 업데이트 중...")
        
        notion_pages = self.query_notion_database()
        total_tasks = len(notion_pages)
        completed_tasks = len([p for p in notion_pages 
                             if p['properties'].get('Status', {}).get('select', {}).get('name') == 'Done'])
        
        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        print(f"📈 진행률: {progress_percentage:.1f}% ({completed_tasks}/{total_tasks})")
        return progress_percentage

    def run_sync(self):
        """전체 동기화 실행"""
        print("🚀 키움 API 프로젝트 GitHub-Notion 동기화 시작")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 커밋 동기화
            self.sync_commits_to_notion()
            time.sleep(2)  # API 제한 고려
            
            # 이슈 동기화
            self.sync_issues_to_notion()
            time.sleep(2)
            
            # 진행률 업데이트
            progress = self.update_progress()
            
            print(f"✅ 동기화 완료! 현재 진행률: {progress:.1f}%")
            
        except Exception as e:
            print(f"❌ 동기화 중 오류 발생: {str(e)}")

def main():
    """메인 실행 함수"""
    # 환경변수 체크
    required_vars = ['NOTION_TOKEN', 'GITHUB_TOKEN', 'NOTION_DATABASE_ID', 'GITHUB_REPO']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 다음 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        print("\n.env 파일에 다음 내용을 추가하세요:")
        print("NOTION_TOKEN=your_notion_integration_token")
        print("GITHUB_TOKEN=your_github_personal_access_token")
        print("NOTION_DATABASE_ID=your_database_id")
        print("GITHUB_REPO=username/repository-name")
        return

    # 명령줄 옵션 처리
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list-database":
            sync = GitHubNotionSync()
            print("\n🔎 Notion 데이터베이스 조회 결과:")
            pages = sync.query_notion_database()
            for i, page in enumerate(pages, 1):
                title = ''
                task_prop = page['properties'].get('Task')
                if task_prop and isinstance(task_prop, dict):
                    title_list = task_prop.get('title', [])
                    if title_list and 'plain_text' in title_list[0]:
                        title = title_list[0]['plain_text']
                # Status
                status = ''
                status_obj = page['properties'].get('Status')
                if status_obj and isinstance(status_obj, dict):
                    status_val = status_obj.get('status')
                    if status_val and isinstance(status_val, dict):
                        status = status_val.get('name', '')
                # Week
                week = ''
                week_prop = page['properties'].get('Week')
                if week_prop and isinstance(week_prop, dict):
                    week_val = week_prop.get('select')
                    if week_val and isinstance(week_val, dict):
                        week = week_val.get('name', '')
                # Day (년/월/일)
                day = ''
                day_prop = page['properties'].get('Day')
                if day_prop and isinstance(day_prop, dict):
                    date_val = day_prop.get('date')
                    if date_val and isinstance(date_val, dict):
                        day = date_val.get('start', '')
                # GitHubIssue
                github_url = ''
                github_url_prop = page['properties'].get('GitHubIssue')
                if github_url_prop and isinstance(github_url_prop, dict):
                    github_url = github_url_prop.get('url', '')
                # Memo
                memo = ''
                memo_prop = page['properties'].get('Memo')
                if memo_prop and isinstance(memo_prop, dict):
                    rich_texts = memo_prop.get('rich_text', [])
                    if rich_texts and 'plain_text' in rich_texts[0]:
                        memo = rich_texts[0]['plain_text']
                print(f"{i}. {title} | 상태: {status} | 주차: {week} | 날짜: {day} | GitHub: {github_url} | 메모: {memo}")
            print(f"총 {len(pages)}개 항목 조회됨.")
            return
        elif sys.argv[1] == "--list-commits":
            sync = GitHubNotionSync()
            print("\n🔎 최근 GitHub 커밋 목록:")
            commits = sync.get_github_commits()
            for i, commit in enumerate(commits[:20], 1):
                msg = commit['commit']['message']
                url = commit['html_url']
                author = commit['commit']['author']['name']
                date = commit['commit']['author']['date']
                print(f"{i}. {msg} | 작성자: {author} | 날짜: {date}\n   URL: {url}")
            print(f"총 {len(commits)}개 커밋 조회됨.")
            return

    # 동기화 실행
    sync = GitHubNotionSync()
    sync.run_sync()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
데이터 백업 스크립트
- SQLite 데이터베이스 백업
- 로그 파일 아카이브
- 설정 파일 백업
- 자동 압축 및 날짜별 관리
"""

import os
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BackupManager:
def __init__(self, backup_dir='backups'):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
def backup_database(self):
        """SQLite 데이터베이스 백업"""
        try:
            source_db = Path('data/trading.db')
            if not source_db.exists():
                logger.warning("⚠️ trading.db 파일이 없습니다.")
                return False
                
            backup_db = self.backup_dir / f'trading_db_{self.timestamp}.db'
            
            # SQLite 백업 (VACUUM으로 최적화)
            source_conn = sqlite3.connect(source_db)
            backup_conn = sqlite3.connect(backup_db)
            source_conn.backup(backup_conn)
            source_conn.close()
            backup_conn.close()
            
            logger.info(f"💾 데이터베이스 백업 완료: {backup_db}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 백업 실패: {e}")
            return False
    
def backup_logs(self):
        """로그 파일 백업 및 아카이브"""
        try:
            logs_dir = Path('logs')
            if not logs_dir.exists():
                logger.warning("⚠️ logs 디렉토리가 없습니다.")
                return False
                
            backup_logs_zip = self.backup_dir / f'logs_{self.timestamp}.zip'
            
            with zipfile.ZipFile(backup_logs_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for log_file in logs_dir.glob('*.log'):
                    zipf.write(log_file, log_file.name)
                    
            logger.info(f"📝 로그 파일 백업 완료: {backup_logs_zip}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 로그 파일 백업 실패: {e}")
            return False
    
def backup_config(self):
        """설정 파일 백업"""
        try:
            config_files = [
                'config.yaml',
                '.env.example',
                'requirements.txt'
            ]
            
            backup_config_zip = self.backup_dir / f'config_{self.timestamp}.zip'
            
            with zipfile.ZipFile(backup_config_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for config_file in config_files:
                    file_path = Path(config_file)
                    if file_path.exists():
                        zipf.write(file_path, file_path.name)
                        
            logger.info(f"⚙️ 설정 파일 백업 완료: {backup_config_zip}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 설정 파일 백업 실패: {e}")
            return False
    
def backup_historical_data(self):
        """과거 데이터 백업"""
        try:
            historical_dir = Path('data/historical')
            if not historical_dir.exists() or not any(historical_dir.iterdir()):
                logger.warning("⚠️ 과거 데이터가 없습니다.")
                return False
                
            backup_historical_zip = self.backup_dir / f'historical_{self.timestamp}.zip'
            
            with zipfile.ZipFile(backup_historical_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for data_file in historical_dir.rglob('*'):
                    if data_file.is_file():
                        # 상대 경로로 저장
                        arcname = data_file.relative_to(historical_dir)
                        zipf.write(data_file, arcname)
                        
            logger.info(f"📊 과거 데이터 백업 완료: {backup_historical_zip}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 과거 데이터 백업 실패: {e}")
            return False
    
def cleanup_old_backups(self, keep_days=30):
        """오래된 백업 파일 정리"""
        try:
            current_time = datetime.now()
            deleted_count = 0
            
            for backup_file in self.backup_dir.glob('*'):
                if backup_file.is_file():
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    days_old = (current_time - file_time).days
                    
                    if days_old > keep_days:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.info(f"🗑️ 오래된 백업 삭제: {backup_file.name}")
            
            if deleted_count > 0:
                logger.info(f"🧹 {deleted_count}개의 오래된 백업 파일 정리 완료")
            else:
                logger.info("✅ 정리할 오래된 백업 파일 없음")
                
        except Exception as e:
            logger.error(f"❌ 백업 정리 실패: {e}")
    
def create_full_backup(self):
        """전체 백업 실행"""
        logger.info(f"🚀 전체 백업 시작 - {self.timestamp}")
        
        results = []
        results.append(self.backup_database())
        results.append(self.backup_logs())
        results.append(self.backup_config())
        results.append(self.backup_historical_data())
        
        success_count = sum(results)
        total_count = len(results)
        
        logger.info(f"📋 백업 완료: {success_count}/{total_count} 성공")
        
        # 오래된 백업 정리
        self.cleanup_old_backups()
        
        return success_count == total_count

def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='데이터 백업 스크립트')
    parser.add_argument('--db-only', action='store_true', help='데이터베이스만 백업')
    parser.add_argument('--logs-only', action='store_true', help='로그 파일만 백업')
    parser.add_argument('--config-only', action='store_true', help='설정 파일만 백업')
    parser.add_argument('--cleanup', action='store_true', help='오래된 백업만 정리')
    parser.add_argument('--keep-days', type=int, default=30, help='백업 보관 일수 (기본: 30일)')
    
    args = parser.parse_args()
    
    backup_manager = BackupManager()
    
    if args.cleanup:
        backup_manager.cleanup_old_backups(args.keep_days)
    elif args.db_only:
        backup_manager.backup_database()
    elif args.logs_only:
        backup_manager.backup_logs()
    elif args.config_only:
        backup_manager.backup_config()
    else:
        backup_manager.create_full_backup()

if __name__ == "__main__":
    main() 
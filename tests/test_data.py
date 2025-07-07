import os
import sqlite3
import tempfile
import pytest
from src.data import database

def test_get_connection_success():
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    try:
        conn = database.get_connection(tmp.name)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()
    finally:
        os.unlink(tmp.name)

def test_get_connection_fail():
    # 존재할 수 없는 경로로 연결 시도
    conn = database.get_connection('/invalid/path/to/db.sqlite')
    assert conn is None

def test_init_db_creates_table():
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    try:
        conn = database.get_connection(tmp.name)
        database.init_db(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        result = cursor.fetchone()
        assert result is not None and result[0] == 'users'
        conn.close()
    finally:
        os.unlink(tmp.name) 
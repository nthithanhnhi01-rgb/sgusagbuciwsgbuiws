import sqlite3
import os
import psycopg2
from urllib.parse import urlparse

# Lấy link DB từ biến môi trường (trên Render sẽ có, máy local sẽ không có)
DB_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """Tự động chọn SQLite (Local) hoặc Postgres (Render)"""
    if DB_URL:
        # Kết nối PostgreSQL (Render)
        conn = psycopg2.connect(DB_URL)
        return conn, '%s' # Postgres dùng placeholder là %s
    else:
        # Kết nối SQLite (Local)
        conn = sqlite3.connect("users.db")
        return conn, '?'  # SQLite dùng placeholder là ?

def init_db():
    """Tạo bảng user nếu chưa có"""
    conn, ph = get_connection()
    c = conn.cursor()
    
    # Cú pháp SQL tạo bảng (tương thích cả 2)
    # Lưu ý: Postgres dùng TEXT hoặc VARCHAR
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username VARCHAR(50) PRIMARY KEY, 
                  password VARCHAR(50), 
                  role VARCHAR(20), 
                  status VARCHAR(20))''')
    
    conn.commit()
    
    # Tạo user Admin mặc định nếu chưa có
    try:
        # Kiểm tra xem admin có chưa
        query_check = f"SELECT username FROM users WHERE username={ph}"
        c.execute(query_check, ('admin',))
        if not c.fetchone():
            query_insert = f"INSERT INTO users (username, password, role, status) VALUES ({ph}, {ph}, {ph}, {ph})"
            c.execute(query_insert, ('admin', 'admin123', 'admin', 'active'))
            conn.commit()
    except Exception as e:
        print("Lỗi khởi tạo Admin:", e)
    
    conn.close()

def check_login(username, password):
    conn, ph = get_connection()
    c = conn.cursor()
    query = f"SELECT role FROM users WHERE username={ph} AND password={ph} AND status='active'"
    c.execute(query, (username, password))
    user = c.fetchone()
    conn.close()
    return user[0] if user else None

def add_user(username, password):
    try:
        conn, ph = get_connection()
        c = conn.cursor()
        query = f"INSERT INTO users (username, password, role, status) VALUES ({ph}, {ph}, 'user', 'active')"
        c.execute(query, (username, password))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_all_users():
    conn, _ = get_connection()
    c = conn.cursor()
    c.execute("SELECT username, password, status FROM users WHERE role='user'")
    data = c.fetchall()
    conn.close()
    return data

def delete_user(username):
    conn, ph = get_connection()
    c = conn.cursor()
    query = f"DELETE FROM users WHERE username={ph}"
    c.execute(query, (username,))
    conn.commit()
    conn.close()

# Chạy khởi tạo DB ngay khi import
init_db()
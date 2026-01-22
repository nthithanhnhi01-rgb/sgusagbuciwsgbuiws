import sqlite3

DB_NAME = "users.db"

def init_db():
    """Tạo bảng user nếu chưa có"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tạo bảng: username, password, role (admin/user), status (active/blocked)
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, status TEXT)''')
    
    # Tạo sẵn 1 tài khoản Admin để bạn đăng nhập lần đầu
    # Pass mặc định: admin123
    try:
        c.execute("INSERT INTO users VALUES ('admin', 'admin123', 'admin', 'active')")
    except:
        pass # Đã có rồi thì thôi
    
    conn.commit()
    conn.close()

def check_login(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password=? AND status='active'", (username, password))
    user = c.fetchone()
    conn.close()
    return user[0] if user else None # Trả về role (admin/user) hoặc None

def add_user(username, password):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO users VALUES (?, ?, 'user', 'active')", (username, password))
        conn.commit()
        conn.close()
        return True
    except:
        return False # Trùng tên user

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT username, password, status FROM users WHERE role='user'")
    data = c.fetchall()
    conn.close()
    return data

def delete_user(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()

# Chạy khởi tạo DB ngay khi import
init_db()
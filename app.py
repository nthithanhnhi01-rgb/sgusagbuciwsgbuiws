from flask import Flask, render_template, request, session, redirect, url_for, send_file, render_template_string
import pandas as pd
import io
import database as db  # Đảm bảo bạn đã tạo file database.py như tôi hướng dẫn trước đó

app = Flask(__name__)
app.secret_key = 'qwertyuiGRE572385' # Đổi cái này thành một chuỗi bí mật bất kỳ

# --- CẤU HÌNH DATA ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-4uKzaw2LpN5lBOGyG4MB3DPbaC6p6SbtO-yhoEQHRVFx30UHgJOSGfwTn-dOHkhBjAMoDea8n0ih/pub?gid=0&single=true&output=csv"

def get_dataframe():
    try:
        df = pd.read_csv(SHEET_URL, dtype=str)
        df.fillna("", inplace=True)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print("Lỗi tải data:", e)
        return pd.DataFrame()

def filter_data(df, form_data):
    batch_input = form_data.get('batch_input', '').strip()
    if batch_input:
        keywords = [x.strip().replace('"', '').replace("'", "") for x in batch_input.split(';') if x.strip()]
        if 'MaCAS' in df.columns: return df[df['MaCAS'].isin(keywords)]
            
    f_cas = form_data.get('f_cas', '').strip()
    f_name = form_data.get('f_name', '').strip()
    f_formula = form_data.get('f_formula', '').strip()

    if f_cas and 'MaCAS' in df.columns:
        df = df[df['MaCAS'].str.contains(f_cas, case=False, na=False)]
    if f_name and 'Tên chất' in df.columns:
        mask = df['Tên chất'].str.contains(f_name, case=False, na=False)
        if 'Tên khoa học (danh pháp IUPAC)' in df.columns:
            mask = mask | df['Tên khoa học (danh pháp IUPAC)'].str.contains(f_name, case=False, na=False)
        df = df[mask]
    if f_formula and 'Công thức hóa học' in df.columns:
        df = df[df['Công thức hóa học'].str.contains(f_formula, case=False, na=False)]
    return df

# Template cho từng hàng kết quả (Bỏ chữ 'Văn bản', thay bằng icon i)
ROW_TEMPLATE = """
{% if results %}
    {% for row in results %}
    <tr>
        <td class="col-center text-muted">{{ loop.index }}</td>
        <td><strong>{{ row['Tên chất'] }}</strong></td>
        <td class="text-secondary">{{ row['Tên khoa học (danh pháp IUPAC)'] }}</td>
        <td class="col-cas col-center">{{ row['MaCAS'] }}</td>
        <td class="col-center">{{ row['Công thức hóa học'] }}</td>
        <td class="text-center">
            {% if row['Ngưỡng khối lượng hóa chất tồn trữ lớn nhất tại một thời điểm (kg)'] %}
                <span class="threshold-high">{{ row['Ngưỡng khối lượng hóa chất tồn trữ lớn nhất tại một thời điểm (kg)'] }}</span>
            {% else %}<span class="text-muted small">-</span>{% endif %}
        </td>
        <td>
            {% if row['Phụ lục quản lý'] %}
                {% set items = row['Phụ lục quản lý'].replace('\\n', ';').split(';') %}
                {% for item in items %}
                    {% if item.strip() %}
                        {% set cls = 'bg-info-light' %}
                        {% if 'hạn chế' in item.lower() or 'pl i' in item.lower() %}{% set cls = 'bg-danger-light' %}
                        {% elif 'khai báo' in item.lower() or 'pl v' in item.lower() %}{% set cls = 'bg-warning-light' %}{% endif %}
                        <span class="badge-custom {{ cls }}">{{ item }}</span>
                    {% endif %}
                {% endfor %}
            {% endif %}
        </td>
        <td class="col-center">
            {% if row['Link văn bản']|length > 5 %}
                <a href="{{ row['Link văn bản'] }}" target="_blank" class="link-icon">
                    <i class="fa-solid fa-circle-info fa-xl"></i>
                </a>
            {% endif %}
        </td>
    </tr>
    {% endfor %}
{% else %}
    <tr><td colspan="8" class="text-center py-5 text-muted">Không tìm thấy dữ liệu phù hợp.</td></tr>
{% endif %}
"""

# --- ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        
        # Giả sử hàm kiểm tra database trả về True
        if db.check_login(user, pw):
            session['username'] = user  # <--- PHẢI CÓ DÒNG NÀY
            session['role'] = 'admin'   # Lưu quyền để vào trang /admin
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return "Bạn không có quyền truy cập!", 403
    msg = ""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            if db.add_user(request.form['new_user'], request.form['new_pass']): msg = "✅ Đã thêm user!"
            else: msg = "❌ Lỗi: User đã tồn tại!"
        elif action == 'delete':
            db.delete_user(request.form['del_user'])
            msg = "🗑️ Đã xóa user!"
    return render_template('admin.html', users=db.get_all_users(), msg=msg)

@app.route('/')
def index():
    # Kiểm tra xem người dùng đã đăng nhập chưa
    if 'username' not in session:
        # Nếu chưa, đá họ về trang login ngay lập tức
        return redirect(url_for('login'))
    
    # Nếu đã đăng nhập rồi thì mới cho xem nội dung trang chủ
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def api_search():
    # Sửa từ 'logged_in' thành 'username' để khớp với hàm login
    if not session.get('username'): 
        return {"html": "<tr><td colspan='5'>Vui lòng đăng nhập lại.</td></tr>", "count": 0}
    
    df = get_dataframe()
    df_res = filter_data(df, request.form) if not df.empty else pd.DataFrame()
    
    return {
        "html": render_template_string(ROW_TEMPLATE, results=df_res.to_dict('records')), 
        "count": len(df_res)
    }

@app.route('/export', methods=['POST'])
def export():
    if not session.get('logged_in'): return redirect(url_for('login'))
    df = get_dataframe()
    df_res = filter_data(df, request.form) if not df.empty else pd.DataFrame()
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
        df_res.to_excel(writer, index=False, sheet_name='KetQua')
    out.seek(0)
    return send_file(out, download_name="KetQua.xlsx", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
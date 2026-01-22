from flask import Flask, render_template, request, send_file, render_template_string
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = 'SHINE_GROUP_SECRET'

# --- CẤU HÌNH DATA ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-4uKzaw2LpN5lBOGyG4MB3DPbaC6p6SbtO-yhoEQHRVFx30UHgJOSGfwTn-dOHkhBjAMoDea8n0ih/pub?gid=0&single=true&output=csv"

def get_dataframe():
    try:
        df = pd.read_csv(SHEET_URL, dtype=str)
        df.fillna("", inplace=True) # Xử lý lỗi NaN
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print("Lỗi data:", e)
        return pd.DataFrame()

# --- LOGIC LỌC DỮ LIỆU ---
def filter_data(df, form_data):
    # 1. Lọc Batch (Ưu tiên)
    batch_input = form_data.get('batch_input', '').strip()
    if batch_input:
        keywords = [x.strip().replace('"', '').replace("'", "") for x in batch_input.split(';') if x.strip()]
        if 'MaCAS' in df.columns:
            return df[df['MaCAS'].isin(keywords)]
            
    # 2. Lọc Single
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

# --- HTML TEMPLATE CHO HÀNG (Dùng để trả về cho AJAX) ---
ROW_TEMPLATE = """
{% if results %}
    {% for row in results %}
    <tr>
        <td class="col-center text-muted">{{ loop.index }}</td>
        <td><strong>{{ row['Tên chất'] }}</strong></td>
        <td class="text-secondary">{{ row['Tên khoa học (danh pháp IUPAC)'] }}</td>
        <td class="col-cas col-center">{{ row['MaCAS'] }}</td>
        <td class="col-center">{{ row['Công thức hóa học'] }}</td>
        <td class="text-end">
            {% if row['Ngưỡng khối lượng hóa chất tồn trữ lớn nhất tại một thời điểm (kg)'] %}
                <span class="threshold-high">{{ row['Ngưỡng khối lượng hóa chất tồn trữ lớn nhất tại một thời điểm (kg)'] }}</span>
            {% else %}
                <span class="text-muted small">-</span>
            {% endif %}
        </td>
        <td>
            {% if row['Phụ lục quản lý'] %}
                {% set items = row['Phụ lục quản lý'].replace('\\n', ';').split(';') %}
                {% for item in items %}
                    {% if item.strip() %}
                        {% set cls = 'bg-info-light' %}
                        {% set txt_lower = item.lower() %}
                        {% if 'hạn chế' in txt_lower or 'nguy hiểm' in txt_lower or 'pl i' in txt_lower or 'tiền chất' in txt_lower %}
                            {% set cls = 'bg-danger-light' %}
                        {% elif 'khai báo' in txt_lower or 'pl v' in txt_lower %}
                            {% set cls = 'bg-warning-light' %}
                        {% endif %}
                        <span class="badge-custom {{ cls }}">{{ item }}</span>
                    {% endif %}
                {% endfor %}
            {% endif %}
        </td>
        <td class="col-center">
            {% if row['Link văn bản']|length > 5 %}
                <a href="{{ row['Link văn bản'] }}" target="_blank" class="link-icon" ><i class="fa-solid fa-circle-info fa-xl"></i>
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

@app.route('/', methods=['GET'])
def index():
    # Load trang lần đầu (chưa tìm gì)
    return render_template('index.html', count=0, results=[])

# ĐÂY LÀ ĐƯỜNG DẪN MÀ BẠN ĐANG BỊ THIẾU (LỖI 404)
@app.route('/api/search', methods=['POST'])
def api_search():
    df = get_dataframe()
    count = 0
    html_rows = ""
    
    if not df.empty:
        df_result = filter_data(df, request.form)
        count = len(df_result)
        results = df_result.to_dict('records')
        # Render HTML từ template con
        html_rows = render_template_string(ROW_TEMPLATE, results=results)
    
    # Trả về JSON cho Javascript
    return {"html": html_rows, "count": count}

@app.route('/export', methods=['POST'])
def export():
    df = get_dataframe()
    if not df.empty:
        df = filter_data(df, request.form)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='KetQua')
    writer.close()
    output.seek(0)
    
    return send_file(output, download_name="KetQua.xlsx", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
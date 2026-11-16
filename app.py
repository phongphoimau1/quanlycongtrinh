import os
import streamlit as st

# 1. Cấu hình trang chuẩn Enterprise (Phải đặt ở lệnh Streamlit đầu tiên)
st.set_page_config(
    page_title="Hệ thống Quản lý Công trình",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Hàm thông minh: Tự động tạo file khung (Placeholder) nếu file module chưa tồn tại
# Giúp hệ thống chạy mượt mà để test từng phần mà không bao giờ báo lỗi thiếu file
def ensure_page_exists(file_path, page_title, icon="🚧"):
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f'''import streamlit as st

st.title("{icon} {page_title}")
st.info("Chức năng **{page_title}** (`{file_path}`) đã được kết nối vào thanh điều hướng và sẵn sàng triển khai chi tiết.")
''')
    return file_path

# 3. Đảm bảo toàn bộ các đường dẫn trong kiến trúc menu đều tồn tại hợp lệ
# --- TỔNG QUAN ---
p_dashboard = ensure_page_exists("modules/dashboard/view.py", "Dashboard Tổng quan", "📊")

# --- NGHIỆP VỤ ---
p_projects = ensure_page_exists("modules/projects/view.py", "Danh sách công trình", "🏗️")
p_proj_detail = ensure_page_exists("modules/projects/detail.py", "Chi tiết công trình", "🔍")
p_proj_create = ensure_page_exists("modules/projects/create.py", "Tạo công trình mới", "➕")
p_email_in = ensure_page_exists("modules/emails/view.py", "Tiếp nhận email", "📥")
p_email_mgr = ensure_page_exists("modules/emails/manage.py", "Quản lý email", "📧")
p_confirm = ensure_page_exists("modules/confirmation/view.py", "Chờ xác nhận", "⏳")
p_docs = ensure_page_exists("modules/documents/view.py", "Quản lý hồ sơ", "📂")
p_progress = ensure_page_exists("modules/progress/view.py", "Theo dõi tiến độ", "📈")
p_assign = ensure_page_exists("modules/assignment/view.py", "Phân công công việc", "👥")

# --- BÁO CÁO ---
p_rep_all = ensure_page_exists("modules/reports/view.py", "Báo cáo & Hiệu suất", "📊")
p_rep_month = ensure_page_exists("modules/reports/monthly.py", "Báo cáo tháng", "📅")
p_rep_year = ensure_page_exists("modules/reports/yearly.py", "Báo cáo năm", "📆")

# --- QUẢN TRỊ ---
p_users = ensure_page_exists("modules/admin/users.py", "Nhân viên và phân quyền", "🛡️")
p_categories = ensure_page_exists("modules/admin/categories.py", "Danh mục", "🗂️")
p_audit = ensure_page_exists("modules/admin/audit_logs.py", "Nhật ký hệ thống", "📜")
p_cfg_gmail = ensure_page_exists("modules/admin/gmail_config.py", "Cấu hình Gmail", "✉️")
p_cfg_ai = ensure_page_exists("modules/admin/ai_config.py", "Cấu hình AI", "🤖")

# 4. Thiết lập cấu trúc Menu Điều hướng Phân tầng
pages = {
    "TỔNG QUAN": [
        st.Page(p_dashboard, title="Dashboard", icon="📊", default=True),
    ],
    "NGHIỆP VỤ": [
        st.Page(p_projects, title="Danh sách công trình", icon="🏗️"),
        st.Page(p_email_in, title="Tiếp nhận email", icon="📥"),
        st.Page(p_email_mgr, title="Quản lý email", icon="📧"),
        st.Page(p_confirm, title="Chờ xác nhận", icon="⏳"),
        st.Page(p_docs, title="Quản lý hồ sơ", icon="📂"),
        st.Page(p_progress, title="Theo dõi tiến độ", icon="📈"),
        st.Page(p_assign, title="Phân công công việc", icon="👥"),
        # Đăng ký ngầm 2 trang con của Công trình để lệnh st.switch_page() hoạt động mượt mà
        st.Page(p_proj_detail, title="Chi tiết công trình", icon="🔍"),
        st.Page(p_proj_create, title="Tạo mới công trình", icon="➕"),
    ],
    "BÁO CÁO": [
        st.Page(p_rep_all, title="Hiệu suất & Tổng hợp", icon="🏆"),
        st.Page(p_rep_month, title="Báo cáo tháng", icon="📅"),
        st.Page(p_rep_year, title="Báo cáo năm", icon="📆"),
    ],
    "QUẢN TRỊ": [
        st.Page(p_users, title="Nhân viên và phân quyền", icon="🛡️"),
        st.Page(p_categories, title="Danh mục", icon="🗂️"),
        st.Page(p_audit, title="Nhật ký hệ thống", icon="📜"),
        st.Page(p_cfg_gmail, title="Cấu hình Gmail", icon="✉️"),
        st.Page(p_cfg_ai, title="Cấu hình AI", icon="🤖"),
    ]
}

# 5. Bổ sung thông tin nhanh ở Sidebar
with st.sidebar:
    st.markdown("### 🏗️ QUẢN LÝ CÔNG TRÌNH")
    st.caption("Hệ thống Điều phối & Tự động hóa AI")
    st.divider()

# 6. Khởi chạy bộ định tuyến (Router)
pg = st.navigation(pages)
pg.run()

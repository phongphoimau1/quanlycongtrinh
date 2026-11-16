import os
import streamlit as st

# 1. Cấu hình trang chuẩn (Phải đặt ở đầu file)
st.set_page_config(
    page_title="Hệ thống Quản lý Công trình",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Hàm khởi tạo Page thông minh:
# - Gán url_path riêng biệt cho từng trang (Tránh lỗi trùng tên file view.py làm sập st.navigation)
# - Nếu file .py đã có trên hệ thống -> Load trực tiếp file đó
# - Nếu file .py chưa kịp tạo -> Dùng hàm Python hiển thị giao diện chờ (Không cần ghi file lên Cloud)
def build_safe_page(file_path, title, icon, url_path, default=False):
    if os.path.exists(file_path):
        return st.Page(
            file_path,
            title=title,
            icon=icon,
            url_path=url_path,
            default=default
        )
    else:
        def placeholder_page():
            st.title(f"{icon} {title}")
            st.info(f"📌 Module **{title}** (đường dẫn dự kiến: `{file_path}`) hiện chưa được tạo file vật lý trên hệ thống.")
            st.caption("Bạn có thể tạo file này trong dự án để kích hoạt đầy đủ tính năng.")
            
        # Đặt tên hàm động để Streamlit không báo trùng tên hàm
        placeholder_page.__name__ = f"page_{url_path}"
        return st.Page(
            placeholder_page,
            title=title,
            icon=icon,
            url_path=url_path,
            default=default
        )

# 3. Khai báo danh sách các trang với url_path duy nhất
pages = {
    "TỔNG QUAN": [
        build_safe_page("modules/dashboard/view.py", "Dashboard", "📊", "dashboard", default=True),
    ],
    "NGHIỆP VỤ": [
        build_safe_page("modules/projects/view.py", "Danh sách công trình", "🏗️", "projects-list"),
        build_safe_page("modules/emails/view.py", "Tiếp nhận email", "📥", "emails-inbox"),
        build_safe_page("modules/emails/manage.py", "Quản lý email", "📧", "emails-manage"),
        build_safe_page("modules/confirmation/view.py", "Chờ xác nhận", "⏳", "confirmation-queue"),
        build_safe_page("modules/documents/view.py", "Quản lý hồ sơ", "📂", "project-documents"),
        build_safe_page("modules/progress/view.py", "Theo dõi tiến độ", "📈", "project-progress"),
        build_safe_page("modules/assignment/view.py", "Phân công công việc", "👥", "staff-assignment"),
        # Hai trang con hỗ trợ điều hướng từ Danh sách công trình
        build_safe_page("modules/projects/detail.py", "Chi tiết công trình", "🔍", "project-detail"),
        build_safe_page("modules/projects/create.py", "Tạo mới công trình", "➕", "project-create"),
    ],
    "BÁO CÁO": [
        build_safe_page("modules/reports/view.py", "Hiệu suất nhân viên", "🏆", "staff-performance"),
        build_safe_page("modules/reports/monthly.py", "Báo cáo tháng", "📅", "monthly-report"),
        build_safe_page("modules/reports/yearly.py", "Báo cáo năm", "📆", "yearly-report"),
    ],
    "QUẢN TRỊ": [
        build_safe_page("modules/admin/users.py", "Nhân viên và phân quyền", "🛡️", "admin-users"),
        build_safe_page("modules/admin/categories.py", "Danh mục", "🗂️", "admin-categories"),
        build_safe_page("modules/admin/audit_logs.py", "Nhật ký hệ thống", "📜", "admin-audit-logs"),
        build_safe_page("modules/admin/gmail_config.py", "Cấu hình Gmail", "✉️", "admin-gmail-config"),
        build_safe_page("modules/admin/ai_config.py", "Cấu hình AI", "🤖", "admin-ai-config"),
    ]
}

# 4. Thanh thông tin Sidebar
with st.sidebar:
    st.markdown("### 🏗️ QUẢN LÝ CÔNG TRÌNH")
    st.caption("Hệ thống Điều phối & Tự động hóa AI")
    st.divider()

# 5. Khởi chạy bộ định tuyến
pg = st.navigation(pages)
pg.run()

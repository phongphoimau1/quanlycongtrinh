import os
import streamlit as st
from services.auth_service import (
    is_authenticated,
    get_current_user,
    logout_user,
    ROLE_DISPLAY_MAP,
)

# 1. Cấu hình trang chuẩn Enterprise (Phải đặt ở lệnh đầu tiên)
st.set_page_config(
    page_title="Hệ thống Quản lý Công trình",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# 2. Hàm khởi tạo Page an toàn với url_path định danh riêng biệt
def build_safe_page(file_path, title, icon, url_path, default=False):
    if os.path.exists(file_path):
        return st.Page(
            file_path,
            title=title,
            icon=icon,
            url_path=url_path,
            default=default,
        )
    else:
        def placeholder_page():
            st.title(f"{icon} {title}")
            st.info(f"📌 Module **{title}** (`{file_path}`) hiện chưa được tạo file vật lý trên hệ thống.")

        placeholder_page.__name__ = f"page_{url_path}"
        return st.Page(
            placeholder_page,
            title=title,
            icon=icon,
            url_path=url_path,
            default=default,
        )


# 3. KIỂM TRA TRẠNG THÁI ĐĂNG NHẬP (AUTH GATE)
if not is_authenticated():
    login_page = build_safe_page(
        "modules/auth/login.py",
        "Đăng nhập Hệ thống",
        "🔐",
        "login",
        default=True,
    )
    pg = st.navigation([login_page], position="hidden")
    pg.run()
    st.stop()


# 4. NẾU ĐÃ ĐĂNG NHẬP -> LẤY THÔNG TIN USER & PHÂN QUYỀN MENU (RBAC)
current_user = get_current_user()
user_role = str(current_user.get("role") or "staff").lower()
role_badge = ROLE_DISPLAY_MAP.get(user_role, user_role.upper())

# Hiển thị thông tin tài khoản đang đăng nhập trên Sidebar
with st.sidebar:
    st.markdown("### 🏗️ QUẢN LÝ CÔNG TRÌNH")
    with st.container(border=True):
        st.markdown(f"👤 **{current_user.get('full_name', 'Người dùng')}**")
        st.caption(f"📧 {current_user.get('email', '')}")
        st.caption(f"🛡️ {role_badge}")
        if st.button("🚪 Đăng xuất", width="stretch", type="secondary"):
            logout_user()
            st.rerun()

# Khởi tạo các trang theo nhóm
overview_pages = [
    build_safe_page("modules/dashboard/view.py", "Dashboard", "📊", "dashboard", default=True),
]

operation_pages = [
    build_safe_page("modules/projects/view.py", "Danh sách công trình", "🏗️", "projects-list"),
    build_safe_page("modules/emails/view.py", "Tiếp nhận email", "📥", "emails-inbox"),
    build_safe_page("modules/emails/manage.py", "Quản lý email", "📧", "emails-manage"),
    build_safe_page("modules/confirmation/view.py", "Chờ xác nhận", "⏳", "confirmation-queue"),
    build_safe_page("modules/documents/view.py", "Quản lý hồ sơ", "📂", "project-documents"),
    build_safe_page("modules/progress/view.py", "Theo dõi tiến độ", "📈", "project-progress"),
    build_safe_page("modules/assignment/view.py", "Phân công công việc", "👥", "staff-assignment"),
    build_safe_page("modules/projects/detail.py", "Chi tiết công trình", "🔍", "project-detail"),
    build_safe_page("modules/projects/create.py", "Tạo mới công trình", "➕", "project-create"),
]

report_pages = [
    build_safe_page("modules/reports/view.py", "Hiệu suất nhân viên", "🏆", "staff-performance"),
    build_safe_page("modules/reports/monthly.py", "Báo cáo tháng", "📅", "monthly-report"),
    build_safe_page("modules/reports/yearly.py", "Báo cáo năm", "📆", "yearly-report"),
]

admin_pages = [
    build_safe_page("modules/admin/users.py", "Nhân viên và phân quyền", "🛡️", "admin-users"),
    build_safe_page("modules/admin/categories.py", "Danh mục", "🗂️", "admin-categories"),
    build_safe_page("modules/admin/audit_logs.py", "Nhật ký hệ thống", "📜", "admin-audit-logs"),
    build_safe_page("modules/admin/gmail_config.py", "Cấu hình Gmail", "✉️", "admin-gmail-config"),
    build_safe_page("modules/admin/ai_config.py", "Cấu hình AI", "🤖", "admin-ai-config"),
]

# Định tuyến Menu động theo Vai trò (Role-Based Menu)
pages = {"TỔNG QUAN": overview_pages}

if user_role in ["admin", "manager", "staff"]:
    pages["NGHIỆP VỤ"] = operation_pages

if user_role in ["admin", "manager", "viewer"]:
    pages["BÁO CÁO"] = report_pages

if user_role == "admin":
    pages["QUẢN TRỊ"] = admin_pages
elif user_role == "manager":
    pages["QUẢN TRỊ"] = [
        build_safe_page("modules/admin/categories.py", "Danh mục", "🗂️", "admin-categories"),
    ]

# 5. Khởi chạy bộ định tuyến
pg = st.navigation(pages)
pg.run()

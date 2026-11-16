import os
import streamlit as st
from supabase import create_client
from services.auth_service import (
    is_authenticated,
    get_current_user,
    logout_user,
    change_user_password,
    ROLE_DISPLAY_MAP,
)

# 1. Cấu hình trang chuẩn Enterprise (Bắt buộc đặt ở lệnh Streamlit đầu tiên)
st.set_page_config(
    page_title="Hệ thống Quản lý Công trình",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# 2. Hàm lấy nhanh số lượng tồn đọng (Live Counters) để gắn Badge lên Menu & Sidebar
@st.cache_data(ttl=20, show_spinner=False)
def get_live_navigation_badges():
    badges = {
        "unassigned_projects": 0,
        "unprocessed_emails": 0,
        "pending_confirmations": 0,
    }
    try:
        sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

        # Đếm công trình chưa phân công
        try:
            proj_res = sb.table("projects").select("assigned_to, status").execute()
            for p in (proj_res.data or []):
                st_val = str(p.get("status") or "").strip()
                if st_val in ["Hoàn thành", "Đã hoàn thành", "Tạm dừng"]:
                    continue
                asg = str(p.get("assigned_to") or "").strip()
                if not asg or asg.lower() in ["none", "null", "nan", "chưa phân công", "chưa phân nhân sự"]:
                    badges["unassigned_projects"] += 1
        except Exception:
            pass

        # Đếm email chưa xử lý
        try:
            em_res = sb.table("emails").select("processing_status").execute()
            for e in (em_res.data or []):
                if str(e.get("processing_status") or "").strip() in ["", "Chưa xử lý", "pending"]:
                    badges["unprocessed_emails"] += 1
        except Exception:
            pass

        # Đếm mục chờ xác nhận AI / Ghép nối
        try:
            cq_res = sb.table("confirmation_queue").select("decision").execute()
            for c in (cq_res.data or []):
                if str(c.get("decision") or "").strip().lower() in ["", "none", "pending", "chờ xác nhận"]:
                    badges["pending_confirmations"] += 1
        except Exception:
            pass

    except Exception:
        pass
    return badges


# 3. Hàm khởi tạo Page an toàn với url_path định danh riêng biệt
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
            st.info(
                f"📌 Module **{title}** (`{file_path}`) hiện chưa được tạo file vật lý trên hệ thống."
            )

        placeholder_page.__name__ = f"page_{url_path}"
        return st.Page(
            placeholder_page,
            title=title,
            icon=icon,
            url_path=url_path,
            default=default,
        )


# 4. CỔNG KIỂM TRA ĐĂNG NHẬP (AUTH GATE)
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


# 5. LẤY THÔNG TIN USER ĐANG ĐĂNG NHẬP & SỐ LIỆU BADGE TRỰC TIẾP
current_user = get_current_user()
user_id = str(current_user.get("id") or "")
user_name = current_user.get("full_name", "Người dùng")
user_email = current_user.get("email", "")
user_role = str(current_user.get("role") or "staff").lower()
role_badge = ROLE_DISPLAY_MAP.get(user_role, user_role.upper())

live_badges = get_live_navigation_badges()
unassigned_cnt = live_badges["unassigned_projects"]
inbox_cnt = live_badges["unprocessed_emails"]
confirm_cnt = live_badges["pending_confirmations"]

# Tạo tiêu đề động có đính kèm số lượng việc cần xử lý ngay trên thanh Menu
lbl_projects = f"Danh sách công trình ({unassigned_cnt} 🚨)" if unassigned_cnt > 0 else "Danh sách công trình"
lbl_inbox = f"Tiếp nhận email ({inbox_cnt} 📩)" if inbox_cnt > 0 else "Tiếp nhận email"
lbl_confirm = f"Chờ xác nhận ({confirm_cnt} ⏳)" if confirm_cnt > 0 else "Chờ xác nhận"


# 6. KHỞI TẠO CÁC TRANG THEO NHÓM CHỨC NĂNG
p_dashboard = build_safe_page("modules/dashboard/view.py", "Dashboard", "📊", "dashboard", default=True)

p_projects = build_safe_page("modules/projects/view.py", lbl_projects, "🏗️", "projects-list")
p_email_in = build_safe_page("modules/emails/view.py", lbl_inbox, "📥", "emails-inbox")
p_email_mgr = build_safe_page("modules/emails/manage.py", "Quản lý email", "📧", "emails-manage")
p_confirm = build_safe_page("modules/confirmation/view.py", lbl_confirm, "⏳", "confirmation-queue")
p_docs = build_safe_page("modules/documents/view.py", "Quản lý hồ sơ", "📂", "project-documents")
p_progress = build_safe_page("modules/progress/view.py", "Theo dõi tiến độ", "📈", "project-progress")
p_assign = build_safe_page("modules/assignment/view.py", "Phân công công việc", "👥", "staff-assignment")
p_proj_detail = build_safe_page("modules/projects/detail.py", "Chi tiết công trình", "🔍", "project-detail")
p_proj_create = build_safe_page("modules/projects/create.py", "Tạo mới công trình", "➕", "project-create")

p_rep_perf = build_safe_page("modules/reports/view.py", "Hiệu suất nhân viên", "🏆", "staff-performance")
p_rep_month = build_safe_page("modules/reports/monthly.py", "Báo cáo tháng", "📅", "monthly-report")
p_rep_year = build_safe_page("modules/reports/yearly.py", "Báo cáo năm", "📆", "yearly-report")

p_users = build_safe_page("modules/admin/users.py", "Nhân viên và phân quyền", "🛡️", "admin-users")
p_categories = build_safe_page("modules/admin/categories.py", "Danh mục", "🗂️", "admin-categories")
p_audit = build_safe_page("modules/admin/audit_logs.py", "Nhật ký hệ thống", "📜", "admin-audit-logs")
p_cfg_gmail = build_safe_page("modules/admin/gmail_config.py", "Cấu hình Gmail", "✉️", "admin-gmail-config")
p_cfg_ai = build_safe_page("modules/admin/ai_config.py", "Cấu hình AI", "🤖", "admin-ai-config")


# 7. ĐỊNH TUYẾN MENU ĐỘNG THEO VAI TRÒ (RBAC ROUTING)
pages = {"TỔNG QUAN": [p_dashboard]}

if user_role in ["admin", "manager", "staff"]:
    pages["NGHIỆP VỤ"] = [
        p_projects,
        p_email_in,
        p_email_mgr,
        p_confirm,
        p_docs,
        p_progress,
        p_assign,
        p_proj_detail,
        p_proj_create,
    ]

if user_role in ["admin", "manager", "viewer"]:
    pages["BÁO CÁO"] = [p_rep_perf, p_rep_month, p_rep_year]

if user_role == "admin":
    pages["QUẢN TRỊ"] = [p_users, p_categories, p_audit, p_cfg_gmail, p_cfg_ai]
elif user_role == "manager":
    pages["QUẢN TRỊ"] = [p_categories]


# 8. THANH ĐIỀU KHIỂN TRUNG TÂM TRÊN SIDEBAR (USER PROFILE + ĐỔI MẬT KHẨU + THÔNG BÁO)
with st.sidebar:
    st.markdown("### 🏗️ QUẢN LÝ CÔNG TRÌNH")
    with st.container(border=True):
        st.markdown(f"👤 **{user_name}**")
        if user_email:
            st.caption(f"📧 {user_email}")
        st.caption(f"🛡️ {role_badge}")

        # Popover Đổi mật khẩu bảo mật ngay tại chỗ
        with st.popover("🔑 Đổi mật khẩu", use_container_width=True):
            st.markdown("##### 🔒 Đổi mật khẩu cá nhân")
            old_pw = st.text_input("Mật khẩu hiện tại", type="password", key="nav_old_pw")
            new_pw = st.text_input("Mật khẩu mới (>= 6 ký tự)", type="password", key="nav_new_pw")
            confirm_pw = st.text_input("Xác nhận mật khẩu mới", type="password", key="nav_conf_pw")

            if st.button("💾 Lưu mật khẩu mới", type="primary", width="stretch"):
                if not old_pw or not new_pw:
                    st.warning("⚠️ Vui lòng nhập đầy đủ mật khẩu!")
                elif new_pw != confirm_pw:
                    st.error("❌ Mật khẩu xác nhận không khớp!")
                else:
                    cp_res = change_user_password(user_id, old_pw, new_pw)
                    if cp_res["success"]:
                        st.success(cp_res["message"])
                    else:
                        st.error(cp_res["message"])

        col_sb1, col_sb2 = st.columns(2)
        with col_sb1:
            if st.button("🔄 Làm mới", width="stretch", help="Xóa bộ nhớ đệm và cập nhật dữ liệu mới nhất"):
                st.cache_data.clear()
                st.rerun()
        with col_sb2:
            if st.button("🚪 Thoát", width="stretch", type="secondary", help="Đăng xuất khỏi phiên làm việc"):
                logout_user()
                st.rerun()

    # Khay thông báo việc gấp nếu có tồn đọng
    if user_role in ["admin", "manager", "staff"] and (unassigned_cnt > 0 or inbox_cnt > 0):
        st.caption(
            f"⚡ **Cần chú ý:** `{unassigned_cnt}` CT chưa giao • `{inbox_cnt}` Email mới"
        )


# 9. KHỞI CHẠY BỘ ĐỊNH TUYẾN
pg = st.navigation(pages)
pg.run()

import streamlit as st
from services.auth_service import (
    authenticate_user,
    get_default_staff_password,
    ROLE_DISPLAY_MAP,
)
from services.admin_service import get_all_users, seed_default_staff_profiles

# CSS tùy chỉnh tạo khung Card đăng nhập hiện đại, sang trọng ở chính giữa màn hình
st.markdown(
    """
    <style>
    .login-header {
        text-align: center;
        padding-top: 1.5rem;
        padding-bottom: 1rem;
    }
    .login-header h1 {
        font-size: 2.1rem;
        font-weight: 800;
        margin-bottom: 0.3rem;
    }
    .login-sub {
        color: #9ca3af;
        font-size: 0.98rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

col_spacer_l, col_main, col_spacer_r = st.columns([1.2, 1.8, 1.2])

with col_main:
    st.markdown(
        """
        <div class="login-header">
            <h1>🏗️ HỆ THỐNG QUẢN LÝ CÔNG TRÌNH</h1>
            <div class="login-sub">Nền tảng Điều phối Phối màu & Tự động hóa AI chuẩn Enterprise</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.subheader("🔐 Đăng nhập Hệ thống")

        with st.form("login_form", clear_on_submit=False):
            email_or_name = st.text_input(
                "📧 Email hoặc Tên nhân sự",
                placeholder="VD: admin@congtrinh.vn, han@congtrinh.vn hoặc Ms Hân...",
            )
            password = st.text_input(
                "🔑 Mật khẩu",
                type="password",
                placeholder="Nhập mật khẩu đăng nhập...",
            )
            remember = st.checkbox("Ghi nhớ phiên đăng nhập trên trình duyệt này", value=True)

            btn_login = st.form_submit_button(
                "🚀 Đăng nhập vào Workspace",
                type="primary",
                width="stretch",
            )

            if btn_login:
                res = authenticate_user(email_or_name, password)
                if res["success"]:
                    st.session_state["authenticated"] = True
                    st.session_state["auth_user"] = res["user"]
                    st.toast(res["message"], icon="🎉")
                    st.rerun()
                else:
                    st.error(res["message"])

    # Khay truy cập nhanh & thông tin tài khoản dành cho Kiểm thử / Triển khai nội bộ
    with st.expander("⚡ Đăng nhập Nhanh & Kiểm thử Phân quyền (Quick Access)", expanded=True):
        users_in_db = get_all_users()
        default_pw = get_default_staff_password()

        st.caption(
            f"💡 **Mật khẩu mặc định:** Tài khoản Admin tối cao là `admin@congtrinh.vn` / `admin123`. "
            f"Các nhân sự trong bảng `profiles` có mật khẩu mặc định là `{default_pw}`."
        )

        q1, q2 = st.columns(2)
        with q1:
            if st.button("👑 Vào nhanh bằng quyền Admin", width="stretch"):
                res = authenticate_user("admin@congtrinh.vn", "admin123")
                if res["success"]:
                    st.session_state["authenticated"] = True
                    st.session_state["auth_user"] = res["user"]
                    st.rerun()

        with q2:
            if users_in_db:
                user_options = {
                    f"{u.get('full_name')} ({u.get('role', 'staff')})": u
                    for u in users_in_db
                    if u.get("is_active", True) is not False
                }
                chosen_label = st.selectbox(
                    "Chọn nhân sự có sẵn để test:",
                    list(user_options.keys()),
                    label_visibility="collapsed",
                )
                if st.button(f"👷 Đăng nhập: {chosen_label.split('(')[0].strip()}", width="stretch"):
                    chosen_u = user_options[chosen_label]
                    res = authenticate_user(chosen_u.get("email") or chosen_u.get("full_name"), default_pw)
                    if res["success"]:
                        st.session_state["authenticated"] = True
                        st.session_state["auth_user"] = res["user"]
                        st.rerun()
            else:
                if st.button("🔄 Khởi tạo 5 Nhân sự chuẩn vào DB", width="stretch"):
                    seed_res = seed_default_staff_profiles()
                    if seed_res["success"]:
                        st.success(seed_res["message"])
                        st.rerun()
                    else:
                        st.warning(seed_res["message"])

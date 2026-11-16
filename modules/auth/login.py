import streamlit as st
from services.auth_service import authenticate_user, check_brute_force_lockout

st.markdown(
    """
    <style>
    .login-header {
        text-align: center;
        padding-top: 2.5rem;
        padding-bottom: 1.2rem;
    }
    .login-header h1 {
        font-size: 2.0rem;
        font-weight: 800;
        margin-bottom: 0.3rem;
    }
    .login-sub {
        color: #9ca3af;
        font-size: 0.95rem;
    }
    .security-footer {
        text-align: center;
        color: #6b7280;
        font-size: 0.82rem;
        margin-top: 1.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

col_spacer_l, col_main, col_spacer_r = st.columns([1.3, 1.4, 1.3])

with col_main:
    st.markdown(
        """
        <div class="login-header">
            <h1>🏗️ HỆ THỐNG QUẢN LÝ CÔNG TRÌNH</h1>
            <div class="login-sub">Cổng Xác thực Nội bộ & Điều phối Phân quyền (RBAC)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    is_locked, wait_sec = check_brute_force_lockout()
    if is_locked:
        st.error(f"🔒 Tạm khóa đăng nhập do nhập sai nhiều lần. Vui lòng thử lại sau **{wait_sec} giây**.")

    with st.container(border=True):
        st.subheader("🔐 Đăng nhập Tài khoản")

        with st.form("secure_login_form", clear_on_submit=False):
            email_or_name = st.text_input(
                "📧 Email công việc",
                placeholder="Nhập địa chỉ email của bạn...",
                disabled=is_locked,
            )
            password = st.text_input(
                "🔑 Mật khẩu",
                type="password",
                placeholder="Nhập mật khẩu bảo mật...",
                disabled=is_locked,
            )

            btn_login = st.form_submit_button(
                "🚀 Đăng nhập Hệ thống",
                type="primary",
                width="stretch",
                disabled=is_locked,
            )

            if btn_login:
                res = authenticate_user(email_or_name, password)
                if res["success"]:
                    st.session_state["authenticated"] = True
                    st.session_state["auth_user"] = res["user"]
                    st.toast(res["message"], icon="🔓")
                    st.rerun()
                else:
                    st.error(res["message"])

    st.markdown(
        """
        <div class="security-footer">
            🛡️ Phiên làm việc được bảo vệ bằng mã hóa SHA-256 & Nhật ký Audit Logs.<br>
            Nếu quên mật khẩu, vui lòng liên hệ Quản trị viên hệ thống để được cấp lại.
        </div>
        """,
        unsafe_allow_html=True,
    )

import streamlit as st
from services.auth_service import (
    authenticate_user,
    register_user_from_login_screen,
    check_brute_force_lockout,
    ROLE_DISPLAY_MAP,
)

st.markdown(
    """
    <style>
    .login-header {
        text-align: center;
        padding-top: 2.0rem;
        padding-bottom: 1.0rem;
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

col_spacer_l, col_main, col_spacer_r = st.columns([1.2, 1.6, 1.2])

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
        st.error(
            f"🔒 Tạm khóa đăng nhập do nhập sai nhiều lần. Vui lòng thử lại sau **{wait_sec} giây**."
        )

    with st.container(border=True):
        tab_login, tab_register = st.tabs([
            "🔐 Đăng nhập Hệ thống",
            "➕ Tạo Tài khoản / User mới",
        ])

        # ======================================================================
        # TAB 1: ĐĂNG NHẬP HỆ THỐNG
        # ======================================================================
        with tab_login:
            with st.form("secure_login_form", clear_on_submit=False):
                email_or_name = st.text_input(
                    "📧 Email hoặc Họ tên nhân sự",
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

        # ======================================================================
        # TAB 2: TẠO TÀI KHOẢN / USER MỚI NGAY TRÊN MÀN HÌNH ĐĂNG NHẬP
        # ======================================================================
        with tab_register:
            st.caption("Điền thông tin bên dưới để khởi tạo hồ sơ nhân sự mới vào hệ thống:")
            with st.form("self_register_form", clear_on_submit=False):
                reg_name = st.text_input(
                    "👤 Họ và Tên hiển thị *",
                    placeholder="VD: Ms Hân, Trần Phương Hân...",
                )
                reg_email = st.text_input(
                    "📧 Địa chỉ Email công việc *",
                    placeholder="VD: han@congtrinh.vn",
                )

                c_pw1, c_pw2 = st.columns(2)
                with c_pw1:
                    reg_pass = st.text_input(
                        "🔑 Mật khẩu (>= 6 ký tự) *",
                        type="password",
                        placeholder="Nhập mật khẩu...",
                    )
                with c_pw2:
                    reg_pass_conf = st.text_input(
                        "🔒 Xác nhận mật khẩu *",
                        type="password",
                        placeholder="Nhập lại mật khẩu...",
                    )

                role_keys = list(ROLE_DISPLAY_MAP.keys())
                reg_role = st.selectbox(
                    "🛡️ Vai trò đăng ký",
                    role_keys,
                    index=2,  # Mặc định là 'staff' (Nhân viên Kỹ thuật / Phối màu)
                    format_func=lambda x: ROLE_DISPLAY_MAP.get(x, x),
                )

                reg_invite = st.text_input(
                    "🎟️ Mã Ủy quyền Nội bộ (Chỉ bắt buộc nếu đăng ký quyền Admin / Manager)",
                    type="password",
                    placeholder="Nhập mã bảo mật nếu tạo tài khoản Quản trị...",
                )

                auto_login_after_reg = st.checkbox(
                    "Tự động đăng nhập vào hệ thống ngay sau khi tạo tài khoản",
                    value=True,
                )

                btn_register = st.form_submit_button(
                    "✨ Tạo User & Lưu vào Hệ thống",
                    type="primary",
                    width="stretch",
                )

                if btn_register:
                    if reg_pass != reg_pass_conf:
                        st.error("❌ Mật khẩu xác nhận không khớp!")
                    else:
                        reg_res = register_user_from_login_screen(
                            full_name=reg_name,
                            email=reg_email,
                            password=reg_pass,
                            role=reg_role,
                            invite_code=reg_invite,
                        )
                        if reg_res["success"]:
                            st.success(reg_res["message"])
                            if auto_login_after_reg and reg_res.get("user"):
                                st.session_state["authenticated"] = True
                                st.session_state["auth_user"] = reg_res["user"]
                                st.toast("🎉 Đã đăng nhập tự động!", icon="🚀")
                                st.rerun()
                        else:
                            st.error(reg_res["message"])

    st.markdown(
        """
        <div class="security-footer">
            🛡️ Phiên làm việc được bảo vệ bằng mã hóa SHA-256 & Nhật ký Audit Logs.<br>
            Nếu quên mật khẩu, vui lòng liên hệ Quản trị viên hệ thống để được cấp lại.
        </div>
        """,
        unsafe_allow_html=True,
    )

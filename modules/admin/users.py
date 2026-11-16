import streamlit as st
import pandas as pd
from services.auth_service import admin_set_user_password
from services.admin_service import (
    get_all_users,
    create_new_user,
    update_user_profile,
    delete_user_profile,
    seed_default_staff_profiles,
)

st.title("🛡️ Quản lý Nhân viên & Phân quyền (Users & Roles)")

ROLE_LABELS = {
    "admin": "👑 Quản trị viên (Admin)",
    "manager": "📋 Quản lý / Điều phối (Manager)",
    "staff": "👷 Nhân viên Kỹ thuật / Phối màu (Staff)",
    "viewer": "👁️ Chỉ xem báo cáo (Viewer)",
}
ROLE_KEYS = list(ROLE_LABELS.keys())

# 1. Tải danh sách nhân viên từ bảng profiles
users_data = get_all_users()

total_u = len(users_data)
active_u = sum(1 for u in users_data if u.get("is_active", True))
admin_u = sum(1 for u in users_data if str(u.get("role") or "").lower() in ["admin", "manager"])
secured_u = sum(1 for u in users_data if u.get("password_hash"))

k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Tổng Nhân sự", total_u)
k2.metric("🟢 Đang hoạt động", active_u)
k3.metric("👑 Quản trị / Quản lý", admin_u)
k4.metric("🔐 Đã có Mật khẩu riêng", f"{secured_u}/{total_u}")

st.divider()

# 2. Thanh công cụ Danh sách, Tạo User mới & Đồng bộ nhanh
tab_list, tab_create, tab_sync = st.tabs([
    f"📋 Danh sách & Phân quyền ({total_u})",
    "➕ Tạo User / Nhân viên mới",
    "⚡ Đồng bộ Nhân sự Mặc định & SQL Fix",
])

# --- TAB 1: DANH SÁCH, CẬP NHẬT PHÂN QUYỀN & ĐẶT LẠI MẬT KHẨU ---
with tab_list:
    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    with col_s1:
        kw = st.text_input("🔍 Tìm kiếm theo Họ tên hoặc Email...", placeholder="Nhập tên nhân viên hoặc email...")
    with col_s2:
        role_filter = st.selectbox("Lọc theo Vai trò", ["Tất cả"] + ROLE_KEYS)
    with col_s3:
        st.write("")
        st.write("")
        if st.button("🔄 Làm mới danh sách", width="stretch"):
            st.cache_data.clear()
            st.rerun()

    if users_data:
        df_u = pd.DataFrame(users_data).fillna("")
        if "is_active" not in df_u.columns:
            df_u["is_active"] = True
        if "role" not in df_u.columns:
            df_u["role"] = "staff"
        if "password_hash" not in df_u.columns:
            df_u["password_hash"] = ""

        df_u["role_display"] = df_u["role"].apply(lambda r: ROLE_LABELS.get(str(r).lower(), str(r)))
        df_u["status_display"] = df_u["is_active"].apply(lambda a: "🟢 Đang hoạt động" if a else "🔴 Tạm khóa")
        df_u["security_display"] = df_u["password_hash"].apply(
            lambda h: "🔐 Đã mã hóa SHA-256" if str(h).strip() else "⚠️ Dùng MK khởi tạo"
        )

        if role_filter != "Tất cả":
            df_u = df_u[df_u["role"].astype(str).str.lower() == role_filter]
        if kw:
            k_low = kw.lower().strip()
            df_u = df_u[
                df_u["full_name"].astype(str).str.lower().str.contains(k_low, na=False)
                | df_u["email"].astype(str).str.lower().str.contains(k_low, na=False)
            ]

        disp_df = df_u[
            ["id", "full_name", "email", "role_display", "security_display", "status_display"]
        ].rename(
            columns={
                "id": "UUID Nhân sự",
                "full_name": "Họ và Tên",
                "email": "Địa chỉ Email",
                "role_display": "Vai trò / Phân quyền",
                "security_display": "Bảo mật Mật khẩu",
                "status_display": "Trạng thái",
            }
        )

        st.markdown("#### Click chọn 1 nhân sự trong bảng để chỉnh sửa quyền hạn hoặc cấp lại mật khẩu:")
        ev = st.dataframe(
            disp_df,
            width="stretch",
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
        )

        if ev.selection.rows:
            sel_user = df_u.iloc[ev.selection.rows[0]]
            uid = sel_user["id"]

            st.divider()
            col_edit_info, col_edit_pw = st.columns([3, 2])

            with col_edit_info:
                st.subheader(f"✏️ Chỉnh sửa Hồ sơ: `{sel_user['full_name']}`")
                with st.form(f"edit_user_form_{uid}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        ed_name = st.text_input("Họ và Tên hiển thị *", value=sel_user["full_name"])
                        ed_email = st.text_input("Email công việc *", value=sel_user["email"])
                    with c2:
                        curr_r = str(sel_user["role"]).lower()
                        r_idx = ROLE_KEYS.index(curr_r) if curr_r in ROLE_KEYS else 2
                        ed_role = st.selectbox(
                            "Phân quyền hệ thống",
                            ROLE_KEYS,
                            index=r_idx,
                            format_func=lambda x: ROLE_LABELS.get(x, x),
                        )
                        ed_active = st.checkbox(
                            "Cho phép hoạt động (Active)",
                            value=bool(sel_user["is_active"]),
                        )

                    btn_save = st.form_submit_button(
                        "💾 Lưu Cập nhật Nhân sự",
                        type="primary",
                        width="stretch",
                    )
                    if btn_save:
                        res = update_user_profile(uid, ed_name, ed_email, ed_role, ed_active)
                        if res["success"]:
                            st.success(res["message"])
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(res["message"])

            with col_edit_pw:
                st.subheader("🔑 Cấp / Đặt lại Mật khẩu")
                with st.form(f"reset_pw_form_{uid}"):
                    new_staff_pw = st.text_input(
                        "Mật khẩu mới (tối thiểu 6 ký tự) *",
                        type="password",
                        placeholder="Nhập mật khẩu mới...",
                    )
                    confirm_staff_pw = st.text_input(
                        "Nhập lại mật khẩu mới *",
                        type="password",
                        placeholder="Xác nhận mật khẩu...",
                    )
                    btn_set_pw = st.form_submit_button(
                        "🔒 Cập nhật Mật khẩu (SHA-256)",
                        type="primary",
                        width="stretch",
                    )
                    if btn_set_pw:
                        if not new_staff_pw or len(new_staff_pw.strip()) < 6:
                            st.warning("⚠️ Mật khẩu phải có từ 6 ký tự trở lên!")
                        elif new_staff_pw != confirm_staff_pw:
                            st.error("❌ Mật khẩu xác nhận không khớp!")
                        else:
                            pw_res = admin_set_user_password(uid, new_staff_pw)
                            if pw_res["success"]:
                                st.success(pw_res["message"])
                                st.rerun()
                            else:
                                st.error(pw_res["message"])

                st.write("")
                if st.button(
                    "🗑️ Xóa nhân viên này khỏi bảng profiles",
                    type="secondary",
                    width="stretch",
                ):
                    del_res = delete_user_profile(uid)
                    if del_res["success"]:
                        st.toast(del_res["message"], icon="🗑️")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(del_res["message"])
    else:
        st.info(
            "📭 Bảng `profiles` hiện đang trống. Hãy chuyển sang Tab **'➕ Tạo User / Nhân viên mới'** "
            "hoặc **'⚡ Đồng bộ Nhân sự Mặc định'** để khởi tạo ngay!"
        )

# --- TAB 2: TẠO USER MỚI ---
with tab_create:
    st.subheader("➕ Thêm mới Nhân viên & Cấp Tài khoản Đăng nhập")
    with st.form("create_new_user_form"):
        c_n1, c_n2 = st.columns(2)
        with c_n1:
            new_fullname = st.text_input(
                "Họ tên / Tên gọi nhân sự *",
                placeholder="VD: Ms Hân, Mr Tuấn...",
            )
            new_email = st.text_input(
                "Địa chỉ Email đăng nhập *",
                placeholder="VD: han.nguyen@congty.com",
            )
            new_role = st.selectbox(
                "Vai trò & Phân quyền *",
                ROLE_KEYS,
                index=2,
                format_func=lambda x: ROLE_LABELS.get(x, x),
            )
        with c_n2:
            new_pass = st.text_input(
                "Mật khẩu khởi tạo (Tối thiểu 6 ký tự) *",
                type="password",
                placeholder="Nhập mật khẩu bảo mật cho nhân viên...",
            )
            new_pass_confirm = st.text_input(
                "Xác nhận mật khẩu *",
                type="password",
                placeholder="Nhập lại mật khẩu...",
            )
            new_active = st.checkbox("Kích hoạt tài khoản ngay sau khi tạo", value=True)

        submitted_new = st.form_submit_button(
            "🚀 Tạo Nhân viên & Mã hóa Mật khẩu",
            type="primary",
            width="stretch",
        )
        if submitted_new:
            if not new_fullname or not new_email:
                st.warning("⚠️ Vui lòng nhập đầy đủ Họ tên và Địa chỉ Email!")
            elif not new_pass or len(new_pass.strip()) < 6:
                st.warning("⚠️ Vui lòng đặt mật khẩu tối thiểu 6 ký tự!")
            elif new_pass != new_pass_confirm:
                st.error("❌ Mật khẩu xác nhận không khớp!")
            else:
                res = create_new_user(
                    full_name=new_fullname,
                    email=new_email,
                    role=new_role,
                    is_active=new_active,
                    password=new_pass,
                )
                if res["success"]:
                    st.success(res["message"])
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(res["message"])

# --- TAB 3: ĐỒNG BỘ NHANH 5 NHÂN SỰ CHUẨN & SQL HỖ TRỢ ---
with tab_sync:
    st.subheader("⚡ Khởi tạo nhanh Đội ngũ Nhân sự Mặc định")
    st.markdown(
        "Chức năng này sẽ tự động thêm 5 nhân sự đang vận hành (`Ms Hân`, `Mr Thái`, `Mr Thịnh`, `Ms Hương`, `Ms Hiếu`) "
        "vào bảng `profiles` để đồng bộ với toàn bộ các bảng `projects`, `project_status_history` và `audit_logs`."
    )
    if st.button("🚀 Đồng bộ 5 Nhân sự chuẩn vào bảng Profiles ngay", type="primary"):
        s_res = seed_default_staff_profiles()
        if s_res["success"]:
            st.success(s_res["message"])
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(s_res["message"])

    st.divider()
    st.markdown("#### 🛠️ Lệnh SQL Chuẩn hóa Bảng `profiles` & Cột Mã hóa Mật khẩu (`password_hash`)")
    st.caption(
        "Nếu bạn chưa thêm cột `password_hash` hoặc gặp lỗi phân quyền `42501` / khóa ngoại `23503`, "
        "hãy chạy đoạn SQL dưới đây 1 lần trong Supabase SQL Editor:"
    )
    st.code(
        """-- 1. Thêm cột lưu mật khẩu mã hóa SHA-256 cho từng nhân sự
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- 2. Gỡ khóa ngoại cứng từ auth.users và cấp quyền truy cập bảng profiles
ALTER TABLE public.profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey;
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_auth_user_id_fkey;
ALTER TABLE public.profiles ALTER COLUMN id SET DEFAULT gen_random_uuid();
GRANT ALL PRIVILEGES ON TABLE public.profiles TO anon, authenticated, service_role;""",
        language="sql",
    )

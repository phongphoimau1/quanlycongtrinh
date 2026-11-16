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
staff_u = total_u - admin_u

k1, k2, k3, k4 = st.columns(4)
k1.metric("👥 Tổng Nhân sự", total_u)
k2.metric("🟢 Đang hoạt động", active_u)
k3.metric("👑 Quản trị / Quản lý", admin_u)
k4.metric("👷 Nhân viên Chuyên môn", staff_u)

st.divider()

# 2. Thanh công cụ Tạo User mới & Đồng bộ nhanh
tab_list, tab_create, tab_sync = st.tabs([
    f"📋 Danh sách & Phân quyền ({total_u})",
    "➕ Tạo User / Nhân viên mới",
    "⚡ Đồng bộ Nhân sự Mặc định & SQL Fix",
])

# --- TAB 1: DANH SÁCH & CẬP NHẬT PHÂN QUYỀN ---
with tab_list:
    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    with col_s1:
        kw = st.text_input("🔍 Tìm kiếm theo Họ tên hoặc Email...", placeholder="Nhập tên nhân viên...")
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

        df_u["role_display"] = df_u["role"].apply(lambda r: ROLE_LABELS.get(str(r).lower(), str(r)))
        df_u["status_display"] = df_u["is_active"].apply(lambda a: "🟢 Đang hoạt động" if a else "🔴 Tạm khóa")

        if role_filter != "Tất cả":
            df_u = df_u[df_u["role"].astype(str).str.lower() == role_filter]
        if kw:
            k_low = kw.lower()
            df_u = df_u[
                df_u["full_name"].astype(str).str.lower().str.contains(k_low, na=False)
                | df_u["email"].astype(str).str.lower().str.contains(k_low, na=False)
            ]

        disp_df = df_u[["id", "full_name", "email", "role_display", "status_display"]].rename(
            columns={
                "id": "UUID Nhân sự",
                "full_name": "Họ và Tên",
                "email": "Địa chỉ Email",
                "role_display": "Vai trò / Phân quyền",
                "status_display": "Trạng thái",
            }
        )

        st.markdown("#### Click chọn 1 nhân sự trong bảng để chỉnh sửa quyền hạn hoặc thông tin:")
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
            st.subheader(f"✏️ Chỉnh sửa Nhân sự: `{sel_user['full_name']}`")

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
                    ed_active = st.checkbox("Cho phép hoạt động (Active)", value=bool(sel_user["is_active"]))

                btn_save = st.form_submit_button("💾 Lưu Cập nhật Nhân sự", type="primary", width="stretch")
                if btn_save:
                    res = update_user_profile(uid, ed_name, ed_email, ed_role, ed_active)
                    if res["success"]:
                        st.success(res["message"])
                        st.rerun()
                    else:
                        st.error(res["message"])

            if st.button("🗑️ Xóa nhân viên này khỏi bảng profiles", type="secondary"):
                del_res = delete_user_profile(uid)
                if del_res["success"]:
                    st.toast(del_res["message"], icon="🗑️")
                    st.rerun()
                else:
                    st.error(del_res["message"])
    else:
        st.info("📭 Bảng `profiles` hiện đang trống. Hãy chuyển sang Tab **'➕ Tạo User / Nhân viên mới'** hoặc **'⚡ Đồng bộ Nhân sự Mặc định'** để khởi tạo ngay!")

# --- TAB 2: TẠO USER MỚI ---
with tab_create:
    st.subheader("➕ Thêm mới Nhân viên vào Hệ thống")
    with st.form("create_new_user_form"):
        c_n1, c_n2 = st.columns(2)
        with c_n1:
            new_fullname = st.text_input("Họ tên / Tên gọi nhân sự *", placeholder="VD: Ms Hân, Mr Tuấn...")
            new_email = st.text_input("Địa chỉ Email *", placeholder="VD: han.nguyen@congty.com")
        with c_n2:
            new_role = st.selectbox(
                "Vai trò & Phân quyền *",
                ROLE_KEYS,
                index=2,
                format_func=lambda x: ROLE_LABELS.get(x, x),
            )
            new_pass = st.text_input(
                "Mật khẩu đăng nhập (Tùy chọn - từ 6 ký tự nếu tạo cả tài khoản Auth)",
                type="password",
                placeholder="Để trống nếu chỉ tạo hồ sơ điều phối công trình",
            )

        new_active = st.checkbox("Kích hoạt tài khoản ngay sau khi tạo", value=True)

        submitted_new = st.form_submit_button("🚀 Tạo Nhân viên mới", type="primary", width="stretch")
        if submitted_new:
            if not new_fullname or not new_email:
                st.warning("⚠️ Vui lòng nhập đầy đủ Họ tên và Địa chỉ Email!")
            else:
                res = create_new_user(
                    full_name=new_fullname,
                    email=new_email,
                    role=new_role,
                    is_active=new_active,
                    password=new_pass if new_pass else None,
                )
                if res["success"]:
                    st.success(res["message"])
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
            st.rerun()
        else:
            st.error(s_res["message"])

    st.divider()
    st.markdown("#### 🛠️ Lệnh SQL Mở khóa Bảng `profiles` (Chỉ dùng khi báo lỗi khóa ngoại `23503` từ `auth.users`)")
    st.caption(
        "Nếu khi tạo nhân viên mới hệ thống báo lỗi khóa ngoại `profiles_id_fkey` hoặc `profiles_auth_user_id_fkey` "
        "(do Supabase mặc định bắt buộc mỗi dòng trong `profiles` phải có tài khoản đăng nhập trước trong `auth.users`), "
        "bạn chỉ cần chạy đoạn SQL dưới đây 1 lần trong Supabase SQL Editor để cho phép tạo nhân sự tự do:"
    )
    st.code(
        """-- Cho phép tạo trực tiếp nhân viên trong bảng profiles mà không bị chặn bởi auth.users
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey;
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_auth_user_id_fkey;
ALTER TABLE public.profiles ALTER COLUMN id SET DEFAULT gen_random_uuid();
GRANT ALL PRIVILEGES ON TABLE public.profiles TO anon, authenticated, service_role;""",
        language="sql",
    )

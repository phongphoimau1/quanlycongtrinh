from datetime import datetime
import streamlit as st
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ROLE_DISPLAY_MAP = {
    "admin": "👑 Quản trị viên (Admin)",
    "manager": "📋 Quản lý / Điều phối (Manager)",
    "staff": "👷 Nhân viên Kỹ thuật / Phối màu (Staff)",
    "viewer": "👁️ Chỉ xem báo cáo (Viewer)",
}


def get_default_staff_password():
    try:
        return str(st.secrets.get("DEFAULT_STAFF_PASSWORD", "123456"))
    except Exception:
        return "123456"


def authenticate_user(email_or_name: str, password: str):
    """
    Xác thực người dùng theo 3 tầng:
    1. Kiểm tra tài khoản Quản trị tối cao (Master Admin) cấu hình trong st.secrets (nếu có).
    2. Tra cứu hồ sơ trong bảng profiles (kiểm tra trạng thái is_active).
    3. Xác thực qua Supabase Auth hoặc mật khẩu nội bộ.
    """
    clean_input = str(email_or_name or "").strip()
    clean_pass = str(password or "").strip()

    if not clean_input or not clean_pass:
        return {"success": False, "message": "⚠️ Vui lòng nhập đầy đủ Email/Tên và Mật khẩu!"}

    # 1. Kiểm tra tài khoản Master Admin dự phòng (đảm bảo luôn vào được hệ thống khi bảng profiles trống)
    master_email = str(st.secrets.get("ADMIN_EMAIL", "admin@congtrinh.vn")).lower()
    master_pass = str(st.secrets.get("ADMIN_PASSWORD", "admin123"))

    if clean_input.lower() in [master_email, "admin"] and clean_pass == master_pass:
        user_info = {
            "id": "00000000-0000-0000-0000-000000000000",
            "full_name": "Quản trị viên Hệ thống",
            "email": master_email,
            "role": "admin",
            "is_active": True,
            "login_at": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
        }
        _record_login_audit(user_info)
        return {"success": True, "user": user_info, "message": "🎉 Đăng nhập quyền Quản trị viên thành công!"}

    # 2. Tìm hồ sơ nhân viên trong bảng profiles theo Email hoặc Họ tên
    matched_profile = None
    try:
        res = supabase.table("profiles").select("*").execute()
        profiles = res.data if res.data else []
        target = clean_input.lower()
        for p in profiles:
            p_email = str(p.get("email") or "").strip().lower()
            p_name = str(p.get("full_name") or "").strip().lower()
            if target == p_email or target == p_name:
                matched_profile = p
                break
    except Exception as e:
        print(f"Loi truy van profiles khi dang nhap: {e}")

    # 3. Thử xác thực qua Supabase Auth nếu người dùng nhập định dạng email
    auth_verified = False
    if "@" in clean_input:
        try:
            auth_res = supabase.auth.sign_in_with_password({
                "email": clean_input.lower(),
                "password": clean_pass,
            })
            if auth_res and getattr(auth_res, "user", None):
                auth_verified = True
        except Exception:
            auth_verified = False

    # 4. Nếu tìm thấy trong bảng profiles
    if matched_profile:
        if matched_profile.get("is_active") is False:
            return {
                "success": False,
                "message": "🚫 Tài khoản này hiện đang bị tạm khóa. Vui lòng liên hệ Quản trị viên!",
            }

        default_pw = get_default_staff_password()
        if auth_verified or clean_pass in [default_pw, master_pass]:
            user_info = {
                "id": str(matched_profile.get("id")),
                "full_name": matched_profile.get("full_name") or matched_profile.get("email"),
                "email": matched_profile.get("email", ""),
                "role": str(matched_profile.get("role") or "staff").lower(),
                "is_active": True,
                "login_at": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
            }
            _record_login_audit(user_info)
            return {
                "success": True,
                "user": user_info,
                "message": f"🎉 Xin chào {user_info['full_name']}!",
            }
        else:
            return {"success": False, "message": "❌ Mật khẩu không chính xác!"}

    return {
        "success": False,
        "message": "❌ Không tìm thấy tài khoản nhân sự trong hệ thống. Vui lòng kiểm tra lại Email hoặc Họ tên!",
    }


def _record_login_audit(user_info: dict):
    """Ghi nhận lịch sử đăng nhập vào bảng audit_logs."""
    try:
        org_res = supabase.table("organizations").select("id").limit(1).execute()
        org_id = org_res.data[0]["id"] if org_res.data else None
        actor_id = user_info.get("id")
        if actor_id == "00000000-0000-0000-0000-000000000000":
            actor_id = None

        supabase.table("audit_logs").insert({
            "organization_id": org_id,
            "action": "USER_LOGIN",
            "entity_type": "profiles",
            "entity_id": actor_id,
            "details": {
                "full_name": user_info.get("full_name"),
                "email": user_info.get("email"),
                "role": user_info.get("role"),
            },
            "actor_id": actor_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }).execute()
    except Exception:
        pass


def get_current_user():
    return st.session_state.get("auth_user", None)


def is_authenticated():
    return bool(st.session_state.get("authenticated", False) and st.session_state.get("auth_user"))


def logout_user():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state["authenticated"] = False
    st.session_state["auth_user"] = None

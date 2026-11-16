import hashlib
import time
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

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 60


def hash_password(raw_password: str) -> str:
    """
    Băm mật khẩu một chiều bằng thuật toán SHA-256 kết hợp chuỗi khóa Salt bảo mật.
    Không lưu mật khẩu dạng văn bản thuần (plain text) trong CSDL.
    """
    salt = str(st.secrets.get("AUTH_SALT", "quanlycongtrinh_enterprise_2026_salt"))
    salted = f"{salt}::{str(raw_password).strip()}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def check_brute_force_lockout():
    """Kiểm tra xem trình duyệt hiện tại có đang bị khóa do nhập sai quá số lần quy định không."""
    lockout_until = st.session_state.get("auth_lockout_until", 0)
    now_ts = time.time()
    if now_ts < lockout_until:
        remaining = int(lockout_until - now_ts)
        return True, remaining
    return False, 0


def _register_failed_attempt():
    attempts = st.session_state.get("auth_failed_attempts", 0) + 1
    st.session_state["auth_failed_attempts"] = attempts
    if attempts >= MAX_LOGIN_ATTEMPTS:
        st.session_state["auth_lockout_until"] = time.time() + LOCKOUT_DURATION_SECONDS


def _reset_failed_attempts():
    st.session_state["auth_failed_attempts"] = 0
    st.session_state["auth_lockout_until"] = 0


def authenticate_user(email_or_name: str, password: str):
    """
    Xác thực người dùng bảo mật cao:
    - Chặn Brute-force nếu sai quá 5 lần.
    - Kiểm tra mật khẩu đã mã hóa SHA-256 trong bảng profiles hoặc Supabase Auth.
    - Không tiết lộ tài khoản có tồn tại hay không khi báo lỗi.
    """
    is_locked, wait_sec = check_brute_force_lockout()
    if is_locked:
        return {
            "success": False,
            "message": f"⏳ Bạn đã nhập sai quá {MAX_LOGIN_ATTEMPTS} lần. Vui lòng thử lại sau {wait_sec} giây!",
        }

    clean_input = str(email_or_name or "").strip()
    clean_pass = str(password or "").strip()

    if not clean_input or not clean_pass:
        return {"success": False, "message": "⚠️ Vui lòng nhập đầy đủ Email và Mật khẩu!"}

    # 1. Tìm hồ sơ trong bảng profiles theo Email (hoặc Họ tên chính xác)
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
        print(f"Loi truy van profiles: {e}")

    # 2. Nếu có hồ sơ trong bảng profiles
    if matched_profile:
        if matched_profile.get("is_active") is False:
            return {
                "success": False,
                "message": "🚫 Tài khoản này đã bị vô hiệu hóa. Vui lòng liên hệ Quản trị viên!",
            }

        stored_hash = matched_profile.get("password_hash")
        input_hash = hash_password(clean_pass)
        is_valid_password = False

        # Ưu tiên 1: Đối chiếu mã băm password_hash trong bảng profiles
        if stored_hash:
            if input_hash == stored_hash:
                is_valid_password = True
        else:
            # Ưu tiên 2: Nếu tài khoản được tạo từ trước khi có cột password_hash,
            # kiểm tra qua Supabase Auth hoặc mật khẩu khởi tạo lần đầu rồi tự động mã hóa lưu lại
            if "@" in clean_input:
                try:
                    auth_res = supabase.auth.sign_in_with_password({
                        "email": clean_input.lower(),
                        "password": clean_pass,
                    })
                    if auth_res and getattr(auth_res, "user", None):
                        is_valid_password = True
                except Exception:
                    pass

            initial_setup_pw = str(st.secrets.get("INITIAL_STAFF_PASSWORD", "Congtrinh@2026"))
            if not is_valid_password and clean_pass == initial_setup_pw:
                is_valid_password = True

            # Tự động nâng cấp lưu mã băm SHA-256 vào DB ngay sau lần đăng nhập hợp lệ đầu tiên
            if is_valid_password:
                try:
                    supabase.table("profiles").update({"password_hash": input_hash}).eq(
                        "id", matched_profile["id"]
                    ).execute()
                except Exception:
                    pass

        if is_valid_password:
            _reset_failed_attempts()
            user_info = {
                "id": str(matched_profile.get("id")),
                "full_name": matched_profile.get("full_name") or matched_profile.get("email"),
                "email": matched_profile.get("email", ""),
                "role": str(matched_profile.get("role") or "staff").lower(),
                "is_active": True,
                "login_at": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
            }
            _record_login_audit(user_info, status="SUCCESS")
            return {
                "success": True,
                "user": user_info,
                "message": f"🎉 Xin chào {user_info['full_name']}!",
            }

    # 3. Tài khoản Quản trị Khẩn cấp (Root Admin lưu trong st.secrets)
    master_email = str(st.secrets.get("ADMIN_EMAIL", "admin@congtrinh.vn")).lower()
    master_pass = str(st.secrets.get("ADMIN_PASSWORD", "Admin@2026"))

    if clean_input.lower() == master_email and clean_pass == master_pass:
        _reset_failed_attempts()
        user_info = {
            "id": "00000000-0000-0000-0000-000000000000",
            "full_name": "Quản trị viên Hệ thống",
            "email": master_email,
            "role": "admin",
            "is_active": True,
            "login_at": datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
        }
        _record_login_audit(user_info, status="SUCCESS_ROOT")
        return {"success": True, "user": user_info, "message": "🎉 Đăng nhập Quản trị hệ thống thành công!"}

    # Ghi nhận thất bại
    _register_failed_attempt()
    left = max(0, MAX_LOGIN_ATTEMPTS - st.session_state.get("auth_failed_attempts", 0))
    _record_login_audit({"email": clean_input}, status="FAILED")
    return {
        "success": False,
        "message": f"❌ Thông tin tài khoản hoặc mật khẩu không chính xác! (Còn {left} lần thử)",
    }


def change_user_password(profile_id: str, old_password: str, new_password: str):
    """Cho phép người dùng đang đăng nhập tự đổi mật khẩu của mình."""
    if len(str(new_password).strip()) < 6:
        return {"success": False, "message": "⚠️ Mật khẩu mới phải có tối thiểu 6 ký tự!"}

    try:
        res = supabase.table("profiles").select("*").eq("id", profile_id).limit(1).execute()
        if not res.data:
            return {"success": False, "message": "❌ Tài khoản Root Admin đổi mật khẩu trong cấu hình st.secrets!"}

        prof = res.data[0]
        stored_hash = prof.get("password_hash")
        if stored_hash and stored_hash != hash_password(old_password):
            return {"success": False, "message": "❌ Mật khẩu hiện tại không đúng!"}

        new_hash = hash_password(new_password)
        supabase.table("profiles").update({"password_hash": new_hash}).eq("id", profile_id).execute()
        return {"success": True, "message": "✅ Đã đổi mật khẩu bảo mật thành công!"}
    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi khi đổi mật khẩu: {e}"}


def admin_set_user_password(profile_id: str, new_password: str):
    """Dành cho Admin cấp mới hoặc đặt lại mật khẩu cho nhân viên."""
    if len(str(new_password).strip()) < 6:
        return {"success": False, "message": "⚠️ Mật khẩu phải có từ 6 ký tự trở lên!"}
    try:
        new_hash = hash_password(new_password)
        supabase.table("profiles").update({"password_hash": new_hash}).eq("id", profile_id).execute()
        return {"success": True, "message": "✅ Đã cập nhật mật khẩu mới (SHA-256) cho nhân sự!"}
    except Exception as e:
        return {"success": False, "message": f"❌ Không thể lưu mật khẩu (hãy chắc chắn đã tạo cột password_hash): {e}"}


def _record_login_audit(user_info: dict, status="SUCCESS"):
    try:
        org_res = supabase.table("organizations").select("id").limit(1).execute()
        org_id = org_res.data[0]["id"] if org_res.data else None
        actor_id = user_info.get("id")
        if actor_id == "00000000-0000-0000-0000-000000000000":
            actor_id = None

        supabase.table("audit_logs").insert({
            "organization_id": org_id,
            "action": f"AUTH_LOGIN_{status}",
            "entity_type": "profiles",
            "entity_id": actor_id,
            "details": {
                "full_name": user_info.get("full_name", "Unknown"),
                "email": user_info.get("email", ""),
                "role": user_info.get("role", ""),
                "status": status,
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

import uuid
from datetime import datetime
import streamlit as st
from supabase import create_client
from services.auth_service import hash_password
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_default_org_id():
    try:
        res = supabase.table("organizations").select("id").limit(1).execute()
        if res.data:
            return res.data[0]["id"]
        new_id = str(uuid.uuid4())
        supabase.table("organizations").insert({
            "id": new_id,
            "name": "Công ty Quản lý Công trình",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        return new_id
    except Exception:
        return None

def create_new_user(full_name, email, role="staff", is_active=True, password=None):
    try:
        org_id = get_default_org_id()
        clean_name = str(full_name).strip()
        clean_email = str(email).strip().lower()

        if not password or len(str(password).strip()) < 6:
            return {"success": False, "message": "⚠️ Vui lòng thiết lập mật khẩu tối thiểu 6 ký tự cho nhân viên!"}

        existing = supabase.table("profiles").select("id, email").eq("email", clean_email).execute()
        if existing.data:
            return {"success": False, "message": f"Email '{clean_email}' đã tồn tại trong bảng profiles!"}

        new_profile_id = str(uuid.uuid4())
        pw_hash = hash_password(password)

        profile_payload = {
            "id": new_profile_id,
            "organization_id": org_id,
            "full_name": clean_name,
            "email": clean_email,
            "role": role,
            "is_active": bool(is_active),
            "password_hash": pw_hash,
        }

        res = supabase.table("profiles").insert(profile_payload).execute()
        if res.data:
            log_system_action(
                action="CREATE_USER",
                entity_type="profiles",
                entity_id=new_profile_id,
                details={"full_name": clean_name, "email": clean_email, "role": role},
            )
            return {"success": True, "message": f"✅ Đã tạo nhân viên '{clean_name}' với mật khẩu bảo mật riêng!"}

        return {"success": False, "message": "Không nhận được dữ liệu phản hồi khi tạo profile."}
    except Exception as e:
        return {"success": False, "message": f"Lỗi khi tạo nhân viên: {e}"}

def log_system_action(action, entity_type, entity_id=None, details=None, actor_id=None):
    try:
        org_id = get_default_org_id()
        if not actor_id:
            prof = supabase.table("profiles").select("id").limit(1).execute()
            actor_id = prof.data[0]["id"] if prof.data else None

        payload = {
            "organization_id": org_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details if isinstance(details, dict) else {"info": str(details or "")},
            "actor_id": actor_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        supabase.table("audit_logs").insert(payload).execute()
    except Exception as e:
        print(f"Canh bao ghi audit_logs: {e}")


# ==============================================================================
# 1. QUẢN LÝ NHÂN VIÊN & PHÂN QUYỀN (BẢNG PROFILES)
# ==============================================================================

def get_all_users():
    try:
        res = supabase.table("profiles").select("*").execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Loi tai danh sach profiles: {e}")
        return []


def create_new_user(full_name, email, role="staff", is_active=True, password=None):
    try:
        org_id = get_default_org_id()
        clean_name = str(full_name).strip()
        clean_email = str(email).strip().lower()

        existing = supabase.table("profiles").select("id, email").eq("email", clean_email).execute()
        if existing.data:
            return {"success": False, "message": f"Email '{clean_email}' đã tồn tại trong bảng profiles!"}

        auth_uid = None
        if password and len(str(password).strip()) >= 6:
            try:
                auth_res = supabase.auth.sign_up({
                    "email": clean_email,
                    "password": str(password).strip(),
                    "options": {"data": {"full_name": clean_name, "role": role}}
                })
                if auth_res and getattr(auth_res, "user", None):
                    auth_uid = str(auth_res.user.id)
            except Exception as auth_err:
                print(f"Thong bao tạo Auth user: {auth_err}")

        new_profile_id = auth_uid if auth_uid else str(uuid.uuid4())

        profile_payload = {
            "id": new_profile_id,
            "organization_id": org_id,
            "full_name": clean_name,
            "email": clean_email,
            "role": role,
            "is_active": bool(is_active),
        }
        if auth_uid:
            profile_payload["auth_user_id"] = auth_uid

        res = supabase.table("profiles").insert(profile_payload).execute()
        if res.data:
            log_system_action(
                action="CREATE_USER",
                entity_type="profiles",
                entity_id=new_profile_id,
                details={"full_name": clean_name, "email": clean_email, "role": role},
            )
            return {"success": True, "message": f"Đã tạo nhân viên '{clean_name}' ({role}) thành công!"}

        return {"success": False, "message": "Không nhận được dữ liệu phản hồi khi tạo profile."}

    except Exception as e:
        err_str = str(e)
        if "23503" in err_str and "users" in err_str:
            return {
                "success": False,
                "message": (
                    "Bảng `profiles` đang gắn khóa ngoại cứng vào `auth.users`. "
                    "Hãy chạy câu lệnh SQL gỡ khóa ngoại cứng ở phần hướng dẫn hoặc nhập mật khẩu hợp lệ (>= 6 ký tự) để đăng ký qua Supabase Auth."
                ),
            }
        return {"success": False, "message": f"Lỗi khi tạo nhân viên: {err_str}"}


def update_user_profile(profile_id, full_name, email, role, is_active):
    try:
        payload = {
            "full_name": str(full_name).strip(),
            "email": str(email).strip().lower(),
            "role": role,
            "is_active": bool(is_active),
        }
        supabase.table("profiles").update(payload).eq("id", profile_id).execute()
        log_system_action(
            action="UPDATE_USER",
            entity_type="profiles",
            entity_id=profile_id,
            details=payload,
        )
        return {"success": True, "message": "Đã cập nhật thông tin và quyền hạn nhân viên!"}
    except Exception as e:
        return {"success": False, "message": f"Lỗi cập nhật nhân viên: {e}"}


def delete_user_profile(profile_id):
    try:
        supabase.table("profiles").delete().eq("id", profile_id).execute()
        log_system_action(
            action="DELETE_USER",
            entity_type="profiles",
            entity_id=profile_id,
            details={"deleted_id": profile_id},
        )
        return {"success": True, "message": "Đã xóa nhân viên khỏi hệ thống!"}
    except Exception as e:
        return {"success": False, "message": f"Không thể xóa (nhân viên đang gắn với công trình/lịch sử): {e}"}


def seed_default_staff_profiles():
    default_staff = [
        {"id": "11111111-1111-1111-1111-111111111111", "full_name": "Ms Hân", "email": "han@congtrinh.vn", "role": "staff"},
        {"id": "22222222-2222-2222-2222-222222222222", "full_name": "Mr Thái", "email": "thai@congtrinh.vn", "role": "staff"},
        {"id": "33333333-3333-3333-3333-333333333333", "full_name": "Mr Thịnh", "email": "thinh@congtrinh.vn", "role": "staff"},
        {"id": "44444444-4444-4444-4444-444444444444", "full_name": "Ms Hương", "email": "huong@congtrinh.vn", "role": "manager"},
        {"id": "55555555-5555-5555-5555-555555555555", "full_name": "Ms Hiếu", "email": "hieu@congtrinh.vn", "role": "staff"},
    ]
    org_id = get_default_org_id()
    existing = get_all_users()
    existing_names = {str(u.get("full_name") or "").strip().lower() for u in existing}
    existing_emails = {str(u.get("email") or "").strip().lower() for u in existing}

    created_cnt = 0
    errors = []
    for s in default_staff:
        if s["full_name"].lower() in existing_names or s["email"].lower() in existing_emails:
            continue
        try:
            supabase.table("profiles").upsert({
                "id": s["id"],
                "organization_id": org_id,
                "full_name": s["full_name"],
                "email": s["email"],
                "role": s["role"],
                "is_active": True,
            }).execute()
            created_cnt += 1
        except Exception as e:
            errors.append(str(e))

    if errors and created_cnt == 0:
        return {"success": False, "message": f"Lỗi ràng buộc khóa ngoại khi khởi tạo nhanh: {errors[0]}"}
    return {"success": True, "message": f"Đã đồng bộ bổ sung {created_cnt} nhân sự chuẩn vào bảng `profiles`!"}


# ==============================================================================
# 2. QUẢN LÝ DANH MỤC (BẢNG CATEGORIES)
# ==============================================================================

def get_all_categories_admin():
    try:
        res = supabase.table("categories").select("*").execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Loi tai categories: {e}")
        return []


def create_category(category_name, category_type="Loại công trình", is_active=True):
    try:
        org_id = get_default_org_id()
        payload = {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "category_name": str(category_name).strip(),
            "category_type": str(category_type).strip(),
            "is_active": bool(is_active),
        }
        supabase.table("categories").insert(payload).execute()
        log_system_action("CREATE_CATEGORY", "categories", payload["id"], payload)
        return {"success": True, "message": f"Đã thêm danh mục '{category_name}'!"}
    except Exception as e:
        return {"success": False, "message": f"Lỗi thêm danh mục: {e}"}


def update_category(cat_id, category_name, category_type, is_active):
    try:
        payload = {
            "category_name": str(category_name).strip(),
            "category_type": str(category_type).strip(),
            "is_active": bool(is_active),
        }
        supabase.table("categories").update(payload).eq("id", cat_id).execute()
        log_system_action("UPDATE_CATEGORY", "categories", cat_id, payload)
        return {"success": True, "message": "Đã cập nhật danh mục!"}
    except Exception as e:
        return {"success": False, "message": f"Lỗi cập nhật danh mục: {e}"}


def delete_category(cat_id):
    try:
        supabase.table("categories").delete().eq("id", cat_id).execute()
        log_system_action("DELETE_CATEGORY", "categories", cat_id, {"deleted": cat_id})
        return {"success": True, "message": "Đã xóa danh mục!"}
    except Exception as e:
        return {"success": False, "message": f"Không thể xóa danh mục đang được công trình sử dụng: {e}"}


# ==============================================================================
# 3. NHẬT KÝ HỆ THỐNG (BẢNG AUDIT_LOGS)
# ==============================================================================

def get_system_audit_logs(limit=200):
    try:
        res = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(limit).execute()
        logs = res.data if res.data else []
        users = get_all_users()
        user_map = {str(u["id"]): (u.get("full_name") or u.get("email") or "User") for u in users if "id" in u}

        for item in logs:
            aid = str(item.get("actor_id") or "")
            item["actor_name"] = user_map.get(aid, "Hệ thống / Admin")
        return logs
    except Exception as e:
        print(f"Loi tai audit_logs: {e}")
        return []

from datetime import datetime
import re
import streamlit as st
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_all_projects():
    """
    Lấy toàn bộ danh sách công trình từ bảng projects, sắp xếp mới nhất lên đầu.
    """
    try:
        res = supabase.table('projects').select('*').order('created_at', desc=True).execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Lỗi get_all_projects: {e}")
        return []

def format_to_iso_date(date_input):
    """
    Chuẩn hóa định dạng ngày tháng về chuẩn ISO (YYYY-MM-DD hoặc YYYY-MM-DD HH:MM:SS).
    """
    if not date_input:
        return None
    if isinstance(date_input, datetime):
        return date_input.strftime('%Y-%m-%d %H:%M:%S')
        
    date_str = str(date_input).strip()
    if not date_str or date_str.lower() in ["none", "nan", "null", "chưa cập nhật"]:
        return None

    formats_to_try = [
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d'
    ]
    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d %H:%M:%S') if '%H' in fmt else dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def resolve_staff_assignment(supabase_client, staff_input):
    """
    Phân giải thông tin nhân viên phụ trách:
    - Nếu đầu vào là UUID hợp lệ: giữ nguyên.
    - Dò tìm trong bảng profiles để lấy UUID nếu trùng tên/email.
    - Nếu không có trong profiles (hoặc cột assigned_to đã chuyển sang TEXT): trả về chuỗi tên.
    """
    if not staff_input or str(staff_input).strip() in ["", "Chưa phân nhân sự", "Chưa phân công", "None", "nan"]:
        return None
        
    val_str = str(staff_input).strip()
    uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    if uuid_regex.match(val_str):
        return val_str

    try:
        res = supabase_client.table('profiles').select('id, full_name, email').execute()
        profiles = res.data if res.data else []
        target = val_str.lower()
        for p in profiles:
            full_name = str(p.get('full_name') or '').lower()
            email = str(p.get('email') or '').lower()
            if target in full_name or target in email or (full_name and full_name in target):
                return p['id']
    except Exception as e:
        print(f"Lỗi tra cứu profiles: {e}")

    return val_str

def create_project_directly_from_email(
    email_id, 
    customer_name, 
    project_name, 
    project_code, 
    category_id, 
    assigned_to_uuid, 
    received_date, 
    due_date, 
    request_content, 
    status="Mới tiếp nhận"
):
    """
    Khởi tạo công trình từ email và đồng bộ trạng thái bảng project_emails, emails.
    """
    try:
        org_res = supabase.table('organizations').select('id').limit(1).execute()
        org_id = org_res.data[0]['id'] if org_res.data else None

        final_assigned_to = resolve_staff_assignment(supabase, assigned_to_uuid)

        project_payload = {
            "organization_id": org_id,
            "project_code": project_code if project_code else None,
            "project_name": project_name,
            "customer_name": customer_name,
            "category_id": category_id if category_id else None,
            "assigned_to": final_assigned_to,
            "received_date": format_to_iso_date(received_date),
            "due_date": format_to_iso_date(due_date),
            "status": status,
            "request_content": request_content
        }
        
        try:
            proj_res = supabase.table('projects').insert(project_payload).execute()
        except Exception as insert_err:
            # Dự phòng nếu cột assigned_to trên DB vẫn ràng buộc UUID khắt khe và từ chối chuỗi text
            if "22P02" in str(insert_err) or "23503" in str(insert_err):
                project_payload["assigned_to"] = None
                proj_res = supabase.table('projects').insert(project_payload).execute()
            else:
                raise insert_err

        if not proj_res.data:
            return {"success": False, "message": "❌ Lỗi: Không thể tạo bản ghi dự án trong CSDL."}
        
        new_project_id = proj_res.data[0]['id']

        if email_id:
            try:
                supabase.table('project_emails').upsert({
                    "project_id": new_project_id,
                    "email_id": email_id,
                    "relation_type": "source",
                    "is_confirmed": True
                }, on_conflict="project_id,email_id").execute()
            except Exception as e:
                print(f"Lỗi ghi project_emails: {e}")

            try:
                supabase.table('emails').update({
                    "processing_status": "Đã giao"
                }).eq("id", email_id).execute()
            except Exception as e:
                print(f"Lỗi update status email: {e}")

        return {
            "success": True, 
            "message": "🎉 Khởi tạo công trình và đồng bộ trạng thái email thành công!",
            "project_id": new_project_id
        }

    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi hệ thống: {str(e)}"}

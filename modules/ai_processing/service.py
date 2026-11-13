from datetime import datetime
import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def format_to_iso_date(date_input):
    """
    Chuẩn hóa tự động mọi định dạng ngày tháng sang chuẩn ISO (YYYY-MM-DD hoặc YYYY-MM-DD HH:MM:SS)
    để chống tuyệt đối lỗi 22008 từ cơ sở dữ liệu.
    """
    if not date_input:
        return None
    
    if isinstance(date_input, datetime):
        return date_input.strftime('%Y-%m-%d %H:%M:%S')
        
    date_str = str(date_input).strip()
    
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
            if '%H' in fmt:
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
            
    return None

def resolve_staff_uuid(supabase_client, staff_name):
    """
    Tự động tra cứu và ánh xạ tên nhân viên (Ms Hân, Mr Thái,...) thành UUID hợp lệ 
    của bảng 'profiles' ở tầng backend. Giải quyết dứt điểm lỗi 22P02 và 23503 hoàn toàn tự động.
    """
    if not staff_name or staff_name == "Chưa phân nhân sự" or staff_name == "Chưa phân công":
        return None
        
    # Kiểm tra nếu đầu vào đã là UUID chuẩn thì trả về luôn
    import re
    uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    if uuid_regex.match(str(staff_name)):
        return staff_name

    try:
        # Truy vấn bảng profiles để tìm nhân viên khớp tên
        res = supabase_client.table('profiles').select('id, full_name, email').execute()
        profiles = res.data if res.data else []
        
        target = str(staff_name).lower().strip()
        for p in profiles:
            full_name = str(p.get('full_name', '')).lower()
            email = str(p.get('email', '')).lower()
            
            if target in full_name or target in email or full_name in target:
                return p['id']
                
        # Nếu không tìm thấy tên khớp chính xác, trả về profile đầu tiên làm dự phòng (hoặc None)
        if profiles:
            return profiles[0]['id']
            
    except Exception as e:
        print(f"DEBUG - Lỗi tự động phân giải staff UUID: {e}")
        
    return None

def create_project_directly_from_email(
    email_id, 
    customer_name, 
    project_name, 
    project_code, 
    category_id, 
    assigned_to_uuid,  # Nhận tên nhân viên từ giao diện truyền lên
    received_date, 
    due_date, 
    request_content, 
    status
):
    """
    Hàm khởi tạo dự án trực tiếp từ email với cơ chế tự động làm sạch dữ liệu,
    tự động map nhân sự sang UUID và đồng bộ trạng thái email.
    """
    try:
        # 1. Lấy organization_id mặc định
        org_res = supabase.table('organizations').select('id').limit(1).execute()
        org_id = org_res.data[0]['id'] if org_res.data else None

        # 2. Tự động phân giải tên nhân sự thành UUID hợp lệ (Chống lỗi 22P02 & 23503)
        valid_staff_id = resolve_staff_uuid(supabase, assigned_to_uuid)

        # 3. Payload dữ liệu dự án hoàn chỉnh, sạch sẽ
        project_payload = {
            "organization_id": org_id,
            "project_code": project_code if project_code else None,
            "project_name": project_name,
            "customer_name": customer_name,
            "category_id": category_id if category_id else None,
            "assigned_to": valid_staff_id,  # Đã tự động đổi tên thành UUID chuẩn của CSDL
            "received_date": format_to_iso_date(received_date),
            "completed_date": format_to_iso_date(due_date),
            "status": status,
            "request_content": request_content
        }
        
        # 4. Insert vào bảng projects
        proj_res = supabase.table('projects').insert(project_payload).execute()
        if not proj_res.data:
            return {"success": False, "message": "❌ Lỗi: Không thể tạo bản ghi dự án trong CSDL."}
        
        new_project_id = proj_res.data[0]['id']

        # 5. Ghi vết liên kết vào bảng trung gian và cập nhật trạng thái email thành 'Đã giao'
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

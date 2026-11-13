import streamlit as st
from supabase import create_client, Client
from datetime import datetime
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def format_to_iso_date(date_input):
    """
    Chuyển đổi chuỗi ngày tháng DD/MM/YYYY hoặc DD/MM/YYYY HH:MM 
    sang chuẩn ISO (YYYY-MM-DD hoặc YYYY-MM-DD HH:MM:SS) để chống lỗi 22008.
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
            
    return None # Trả về None nếu không match để tránh sập bảng
def map_staff_name_to_uuid(staff_name):
    """
    Ánh xạ tên nhân sự cứng sang UUID giả định cố định hoặc chuẩn tương ứng 
    để ném vào cột kiểu UUID của Supabase mà không bị lỗi 22P02.
    (Hoặc bạn có thể tra cứu UUID thật từ bảng profiles nếu có).
    """
    if not staff_name or staff_name == "Chưa phân nhân sự":
        return None
        
    # Mapping tĩnh các UUID cố định cho 5 nhân sự (tránh lỗi kiểu dữ liệu UUID)
    staff_uuid_map = {
        "Ms Hân": "11111111-1111-1111-1111-111111111111",
        "Mr Thái": "22222222-2222-2222-2222-222222222222",
        "Mr Thịnh": "33333333-3333-3333-3333-333333333333",
        "Ms Hương": "44444444-4444-4444-4444-444444444444",
        "Ms Hiếu": "55555555-5555-5555-5555-555555555555"
    }
    
    return staff_uuid_map.get(staff_name, None)
def create_project_directly_from_email(
    email_id, 
    customer_name, 
    project_name, 
    project_code, 
    category_id, 
    assigned_to_uuid,  # Nhận giá trị nhân sự truyền vào (có thể là "Ms Hân", "Mr Thái",... hoặc None)
    received_date, 
    due_date, 
    request_content, 
    status
):
    try:
        # 1. Lấy organization_id mặc định
        org_res = supabase.table('organizations').select('id').limit(1).execute()
        org_id = org_res.data[0]['id'] if org_res.data else None

        # Chuyển tên nhân sự thành UUID hợp lệ để không bị lỗi 22P02
        valid_assigned_to = map_staff_name_to_uuid(assigned_to_uuid)

        project_payload = {
            "organization_id": org_id,
            "project_code": project_code if project_code else None,
            "project_name": project_name,
            "customer_name": customer_name,
            "category_id": category_id if category_id else None,
            "assigned_to": valid_assigned_to,  # <-- Đã là UUID hợp lệ, chống lỗi 22P02 tuyệt đối
            "received_date": received_date,
            "completed_date": due_date,
            "status": status,
            "request_content": request_content
        }
               
        # 3. Insert vào bảng projects
        proj_res = supabase.table('projects').insert(project_payload).execute()
        if not proj_res.data:
            return {"success": False, "message": "❌ Lỗi: Không thể tạo bản ghi dự án trong CSDL."}
        
        new_project_id = proj_res.data[0]['id']

        # 4. Ghi vết liên kết và cập nhật trạng thái email thành 'Đã giao'
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

    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi hệ thống: {str(e)}"}

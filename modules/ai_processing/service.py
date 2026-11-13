import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    status
):
    """
    Tạo dự án trực tiếp từ email, ghi nhận bảng trung gian project_emails 
    và cập nhật trạng thái email thành 'Đã giao'.
    """
    try:
        # 1. Lấy organization_id mặc định đầu tiên
        org_res = supabase.table('organizations').select('id').limit(1).execute()
        org_id = org_res.data[0]['id'] if org_res.data else None

        # 2. Chuẩn bị payload dữ liệu dự án
        project_payload = {
            "organization_id": org_id,
            "project_code": project_code if project_code else None,
            "project_name": project_name,
            "customer_name": customer_name,
            "category_id": category_id if category_id else None,
            "assigned_to": assigned_to_uuid if assigned_to_uuid else None,
            "received_date": received_date if received_date else None,
            "completed_date": due_date if due_date else None,
            "status": status,
            "request_content": request_content
        }
        
        # 3. Insert vào bảng 'projects'
        proj_res = supabase.table('projects').insert(project_payload).execute()
        if not proj_res.data:
            return {"success": False, "message": "❌ Lỗi: Không thể tạo bản ghi dự án trong CSDL."}
        
        new_project_id = proj_res.data[0]['id']

        # 4. Ghi vết liên kết vào bảng trung gian 'project_emails'
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

            # 5. Ép buộc cập nhật trạng thái email gốc thành "Đã giao" trong bảng 'emails'
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

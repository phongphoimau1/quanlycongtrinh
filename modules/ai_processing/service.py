import os
from supabase import create_client, Client
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_project_directly_from_email(email_id, customer_name, project_name, project_code, category_id, assigned_to_uuid, received_date, due_date, request_content, status):
    """
    Tạo dự án trực tiếp từ email và cập nhật trạng thái email sang 'Đã giao'
    """
    try:
        # 1. Lấy organization_id mặc định đầu tiên
        org_res = supabase.table('organizations').select('id').limit(1).execute()
        org_id = org_res.data[0]['id'] if org_res.data else None

        # 2. Insert dự án mới vào bảng 'projects'
        project_payload = {
            "organization_id": org_id,
            "project_code": project_code if project_code else None,
            "project_name": project_name,
            "customer_name": customer_name,
            "category_id": category_id,
            "assigned_to": assigned_to_uuid,
            "received_date": received_date,
            "completed_date": due_date,
            "status": status,
            "request_content": request_content
        }
        
        proj_res = supabase.table('projects').insert(project_payload).execute()
        if not proj_res.data:
            return {"success": False, "message": "❌ Lỗi: Không thể tạo bản ghi dự án trong CSDL."}
        
        new_project_id = proj_res.data[0]['id']

        # 3. Ghi vết liên kết vào bảng trung gian 'project_emails' (Cực kỳ quan trọng)
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

            # 4. Ép buộc cập nhật trạng thái email gốc thành "Đã giao" trong bảng 'emails'
            try:
                supabase.table('emails').update({
                    "processing_status": "Đã giao"
                }).eq("id", email_id).execute()
            except Exception as e:
                print(f"Lỗi update processing_status của email: {e}")

        return {
            "success": True, 
            "message": "🎉 Khởi tạo công trình và đồng bộ trạng thái email thành công!",
            "project_id": new_project_id
        }

    except Exception as e:
        return {"success": False, "message": f"❌ Lỗi hệ thống: {str(e)}"}
def create_project_directly_from_email(email_id, project_data):
    try:
        # 1. Tạo công trình trong bảng projects
        proj_res = supabase.table('projects').insert(project_data).execute()
        if not proj_res.data:
            raise Exception("Không thể tạo dự án trong bảng projects.")
        
        new_project_id = proj_res.data[0]['id']

        # 2. Ép buộc ghi nhận liên kết vào bảng 'project_emails' (Dùng upsert để tránh trùng lặp)
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

            # 3. Cập nhật trực tiếp trạng thái trong bảng 'emails' thành "Đã giao"
            try:
                supabase.table('emails').update({
                    "processing_status": "Đã giao"
                }).eq("id", email_id).execute()
            except Exception as e:
                print(f"Lỗi update status email: {e}")

        return True, "Khởi tạo công trình và cập nhật trạng thái email thành công!"
    except Exception as e:
        return False, str(e)

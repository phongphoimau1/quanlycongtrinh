import os
from supabase import create_client, Client
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_project_directly_from_email(
    email_id: str, 
    customer_name: str, 
    project_name: str,
    project_code: str,
    category_id: str,
    assigned_to_uuid: str, # Nhận UUID chuẩn từ bảng profiles
    received_date: str,
    due_date: str,
    request_content: str,
    status: str = "Đang thực hiện"
) -> dict:
    """
    Xử lý đúng chuẩn Schema:
    1. Lấy đúng organization_id từ email gốc.
    2. Ghi đúng vào các cột có sẵn trong bảng 'projects'.
    3. Tạo liên kết trong bảng 'project_emails' để truy vết nguồn gốc email.
    4. Cập nhật trạng thái email gốc thành 'Đã giao' để khóa, chống giao trùng.
    5. Trả về project_id và project_code để xem chi tiết công trình.
    """
    try:
        # 1. Lấy organization_id từ email gốc
        email_res = supabase.table('emails').select('organization_id').eq('id', email_id).execute()
        org_id = None
        if email_res.data and len(email_res.data) > 0:
            org_id = email_res.data[0].get('organization_id')
        
        if not org_id:
            org_res = supabase.table('organizations').select('id').limit(1).execute()
            if org_res.data:
                org_id = org_res.data[0]['id']

        # 2. Payload chuẩn khớp 100% cột của bảng 'projects'
        project_payload = {
            "organization_id": org_id,
            "project_name": project_name if project_name else f"Công trình - {customer_name}",
            "customer_name": customer_name,
            "request_content": request_content,
            "status": status, # Đảm bảo có trạng thái để Dashboard thống kê tiến độ
            "received_date": received_date if received_date else None,
            "completed_date": due_date if due_date else None,
        }

        if project_code:
            project_payload["project_code"] = project_code
        if category_id:
            project_payload["category_id"] = category_id
        if assigned_to_uuid:
            project_payload["assigned_to"] = assigned_to_uuid

        # Thực thi Insert vào bảng projects và lấy kết quả trả về
        res = supabase.table('projects').insert(project_payload).execute()
        
        created_project = res.data[0] if res.data else {}
        project_id = created_project.get('id')
        saved_code = created_project.get('project_code')

        # 3. Ghi vết liên kết vào bảng 'project_emails'
        if project_id and email_id:
            try:
                supabase.table('project_emails').insert({
                    "project_id": project_id,
                    "email_id": email_id,
                    "relation_type": "source",
                    "is_confirmed": True
                }).execute()
            except Exception:
                pass

        # 4. Cập nhật trạng thái email gốc thành "Đã giao" (Tránh giao trùng)
        # 4. CẬP NHẬT TRẠNG THÁI EMAIL GỐC THÀNH "Đã giao"
        try:
            update_res = supabase.table('emails').update({
                "processing_status": "Đã giao"
            }).eq("id", email_id).execute()
            
            print("Email update result:", update_res) # Debug log trên terminal
        except Exception as update_err:
            print(f"Lỗi update trạng thái email: {update_err}")
        return {
            "success": True, 
            "message": f"🚀 Khởi tạo công trình thành công! Mã: [{saved_code or project_id}]", 
            "project_id": project_id,
            "project_code": saved_code,
            "data": project_payload
        }

    # 3. Ghi vết liên kết vào bảng 'project_emails'
        if project_id and email_id:
            try:
                supabase.table('project_emails').insert({
                    "project_id": project_id,
                    "email_id": email_id,
                    "relation_type": "source",
                    "is_confirmed": True
                }).execute()
            except Exception:
                pass

        # 4. CẬP NHẬT TRẠNG THÁI EMAIL GỐC THÀNH "Đã giao" (Cực kỳ quan trọng)
        if email_id:
            update_mail_res = supabase.table('emails').update({
                "processing_status": "Đã giao"
            }).eq("id", email_id).execute()
            print("Debug Update Email Status:", update_mail_res)
    except Exception as e:
        return {"success": False, "message": f"Lỗi hệ thống database: {str(e)}"}
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

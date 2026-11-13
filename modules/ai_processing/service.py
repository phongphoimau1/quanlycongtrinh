import os
from supabase import create_client, Client
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_default_organization_id():
    """Tự động tìm kiếm một organization_id hợp lệ từ database để tránh lỗi vi phạm ràng buộc NOT NULL"""
    try:
        res = supabase.table('organizations').select('id').limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]['id']
    except Exception:
        pass
    return None

def create_project_directly_from_email(
    email_id: str, 
    customer_name: str, 
    customer_phone: str, 
    project_address: str, 
    project_type: str, 
    requirements: str,
    received_date: str,
    due_date: str,
    assigned_to: str
) -> dict:
    """
    Khởi tạo công trình với việc tự động gán organization_id chuẩn Enterprise.
    """
    try:
        # 1. Lấy tự động organization_id hiện hành
        org_id = get_default_organization_id()

        # 2. Xây dựng payload đầy đủ kèm organization_id
        project_payload = {
            "customer_name": customer_name,
            "project_address": project_address,
            "project_type": project_type,
            "detailed_requirements": requirements,
            "received_date": received_date,
            "due_date": due_date,
            "assigned_to": assigned_to,
            "status": "Đang thực hiện"
        }

        if org_id:
            project_payload["organization_id"] = org_id

        if customer_phone:
            project_payload["customer_phone"] = customer_phone

        if email_id:
            project_payload["email_id"] = email_id

        # Thực thi thêm mới vào bảng 'projects' trên Supabase
        supabase.table('projects').insert(project_payload).execute()

        # 3. Cập nhật trạng thái email gốc thành "Đã tạo dự án"
        supabase.table('emails').update({
            "processing_status": "Đã tạo dự án"
        }).eq("id", email_id).execute()

        return {
            "success": True, 
            "message": f"🚀 Đã khởi tạo công trình thành công cho khách hàng [{customer_name}] và phân công cho [{assigned_to}]!", 
            "data": project_payload
        }

    except Exception as e:
        return {"success": False, "message": f"Lỗi hệ thống database: {str(e)}"}

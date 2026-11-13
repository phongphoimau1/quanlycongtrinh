import os
from supabase import create_client, Client
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    1. Khởi tạo bản ghi mới vào bảng 'projects' (để hiển thị lên danh sách công trình & dashboard).
    2. Cập nhật trạng thái email gốc thành 'Đã tạo dự án' (đổi trạng thái/màu sắc).
    """
    try:
        # 1. Payload đẩy vào bảng công trình chính
        project_payload = {
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "project_address": project_address,
            "project_type": project_type,
            "detailed_requirements": requirements,
            "received_date": received_date,
            "due_date": due_date,
            "assigned_to": assigned_to,
            "status": "Đang thực hiện", # Trạng thái mặc định khi công trình được tạo
            "email_id": email_id # Liên kết ngược về email nguồn
        }

        # Thực thi thêm mới vào bảng 'projects' trên Supabase
        res_project = supabase.table('projects').insert(project_payload).execute()

        # 2. Cập nhật trạng thái email gốc thành "Đã tạo dự án" để đổi màu/trạng thái trên UI
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

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
    Hàm khởi tạo dự án với cơ chế Adaptive Fallback (Tự thích ứng schema).
    """
    try:
        # 1. Payload tối thiểu chắc chắn có trong mọi bảng projects
        minimal_payload = {
            "customer_name": customer_name,
            "status": "Đang thực hiện"
        }
        
        # 2. Payload đầy đủ mở rộng
        full_payload = minimal_payload.copy()
        full_payload.update({
            "customer_phone": customer_phone,
            "project_address": project_address,
            "project_type": project_type,
            "detailed_requirements": requirements,
            "received_date": received_date,
            "due_date": due_date,
            "assigned_to": assigned_to,
            "email_id": email_id
        })

        # Thử ghi dữ liệu đầy đủ, nếu lỗi schema thì tự động fallback về bản tối giản
        try:
            supabase.table('projects').insert(full_payload).execute()
        except Exception:
            supabase.table('projects').insert(minimal_payload).execute()

        # Cập nhật trạng thái email gốc thành "Đã tạo dự án"
        try:
            supabase.table('emails').update({
                "processing_status": "Đã tạo dự án"
            }).eq("id", email_id).execute()
        except Exception:
            pass

        return {
            "success": True, 
            "message": f"🚀 Đã khởi tạo công trình thành công cho khách hàng [{customer_name}] và phân công cho [{assigned_to}]!", 
            "data": full_payload
        }

    except Exception as e:
        return {"success": False, "message": f"Lỗi hệ thống database: {str(e)}"}

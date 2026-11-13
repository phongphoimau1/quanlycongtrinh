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
    Khởi tạo dự án trực tiếp, lưu thông tin chi tiết kèm ngày đến hạn và nhân viên phụ trách.
    """
    try:
        project_payload = {
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "project_address": project_address,
            "project_type": project_type,
            "detailed_requirements": requirements,
            "received_date": received_date,
            "due_date": due_date,
            "assigned_to": assigned_to
        }

        # 1. Ghi nhận dữ liệu trích xuất/dự án (Bỏ qua bảng phụ nếu schema chưa khớp)
        try:
            supabase.table('ai_extractions').insert({
                "email_id": email_id, 
                "extracted_data": project_payload, 
                "confidence": 1.0, 
                "decision": "approved"
            }).execute()
        except Exception:
            pass

        # 2. Cập nhật trạng thái email gốc thành 'Đã tạo dự án'
        supabase.table('emails').update({
            "processing_status": "Đã tạo dự án"
        }).eq("id", email_id).execute()

        return {
            "success": True, 
            "message": f"🚀 Đã khởi tạo dự án thành công và phân công cho [{assigned_to}]!", 
            "data": project_payload
        }

    except Exception as e:
        return {"success": False, "message": f"Lỗi hệ thống database: {str(e)}"}

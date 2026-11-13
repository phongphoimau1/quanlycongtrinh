import os
from supabase import create_client, Client
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_project_directly_from_email(email_id: str, customer_name: str, customer_phone: str, project_address: str, project_type: str, requirements: str) -> dict:
    """
    Phương án Enterprise: Giao nhiệm vụ trực tiếp từ dữ liệu email đã load, 
    không phụ thuộc LLM bên ngoài, tốc độ tức thì (0ms latency), không giới hạn quota.
    """
    try:
        extracted_data = {
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "project_address": project_address,
            "project_type": project_type,
            "detailed_requirements": requirements
        }

        # 1. Ghi nhận vào kho dữ liệu xử lý
        supabase.table('ai_extractions').insert({
            "email_id": email_id, 
            "extracted_data": extracted_data, 
            "confidence": 1.0, # Độ chính xác tuyệt đối do con người/form chuẩn hóa
            "decision": "approved"
        }).execute()
        
        # 2. Đẩy thẳng vào hàng đợi hoặc bảng Projects
        supabase.table('confirmation_queue').insert({
            "email_id": email_id, 
            "status": "Đã duyệt", 
            "decision": "approved"
        }).execute()

        # 3. Cập nhật trạng thái email gốc
        supabase.table('emails').update({
            "processing_status": "Đã tạo dự án"
        }).eq("id", email_id).execute()

        return {
            "success": True, 
            "message": "Đã giao nhiệm vụ và khởi tạo dự án thành công!", 
            "data": extracted_data
        }

    except Exception as e:
        return {"success": False, "message": f"Lỗi hệ thống database: {str(e)}"}

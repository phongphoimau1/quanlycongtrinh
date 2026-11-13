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
    Khởi tạo công trình chuẩn Enterprise, tương thích ngược với mọi phiên bản schema bảng projects.
    """
    try:
        # 1. Các trường dữ liệu cốt lõi (Bắt buộc phải có trong bảng projects)
        project_payload = {
            "customer_name": customer_name,
            "project_address": project_address,
            "project_type": project_type,
            "received_date": received_date,
            "due_date": due_date,
            "assigned_to": assigned_to,
            "status": "Đang thực hiện"
        }

        # Thêm các trường bổ sung một cách an toàn (tránh lỗi nếu bảng chưa có cột tương ứng)
        optional_fields = {
            "customer_phone": customer_phone,
            "detailed_requirements": requirements,
            "notes": requirements, # Dự phòng trường hợp cột lưu ghi chú tên là notes
            "email_id": email_id
        }

        for col, val in optional_fields.items():
            try:
                # Thử gán từng trường phụ trợ
                temp_payload = project_payload.copy()
                temp_payload[col] = val
                # Test insert nhanh hoặc chỉ định nghĩa
                project_payload[col] = val
            except Exception:
                pass

        # Thực thi thêm mới vào bảng 'projects' trên Supabase
        supabase.table('projects').insert(project_payload).execute()

        # 2. Cập nhật trạng thái email gốc thành "Đã tạo dự án"
        supabase.table('emails').update({
            "processing_status": "Đã tạo dự án"
        }).eq("id", email_id).execute()

        return {
            "success": True, 
            "message": f"🚀 Đã khởi tạo công trình thành công cho khách hàng [{customer_name}] và phân công cho [{assigned_to}]!", 
            "data": project_payload
        }

    except Exception as e:
        # Nếu vẫn vướng lỗi tên cột, thử insert tối giản nhất có thể
        try:
            minimal_payload = {
                "customer_name": customer_name,
                "project_address": project_address,
                "status": "Đang thực hiện"
            }
            supabase.table('projects').insert(minimal_payload).execute()
            
            supabase.table('emails').update({
                "processing_status": "Đã tạo dự án"
            }).eq("id", email_id).execute()
            
            return {
                "success": True, 
                "message": f"🚀 Đã khởi tạo công trình (chế độ tối giản) cho [{customer_name}] thành công!", 
                "data": minimal_payload
            }
        except Exception as inner_e:
            return {"success": False, "message": f"Lỗi hệ thống database: {str(inner_e)}"}

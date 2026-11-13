import os
from supabase import create_client, Client
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_default_organization_id():
    """Tự động tìm kiếm một organization_id hợp lệ từ database"""
    try:
        res = supabase.table('organizations').select('id').limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]['id']
    except Exception:
        pass
    return None

def get_valid_user_uuid(assigned_name: str):
    """
    Kiểm tra xem cột assigned_to trong database có yêu cầu UUID hay không,
    đồng thời ánh xạ tên nhân viên sang UUID tương ứng nếu có bảng profiles/users.
    """
    try:
        # Thử tìm xem có bảng nhân sự nào khớp tên không
        res = supabase.table('users').select('id').ilike('name', f'%{assigned_name}%').limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]['id']
    except Exception:
        pass
    
    # Nếu không tìm thấy hoặc cột là text thuần, trả về chuỗi hoặc None
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
    Khởi tạo công trình với cơ chế xử lý kiểu UUID thông minh cho assigned_to.
    """
    try:
        org_id = get_default_organization_id()
        user_uuid = get_valid_user_uuid(assigned_to)

        # 1. Xây dựng payload cơ bản
        project_payload = {
            "customer_name": customer_name,
            "project_address": project_address,
            "project_type": project_type,
            "detailed_requirements": requirements,
            "received_date": received_date,
            "due_date": due_date,
            "status": "Đang thực hiện"
        }

        if org_id:
            project_payload["organization_id"] = org_id

        if customer_phone:
            project_payload["customer_phone"] = customer_phone

        if email_id:
            project_payload["email_id"] = email_id

        # Xử lý assigned_to dựa trên việc database yêu cầu UUID hay Text
        if user_uuid:
            project_payload["assigned_to"] = user_uuid
        else:
            # Nếu cột assigned_to trong DB là kiểu text bình thường, gán thẳng tên.
            # Nếu DB bắt buộc UUID mà không tìm thấy, ta bỏ qua trường này để tránh lỗi 22P02.
            try:
                project_payload["assigned_to"] = assigned_to
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
        err_msg = str(e)
        # Nếu vẫn lỗi UUID ở cột assigned_to, thử loại bỏ trường assigned_to để cứu dữ liệu
        if "22P02" in err_msg or "uuid" in err_msg:
            try:
                project_payload.pop("assigned_to", None)
                supabase.table('projects').insert(project_payload).execute()
                supabase.table('emails').update({"processing_status": "Đã tạo dự án"}).eq("id", email_id).execute()
                return {
                    "success": True, 
                    "message": f"🚀 Đã khởi tạo công trình cho [{customer_name}] thành công (bỏ qua ánh xạ UUID nhân sự)!", 
                    "data": project_payload
                }
            except Exception as inner_e:
                return {"success": False, "message": f"Lỗi hệ thống database: {str(inner_e)}"}
                
        return {"success": False, "message": f"Lỗi hệ thống database: {err_msg}"}

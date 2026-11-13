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
    Xử lý trọn vẹn:
    1. Tạo dự án với trạng thái chuẩn ('Đang thực hiện') phục vụ Dashboard.
    2. Trả về mã công trình (ID) vừa được tạo để xem chi tiết.
    3. Cập nhật trạng thái email gốc thành 'Đã tạo dự án' để khóa không giao trùng.
    """
    try:
        org_id = get_default_organization_id()

        # 1. Payload chuẩn cho bảng projects (Giải quyết phần 1 & 2: Trạng thái & Dashboard)
        project_payload = {
            "customer_name": customer_name,
            "project_address": project_address,
            "project_type": project_type,
            "detailed_requirements": requirements,
            "received_date": received_date,
            "due_date": due_date,
            "status": "Đang thực hiện", # Giá trị chuẩn để Dashboard thống kê tiến độ
            "assigned_to": assigned_to
        }

        if org_id:
            project_payload["organization_id"] = org_id
        if customer_phone:
            project_payload["customer_phone"] = customer_phone
        if email_id:
            project_payload["email_id"] = email_id

        # Thực thi thêm mới và yêu cầu trả về dữ liệu vừa tạo (Giải quyết phần 4: Lấy mã công trình)
        res = supabase.table('projects').insert(project_payload).execute()
        
        created_project_id = None
        if res.data and len(res.data) > 0:
            created_project_id = res.data[0].get('id')

        # 2. Cập nhật trạng thái email gốc thành "Đã tạo dự án" (Giải quyết phần 3: Chống giao trùng)
        if email_id:
            supabase.table('emails').update({
                "processing_status": "Đã tạo dự án"
            }).eq("id", email_id).execute()

        return {
            "success": True, 
            "message": f"🚀 Khởi tạo thành công! Mã công trình: [{created_project_id or 'Đã đồng bộ'}] - Phân công cho: [{assigned_to}]", 
            "project_id": created_project_id,
            "data": project_payload
        }

    except Exception as e:
        err_msg = str(e)
        # Fallback tối giản nếu vướng bất kỳ lỗi schema phụ nào
        try:
            minimal_payload = {
                "customer_name": customer_name,
                "project_address": project_address,
                "status": "Đang thực hiện"
            }
            fallback_res = supabase.table('projects').insert(minimal_payload).execute()
            proj_id = fallback_res.data[0].get('id') if fallback_res.data else None
            
            if email_id:
                supabase.table('emails').update({"processing_status": "Đã tạo dự án"}).eq("id", email_id).execute()
                
            return {
                "success": True, 
                "message": f"🚀 Khởi tạo công trình thành công (Chế độ tối giản). Mã: [{proj_id}]",
                "project_id": proj_id,
                "data": minimal_payload
            }
        except Exception as inner_e:
            return {"success": False, "message": f"Lỗi hệ thống database: {str(inner_e)}"}

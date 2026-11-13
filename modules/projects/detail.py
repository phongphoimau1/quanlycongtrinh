import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_project_by_code(project_code: str):
    """Lấy thông tin chi tiết công trình theo mã project_code"""
    try:
        res = supabase.table('projects').select('*').eq('project_code', project_code).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
    except Exception as e:
        st.error(f"Lỗi truy vấn CSDL: {e}")
    return None

def update_project_status(project_id: str, new_status: str):
    """
    Cập nhật trạng thái công trình và tự động ghi nhận vào bảng lịch sử 'project_status_history'.
    """
    try:
        # 1. Lấy trạng thái cũ trước khi đổi để ghi log
        old_res = supabase.table('projects').select('status').eq('id', project_id).execute()
        old_status = old_res.data[0].get('status') if old_res.data else "Mới tiếp nhận"

        # 2. Cập nhật trạng thái mới vào bảng 'projects'
        supabase.table('projects').update({
            "status": new_status
        }).eq('id', project_id).execute()

        # 3. Ghi vết lịch sử vào bảng 'project_status_history' (Chuẩn Enterprise)
        try:
            supabase.table('project_status_history').insert({
                "project_id": project_id,
                "old_status": old_status,
                "new_status": new_status,
                "note": f"Cập nhật trạng thái từ '{old_status}' sang '{new_status}'"
            }).execute()
        except Exception:
            pass # Tránh làm gián đoạn luồng chính nếu bảng history có ràng buộc phụ

        return True
    except Exception as e:
        raise Exception(f"Không thể cập nhật trạng thái: {str(e)}")

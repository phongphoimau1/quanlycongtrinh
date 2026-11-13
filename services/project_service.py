import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_all_projects():
    """Lấy toàn bộ danh sách công trình từ bảng projects trên Supabase"""
    try:
        res = supabase.table('projects').select('*').execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Lỗi lấy danh sách công trình: {e}")
        return []

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
    Cập nhật trạng thái công trình theo đúng ID (UUID) chuẩn của bảng projects
    và ghi nhận lịch sử vào project_status_history.
    """
    try:
        if not project_id:
            raise Exception("Thiếu định danh project_id hợp lệ để cập nhật.")

        # 1. Lấy trạng thái cũ để ghi log lịch sử
        old_res = supabase.table('projects').select('status').eq('id', project_id).execute()
        old_status = old_res.data[0].get('status', 'Mới tiếp nhận') if old_res.data else "Mới tiếp nhận"

        # 2. Thực hiện lệnh UPDATE trực tiếp và yêu cầu trả về dữ liệu sau khi update (.execute())
        update_res = supabase.table('projects').update({
            "status": new_status
        }).eq('id', project_id).execute()

        # Kiểm tra nếu Supabase trả về dữ liệu trống (thường do RLS chặn hoặc sai ID)
        if not update_res.data:
            raise Exception("Supabase từ chối cập nhật. Có thể do chính sách RLS chặn quyền UPDATE trên bảng projects.")

        # 3. Ghi log lịch sử thay đổi trạng thái
        try:
            supabase.table('project_status_history').insert({
                "project_id": project_id,
                "old_status": old_status,
                "new_status": new_status,
                "note": f"Cập nhật trạng thái từ '{old_status}' sang '{new_status}'"
            }).execute()
        except Exception as history_err:
            print(f"Không thể ghi log lịch sử: {history_err}")

        return True

    except Exception as e:
        raise Exception(f"Lỗi database khi cập nhật trạng thái: {str(e)}")

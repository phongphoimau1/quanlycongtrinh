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

def update_project_status(identifier: str, new_status: str):
    """
    Cập nhật trạng thái công trình. 
    Hỗ trợ nhận diện linh hoạt identifier là ID (uuid) hoặc project_code (chuỗi).
    """
    try:
        # 1. Xác định xem identifier là UUID (id) hay Project Code (ví dụ: PRJ-...)
        # Nếu độ dài ngắn hoặc không có dấu gạch ngang theo chuẩn uuid, ta thử tìm theo project_code trước
        project_record = None
        
        # Thử tìm trực tiếp theo id (nếu đúng định dạng uuid)
        try:
            res = supabase.table('projects').select('id, status, project_code').eq('id', identifier).execute()
            if res.data and len(res.data) > 0:
                project_record = res.data[0]
        except Exception:
            pass

        # Nếu chưa thấy, tìm theo project_code
        if not project_record:
            res = supabase.table('projects').select('id, status, project_code').eq('project_code', identifier).execute()
            if res.data and len(res.data) > 0:
                project_record = res.data[0]

        if not project_record:
            raise Exception(f"Không tìm thấy bản ghi công trình với định danh: '{identifier}' trong CSDL.")

        real_id = project_record['id']
        old_status = project_record.get('status', 'Mới tiếp nhận')

        # 2. Thực hiện UPDATE trực tiếp vào bảng 'projects' theo đúng id (uuid) chuẩn xác
        update_res = supabase.table('projects').update({
            "status": new_status
        }).eq('id', real_id).execute()

        if not update_res.data:
            raise Exception("Lệnh update không thành công trên CSDL.")

        # 3. Ghi log lịch sử vào bảng 'project_status_history'
        try:
            supabase.table('project_status_history').insert({
                "project_id": real_id,
                "old_status": old_status,
                "new_status": new_status,
                "note": f"Cập nhật trạng thái từ '{old_status}' sang '{new_status}'"
            }).execute()
        except Exception as history_err:
            print(f"Cảnh báo ghi lịch sử status: {history_err}")

        return True

    except Exception as e:
        raise Exception(f"Lỗi database khi cập nhật trạng thái: {str(e)}")

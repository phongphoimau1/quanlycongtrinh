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

def get_dashboard_stats():
    """
    Truy vấn và thống kê các chỉ số tổng quan cho Dashboard từ bảng 'projects'.
    Trả về tổng số công trình và số lượng theo từng trạng thái tiến độ.
    """
    try:
        res = supabase.table('projects').select('*').execute()
        projects = res.data if res.data else []
        
        total_projects = len(projects)
        
        # Thống kê số lượng công trình theo trạng thái
        status_counts = {}
        for p in projects:
            status = p.get('status', 'Mới tiếp nhận')
            if not status:
                status = 'Mới tiếp nhận'
            status_counts[status] = status_counts.get(status, 0) + 1
            
        return {
            "total": total_projects,
            "status_counts": status_counts,
            "projects": projects
        }
    except Exception as e:
        print(f"Lỗi truy vấn thống kê Dashboard: {e}")
        return {
            "total": 0,
            "status_counts": {},
            "projects": []
        }
def get_dashboard_stats():
    """
    Thống kê tổng quan cho Dashboard, chuẩn hóa tuyệt đối các trạng thái tiến độ
    để không bị lệch số liệu giữa thẻ Metric và Biểu đồ.
    """
    try:
        res = supabase.table('projects').select('*').execute()
        projects = res.data if res.data else []
        
        total_projects = len(projects)
        
        status_counts = {}
        for p in projects:
            raw_status = p.get('status')
            # Chuẩn hóa trạng thái: loại bỏ khoảng trắng thừa, mặc định là 'Mới tiếp nhận' nếu trống
            status = raw_status.strip() if raw_status else 'Mới tiếp nhận'
            
            # Gom nhóm chuẩn hóa tiếng Việt nếu cần thiết
            if status.lower() in ['dang thuc hien', 'đang thực hiện', 'in progress']:
                status = 'Đang thực hiện'
            elif status.lower() in ['da hoan thanh', 'đã hoàn thành', 'completed']:
                status = 'Đã hoàn thành'
            elif status.lower() in ['moi tiep nhan', 'mới tiếp nhận', 'pending']:
                status = 'Mới tiếp nhận'
                
            status_counts[status] = status_counts.get(status, 0) + 1
            
        return {
            "total": total_projects,
            "status_counts": status_counts,
            "projects": projects
        }
    except Exception as e:
        print(f"Lỗi truy vấn thống kê Dashboard: {e}")
        return {
            "total": 0,
            "status_counts": {},
            "projects": []
        }

    except Exception as e:
        raise Exception(f"Lỗi database khi cập nhật trạng thái: {str(e)}")
def update_project_status(project_id: str, new_status: str):
    """
    Cập nhật trạng thái công trình theo đúng ID (UUID) chuẩn của bảng projects
    và ghi nhận lịch sử vào bảng project_status_history.
    """
    try:
        if not project_id:
            raise Exception("Thiếu định danh project_id hợp lệ để cập nhật.")

        # 1. Lấy trạng thái cũ để ghi log lịch sử
        old_res = supabase.table('projects').select('status').eq('id', project_id).execute()
        old_status = old_res.data[0].get('status', 'Mới tiếp nhận') if old_res.data else "Mới tiếp nhận"

        # 2. Thực hiện lệnh UPDATE trực tiếp vào bảng 'projects'
        update_res = supabase.table('projects').update({
            "status": new_status
        }).eq('id', project_id).execute()

        if not update_res.data:
            raise Exception("Supabase từ chối cập nhật. Vui lòng kiểm tra quyền RLS trên bảng projects.")

        # 3. Ghi log lịch sử thay đổi trạng thái
        try:
            supabase.table('project_status_history').insert({
                "project_id": project_id,
                "old_status": old_status,
                "new_status": new_status,
                "note": f"Cập nhật trạng thái từ '{old_status}' sang '{new_status}'"
            }).execute()
        except Exception as history_err:
            print(f"Cảnh báo ghi log lịch sử: {history_err}")

        return True

    except Exception as e:
        raise Exception(f"Lỗi database khi cập nhật trạng thái: {str(e)}")

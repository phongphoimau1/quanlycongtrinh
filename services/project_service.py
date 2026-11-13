from core.database import supabase

# ID công ty mặc định đã tạo ở bước trên (có thể thay bằng auth sau này)
DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"

def get_projects(search_term=""):
    query = supabase.table("projects").select("id, project_code, project_name, customer_name, status, created_at")
    if search_term:
        query = query.ilike("project_name", f"%{search_term}%")
    
    # Sắp xếp mới nhất lên đầu
    query = query.order("created_at", desc=True)
    return query.execute().data

def create_project(data: dict):
    data["organization_id"] = DEFAULT_ORG_ID
    data["status"] = "Mới tiếp nhận"
    # project_code sẽ tự động được Supabase sinh ra qua Trigger
    return supabase.table("projects").insert(data).execute().data
def get_dashboard_stats():
    # Lấy toàn bộ project để thống kê (có thể tối ưu bằng RPC sau nếu data lớn)
    response = supabase.table("projects").select("status").execute()
    projects = response.data
    
    total = len(projects)
    new_projects = sum(1 for p in projects if p["status"] == "Mới tiếp nhận")
    processing = sum(1 for p in projects if p["status"] == "Đang xử lý")
    completed = sum(1 for p in projects if p["status"] == "Hoàn thành")
    
    return {
        "total": total,
        "new": new_projects,
        "processing": processing,
        "completed": completed
    }
def get_project_by_code(project_code):
    """Lấy chi tiết 1 công trình dựa vào mã"""
    response = supabase.table("projects").select("*").eq("project_code", project_code).execute()
    return response.data[0] if response.data else None

def get_all_projects():
    """Lấy toàn bộ danh sách công trình từ bảng projects trên Supabase"""
    try:
        res = supabase.table('projects').select('*').execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Lỗi lấy danh sách công trình: {e}")
        return []
def update_project_status(project_id: str, new_status: str):
    """
    Cập nhật trạng thái công trình trực tiếp vào bảng 'projects' 
    và ghi log lịch sử vào 'project_status_history'.
    """
    try:
        # 1. Lấy trạng thái cũ hiện tại trong CSDL để phục vụ việc ghi log lịch sử
        old_res = supabase.table('projects').select('status').eq('id', project_id).execute()
        old_status = old_res.data[0].get('status') if old_res.data else "Mới tiếp nhận"

        # 2. Thực hiện UPDATE trực tiếp vào bảng 'projects'
        update_res = supabase.table('projects').update({
            "status": new_status
        }).eq('id', project_id).execute()

        # Kiểm tra xem có thực sự update được dòng nào không
        if not update_res.data:
            raise Exception("Không tìm thấy bản ghi project tương ứng để cập nhật trên CSDL.")

        # 3. Ghi log lịch sử vào bảng 'project_status_history'
        try:
            supabase.table('project_status_history').insert({
                "project_id": project_id,
                "old_status": old_status,
                "new_status": new_status,
                "note": f"Cập nhật trạng thái từ '{old_status}' sang '{new_status}'"
            }).execute()
        except Exception as history_err:
            print(f"Cảnh báo ghi lịch sử status: {history_err}")

        return True

    except Exception as e:
        # Ném lỗi ra ngoài để giao diện hiển thị thông báo chi tiết
        raise Exception(f"Lỗi database khi cập nhật trạng thái: {str(e)}")

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
def update_project_status(project_id, new_status):
    """Cập nhật trạng thái công trình (Trigger DB sẽ tự động lưu lịch sử)"""
    return supabase.table("projects").update({"status": new_status}).eq("id", project_id).execute().data

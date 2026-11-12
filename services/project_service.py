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

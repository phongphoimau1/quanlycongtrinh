from core.database import supabase

def get_emails(search_term=""):
    """Lấy danh sách email và sắp xếp mới nhất lên đầu"""
    query = supabase.table("emails").select("*").order("received_at", desc=True)
    if search_term:
        # Tìm kiếm theo tiêu đề (subject) hoặc người gửi (sender_email)
        query = query.or_(f"subject.ilike.%{search_term}%,sender_email.ilike.%{search_term}%")
    return query.execute().data

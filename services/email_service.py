from core.database import supabase

def get_emails(search_term=""):
    """
    Lấy danh sách email và tự động đồng bộ trạng thái 'Đã giao' 
    dựa trên việc email đó đã có trong bảng 'project_emails' hay chưa.
    """
    try:
        # Lấy toàn bộ emails
        res = supabase.table('emails').select('*').order('received_at', desc=True).execute()
        emails = res.data if res.data else []

        # Lấy danh sách email_id đã được tạo dự án từ bảng trung gian 'project_emails'
        linked_res = supabase.table('project_emails').select('email_id').execute()
        linked_email_ids = {item['email_id'] for item in linked_res.data} if linked_res.data else set()

        # Chuẩn hóa trạng thái động cho từng email
        for email in emails:
            email_id = email.get('id')
            current_status = email.get('processing_status')
            
            # Nếu đã có trong bảng project_emails hoặc status là Đã giao -> Đổi thành "Đã giao"
            if email_id in linked_email_ids or current_status in ['Đã giao', 'Đã tạo dự án']:
                email['processing_status'] = 'Đã giao'
            else:
                email['processing_status'] = 'Chưa xử lý'

        # Lọc theo từ khóa tìm kiếm nếu có
        if search_term:
            emails = [
                e for e in emails 
                if (e.get('subject') and search_term.lower() in e['subject'].lower()) or 
                   (e.get('sender_email') and search_term.lower() in e['sender_email'].lower())
            ]

        return emails
    except Exception as e:
        print(f"Lỗi lấy danh sách email: {e}")
        return []

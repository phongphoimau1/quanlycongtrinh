import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_emails(search_term=""):
    """
    Hàm lấy danh sách email kết hợp kiểm tra bảng 'project_emails':
    - Luôn tải đầy đủ danh sách thư từ CSDL.
    - Tự động đánh dấu trạng thái 'Đã giao' nếu email đó đã được liên kết với bất kỳ dự án nào trong 'project_emails'.
    """
    try:
        # 1. Lấy toàn bộ danh sách email
        res = supabase.table('emails').select('*').order('received_at', desc=True).execute()
        emails = res.data if res.data else []

        if not emails:
            return []

        # 2. Lấy danh sách các email_id đã được tạo dự án từ bảng trung gian 'project_emails'
        linked_email_ids = set()
        try:
            link_res = supabase.table('project_emails').select('email_id').execute()
            if link_res.data:
                linked_email_ids = {str(item['email_id']) for item in link_res.data if item.get('email_id')}
        except Exception:
            pass

        # 3. Chuẩn hóa trạng thái động cho từng email
        for email in emails:
            email_id = str(email.get('id', ''))
            db_status = email.get('processing_status')
            
            # Nếu email đã có trong bảng project_emails hoặc status trong DB là Đã giao -> Đổi thành "Đã giao"
            if email_id in linked_email_ids or db_status in ['Đã giao', 'Đã tạo dự án']:
                email['processing_status'] = 'Đã giao'
            else:
                email['processing_status'] = 'Chưa xử lý'

        # 4. Lọc theo từ khóa tìm kiếm (nếu có)
        if search_term:
            keyword = search_term.lower()
            filtered_emails = []
            for e in emails:
                subject = str(e.get('subject', '')).lower()
                sender = str(e.get('sender_email', '')).lower()
                if keyword in subject or keyword in sender:
                    filtered_emails.append(e)
            return filtered_emails

        return emails

    except Exception as e:
        print(f"Lỗi truy vấn email: {e}")
        return []

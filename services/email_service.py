import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_emails(search_term=""):
    """
    Hàm lấy danh sách email kết hợp kiểm tra bảng 'project_emails':
    - Luôn tải đầy đủ danh sách thư từ CSDL.
    - Tự động đánh dấu trạng thái 'Đã giao' nếu email đó đã được liên kết trong 'project_emails' 
      hoặc có cột processing_status là 'Đã giao'.
    """
    try:
        # 1. Lấy toàn bộ danh sách email từ CSDL
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
                print(f"DEBUG - Các email_id đã liên kết dự án: {linked_email_ids}")
        except Exception as err:
            print(f"DEBUG - Lỗi khi query project_emails: {err}")
            pass

        # 3. Chuẩn hóa trạng thái động cho từng email
        for email in emails:
            email_id = str(email.get('id', ''))
            db_status = str(email.get('processing_status', '')).strip()
            
            # Kiểm tra điều kiện "Đã giao": có trong bảng liên kết hoặc DB lưu trạng thái đã giao
            if email_id in linked_email_ids or db_status in ['Đã giao', 'Đã tạo dự án', 'Đã xử lý']:
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
        print(f"Lỗi truy vấn email trong service: {e}")
        return []

def update_email_status(email_id: str, status: str = "Đã giao"):
    """
    Hàm chủ động cập nhật trạng thái xử lý của email trực tiếp trên bảng 'emails'.
    Giúp đồng bộ ngay lập tức khi người dùng bấm nút xác nhận.
    """
    try:
        res = supabase.table('emails').update({
            "processing_status": status
        }).eq("id", email_id).execute()
        
        print(f"DEBUG - Update status email {email_id} thành {status}: {res.data}")
        return True if res.data else False
    except Exception as e:
        print(f"Lỗi cập nhật trạng thái email tại CSDL: {e}")
        return False

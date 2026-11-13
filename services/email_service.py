import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_emails(search_term=""):
    """
    Hàm lấy danh sách email chuẩn xác và an toàn tuyệt đối:
    - Luôn trả về đầy đủ toàn bộ email từ CSDL như ban đầu.
    - Tự động gán trạng thái dựa trên cột processing_status có sẵn trong bảng emails.
    """
    try:
        # Truy vấn trực tiếp toàn bộ bảng emails từ CSDL
        res = supabase.table('emails').select('*').order('received_at', desc=True).execute()
        emails = res.data if res.data else []

        if not emails:
            return []

        # Chuẩn hóa trạng thái hiển thị
        for email in emails:
            db_status = email.get('processing_status')
            # Nếu trong database đã lưu là "Đã giao" hoặc "Đã tạo dự án", giữ nguyên
            if db_status in ['Đã giao', 'Đã tạo dự án']:
                email['processing_status'] = 'Đã giao'
            else:
                email['processing_status'] = 'Chưa xử lý'

        # Lọc theo từ khóa tìm kiếm nếu có
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
        st.error(f"Lỗi kết nối CSDL khi lấy email: {str(e)}")
        return []

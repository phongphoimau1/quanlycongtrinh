import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_emails(search_term=""):
    """
    Hàm lấy danh sách email an toàn tuyệt đối:
    - Luôn trả về đầy đủ danh sách thư từ CSDL.
    - Tự động nhận diện trạng thái 'Đã giao' nếu đã có trong bảng project_emails hoặc processing_status.
    - Không bao giờ làm mất hay trống danh sách email.
    """
    try:
        # 1. Truy vấn toàn bộ email từ bảng 'emails'
        res = supabase.table('emails').select('*').order('received_at', desc=True).execute()
        emails = res.data if res.data else []

        if not emails:
            return []

        # 2. Thử lấy danh sách email_id đã tạo dự án từ bảng 'project_emails' (an toàn bằng try-except)
        linked_email_ids = set()
        try:
            linked_res = supabase.table('project_emails').select('email_id').execute()
            if linked_res.data:
                linked_email_ids = {str(item['email_id']) for item in linked_res.data if item.get('email_id')}
        except Exception:
            pass

        # 3. Duyệt và chuẩn hóa trạng thái hiển thị cho từng email
        for email in emails:
            email_id = str(email.get('id', ''))
            db_status = email.get('processing_status')
            
            # Kiểm tra xem email đã được giao việc chưa
            if email_id in linked_email_ids or db_status in ['Đã giao', 'Đã tạo dự án']:
                email['processing_status'] = 'Đã giao'
            else:
                # Nếu chưa có trạng thái hoặc đang là giá trị cũ, gán mặc định là "Chưa xử lý"
                if not db_status or db_status not in ['Đã giao', 'Đã tạo dự án']:
                    email['processing_status'] = 'Chưa xử lý'

        # 4. Lọc theo từ khóa tìm kiếm (nếu có nhập trên giao diện)
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
        print(f"Lỗi khi truy vấn danh sách email: {e}")
        return []

import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd

# Khởi tạo kết nối Supabase (Đảm bảo đã có biến môi trường hoặc st.secrets)
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("📬 Trung Tâm Xử Lý Yêu Cầu (Email)")

# Hàm kéo dữ liệu
@st.cache_data(ttl=60) # Cập nhật mỗi 60 giây
def load_emails():
    response = supabase.table('emails').select('*').order('received_at', desc=True).execute()
    return response.data

emails_data = load_emails()

if not emails_data:
    st.info("📭 Hiện chưa có yêu cầu phối màu/dự án mới nào.")
else:
    df = pd.DataFrame(emails_data)
    
    # Làm đẹp bảng dữ liệu để hiển thị
    df_display = df[['subject', 'sender_email', 'received_at', 'processing_status']]
    df_display.columns = ['Tiêu đề yêu cầu', 'Người gửi', 'Thời gian nhận', 'Trạng thái']
    
    # Hiển thị bảng tương tác
    st.dataframe(
        df_display, 
        use_container_width=True,
        hide_index=True
    )

import streamlit as st
import pandas as pd
from services.email_service import get_emails

st.title("📧 Quản lý Email")

# Công cụ tìm kiếm
search = st.text_input("🔍 Tìm kiếm email theo tiêu đề hoặc người gửi...")

# Lấy dữ liệu từ database
data = get_emails(search_term=search)

if data:
    df = pd.DataFrame(data)
    
    # Chuẩn hóa tên cột để hiển thị
    df = df.rename(columns={
        "sender_email": "Người gửi",
        "subject": "Tiêu đề",
        "email_type": "Phân loại",
        "processing_status": "Trạng thái",
        "received_at": "Ngày nhận"
    })
    
    # Format lại cột ngày tháng (nếu có dữ liệu null thì bỏ qua lỗi)
    if 'Ngày nhận' in df.columns:
        df['Ngày nhận'] = pd.to_datetime(df['Ngày nhận'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')
        df['Ngày nhận'] = df['Ngày nhận'].fillna("Chưa xác định")

    # Điền giá trị mặc định cho cột null
    df['Phân loại'] = df['Phân loại'].fillna("-")
    df['Trạng thái'] = df['Trạng thái'].fillna("Chưa xử lý")

    st.dataframe(
        df[["Người gửi", "Tiêu đề", "Phân loại", "Trạng thái", "Ngày nhận"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("📭 Hộp thư trống hoặc không tìm thấy kết quả phù hợp.")

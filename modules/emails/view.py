import streamlit as st
import pandas as pd
from services.email_service import get_emails

st.title("✉️ Quản lý Email Yêu Cầu")

search = st.text_input("🔍 Tìm kiếm email theo tiêu đề hoặc người gửi...")

if st.button("🔄 Làm mới"):
    st.cache_data.clear()
    st.rerun()

emails_data = get_emails(search)

if emails_data:
    df_email = pd.DataFrame(emails_data)
    
    # Đảm bảo cột hiển thị trạng thái phản ánh đúng giá trị
    display_df = df_email[["sender_email", "subject", "email_type", "processing_status", "received_at"]].rename(columns={
        "sender_email": "Người gửi",
        "subject": "Tiêu đề",
        "email_type": "Phân loại",
        "processing_status": "Trạng thái",
        "received_at": "Ngày nhận"
    })

    st.markdown("### 📋 Danh sách Yêu cầu")
    
    # Hiển thị bảng kèm cấu hình đổi màu trực quan cho trạng thái "Đã giao"
    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        column_config={
            "Trạng thái": st.column_config.TextColumn(
                "Trạng thái xử lý",
                help="Trạng thái phân công công trình",
                width="medium"
            )
        }
    )
else:
    st.info("📭 Chưa có email nào trong hệ thống.")

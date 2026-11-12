import streamlit as st
import pandas as pd
from services.project_service import get_projects

st.title("🏗️ Quản lý Công trình")

# Thanh công cụ[cite: 2]
col1, col2 = st.columns([8, 2])
with col1:
    search = st.text_input("🔍 Tìm kiếm công trình (Nhập tên)...")
with col2:
    st.write("") # Căn lề
    if st.button("➕ Tạo công trình", use_container_width=True, type="primary"):
        st.switch_page("modules/projects/create.py")

# Bảng dữ liệu[cite: 2]
st.subheader("Danh sách dự án")
data = get_projects(search_term=search)

if data:
    df = pd.DataFrame(data)
    # Định dạng lại bảng cho đẹp
    df = df.rename(columns={
        "project_code": "Mã CT", 
        "project_name": "Tên công trình",
        "customer_name": "Khách hàng",
        "status": "Trạng thái",
        "created_at": "Ngày tạo"
    })
    # Chuyển đổi format ngày tháng
    df['Ngày tạo'] = pd.to_datetime(df['Ngày tạo']).dt.strftime('%d/%m/%Y %H:%M')
    
    st.dataframe(
        df[["Mã CT", "Tên công trình", "Khách hàng", "Trạng thái", "Ngày tạo"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Không tìm thấy công trình nào.")

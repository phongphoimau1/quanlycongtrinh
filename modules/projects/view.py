import streamlit as st
import pandas as pd
from services.project_service import get_projects

st.title("🏗️ Quản lý Công trình")

col1, col2 = st.columns([8, 2])
with col1:
    search = st.text_input("🔍 Tìm kiếm công trình (Nhập tên)...")
with col2:
    st.write("")
    if st.button("➕ Tạo công trình", use_container_width=True, type="primary"):
        st.switch_page("modules/projects/create.py")

data = get_projects(search_term=search)

if data:
    df = pd.DataFrame(data)
    df = df.rename(columns={
        "project_code": "Mã CT", 
        "project_name": "Tên công trình",
        "customer_name": "Khách hàng",
        "status": "Trạng thái",
        "created_at": "Ngày tạo"
    })
    df['Ngày tạo'] = pd.to_datetime(df['Ngày tạo']).dt.strftime('%d/%m/%Y %H:%M')
    
    st.dataframe(
        df[["Mã CT", "Tên công trình", "Khách hàng", "Trạng thái", "Ngày tạo"]],
        use_container_width=True,
        hide_index=True
    )
    
    # 200 IQ UX: Thanh chọn nhanh công trình để xem chi tiết
    st.write("---")
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        selected_code = st.selectbox("Chọn công trình để xem chi tiết / cập nhật:", df["Mã CT"].tolist())
    with col_btn:
        st.write("")
        if st.button("Mở chi tiết ➡️", use_container_width=True):
            st.switch_page(f"modules/projects/detail.py?code={selected_code}")
else:
    st.info("Không tìm thấy công trình nào.")

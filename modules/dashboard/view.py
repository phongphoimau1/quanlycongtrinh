import streamlit as st
from services.project_service import get_dashboard_stats

st.title("📊 Tổng quan Hệ thống")

# Lấy dữ liệu thống kê thực tế
stats = get_dashboard_stats()

# Hiển thị các thẻ chỉ số (KPI Cards)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Tổng công trình", value=stats["total"])
with col2:
    st.metric(label="Mới tiếp nhận", value=stats["new"])
with col3:
    st.metric(label="Đang xử lý", value=stats["processing"])
with col4:
    st.metric(label="Đã hoàn thành", value=stats["completed"])

st.markdown("---")

# Layout chia cột cho biểu đồ/danh sách sau này
col_left, col_right = st.columns([6, 4])

with col_left:
    st.subheader("📈 Tiến độ tuần này")
    st.info("Module biểu đồ sẽ được tích hợp ở giai đoạn Báo cáo (P0).")

with col_right:
    st.subheader("⚠️ Cần chú ý")
    st.warning("Chưa có công trình nào sắp đến hạn.")

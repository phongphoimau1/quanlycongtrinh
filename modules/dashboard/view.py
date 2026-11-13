import streamlit as st
from services.project_service import get_dashboard_stats

st.title("📊 Tổng quan Tiến độ Dự án (Dashboard)")

# Lấy dữ liệu thống kê
stats = get_dashboard_stats()

total = stats.get("total", 0)
status_counts = stats.get("status_counts", {})

# Hiển thị các metric tổng quan
col1, col2, col3 = st.columns(3)
col1.metric("Tổng số công trình", total)
col2.metric("Đang thực hiện", status_counts.get("Đang thực hiện", 0))
col3.metric("Đã hoàn thành", status_counts.get("Đã hoàn thành", 0))

st.markdown("---")
st.subheader("📈 Chi tiết tiến độ các công trình")

if total > 0:
    # Hiển thị bảng hoặc biểu đồ thống kê trạng thái
    st.bar_chart(status_counts)
else:
    st.info("📭 Chưa có dữ liệu công trình để hiển thị thống kê.")

import streamlit as st
from services.project_service import get_dashboard_stats

st.title("📊 Tổng quan Tiến độ Dự án (Dashboard)")

# Lấy dữ liệu thống kê đã chuẩn hóa
stats = get_dashboard_stats()

total = stats.get("total", 0)
status_counts = stats.get("status_counts", {})

# Lấy chính xác số lượng từ từ điển đã chuẩn hóa
dang_thuc_hien = (
    status_counts.get("Đang thực hiện", 0) + 
    status_counts.get("Mới tiếp nhận", 0) # Gộp cả Mới tiếp nhận vào nhóm đang xử lý nếu muốn hiển thị tổng lực
)
da_hoan_thanh = status_counts.get("Đã hoàn thành", 0)

# Hiển thị Metric khớp 100% với dữ liệu thực tế
col1, col2, col3 = st.columns(3)
col1.metric("Tổng số công trình", total)
col2.metric("Đang thực hiện / Tiếp nhận", dang_thuc_hien)
col3.metric("Đã hoàn thành", da_hoan_thanh)

st.markdown("---")
st.subheader("📈 Phân bổ Tiến độ Công trình")

if total > 0:
    # Hiển thị biểu đồ thống kê trạng thái chi tiết
    st.bar_chart(status_counts)
    
    with st.expander("🔍 Xem chi tiết số liệu từng trạng thái"):
        st.json(status_counts)
else:
    st.info("📭 Chưa có dữ liệu công trình trên hệ thống.")

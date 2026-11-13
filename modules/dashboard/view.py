import streamlit as st
from services.project_service import get_dashboard_stats

st.title("📊 Tổng quan Tiến độ Dự án (Dashboard)")

# Lấy dữ liệu thống kê
stats = get_dashboard_stats()

total = stats.get("total", 0)
status_counts = stats.get("status_counts", {})

# Lấy chính xác key từ dictionary thực tế ("Hoàn thành" và "Mới tiếp nhận" / "Đang thực hiện")
so_hoan_thanh = status_counts.get("Hoàn thành", 0) + status_counts.get("Đã hoàn thành", 0)
dang_xu_ly = status_counts.get("Đang thực hiện", 0) + status_counts.get("Mới tiếp nhận", 0)

# Hiển thị Metric chuẩn xác
col1, col2, col3 = st.columns(3)
col1.metric("Tổng số công trình", total)
col2.metric("Đang xử lý / Tiếp nhận", dang_xu_ly)
col3.metric("Đã hoàn thành", so_hoan_thanh)

st.markdown("---")
st.subheader("📈 Phân bổ Tiến độ Công trình")

if total > 0:
    # Hiển thị biểu đồ thống kê trạng thái
    st.bar_chart(status_counts)
    
    with st.expander("🔍 Xem chi tiết số liệu từng trạng thái"):
        st.json(status_counts)
else:
    st.info("📭 Chưa có dữ liệu công trình trên hệ thống.")

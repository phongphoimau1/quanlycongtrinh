import streamlit as st
import pandas as pd
from services.email_service import get_emails

st.title("📧 Quản lý Email Yêu Cầu")

# --- 1. THANH CÔNG CỤ: TÌM KIẾM & LÀM MỚI ---
col1, col2 = st.columns([4, 1])
with col1:
    search = st.text_input("🔍 Tìm kiếm email theo tiêu đề hoặc người gửi...", placeholder="Nhập từ khóa...")
with col2:
    st.write("") # Căn chỉnh layout cho nút bấm ngang hàng với ô tìm kiếm
    st.write("")
    if st.button("🔄 Làm mới", use_container_width=True):
        st.cache_data.clear() # Xóa cache để ép tải lại dữ liệu mới nhất
        st.rerun()

# --- 2. TẢI VÀ XỬ LÝ DỮ LIỆU ---
with st.spinner("Đang đồng bộ dữ liệu..."):
    try:
        data = get_emails(search_term=search)
    except Exception as e:
        st.error(f"❌ Lỗi kết nối CSDL: {e}")
        data = None

if data:
    df = pd.DataFrame(data)
    
    # [NÂNG CẤP]: Dashboard Thống kê nhanh
    total_emails = len(df)
    pending_emails = len(df[df['processing_status'] == 'Chưa xử lý'])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng thư yêu cầu", total_emails)
    m2.metric("Chưa xử lý (Cần duyệt)", pending_emails, delta="- Cần làm ngay" if pending_emails > 0 else "Hoàn tất", delta_color="inverse")
    st.divider()

    # Chuẩn hóa dữ liệu hiển thị (GIỮ LẠI CỘT ID ĐỂ XỬ LÝ LOGIC NGẦM)
    df = df.rename(columns={
        "id": "ID", 
        "sender_email": "Người gửi",
        "subject": "Tiêu đề",
        "email_type": "Phân loại",
        "processing_status": "Trạng thái",
        "received_at": "Ngày nhận"
    })
    
    if 'Ngày nhận' in df.columns:
        df['Ngày nhận'] = pd.to_datetime(df['Ngày nhận'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')
        df['Ngày nhận'] = df['Ngày nhận'].fillna("Chưa xác định")

    df['Phân loại'] = df['Phân loại'].fillna("-")
    df['Trạng thái'] = df['Trạng thái'].fillna("Chưa xử lý")

    st.markdown("### 📋 Danh sách Yêu cầu")
    
    # --- 3. BẢNG DỮ LIỆU TƯƠNG TÁC (Tích hợp Selection) ---
    # Sử dụng on_select="rerun" để bắt sự kiện click của người dùng (Streamlit >= 1.35)
    event = st.dataframe(
        df[["Người gửi", "Tiêu đề", "Phân loại", "Trạng thái", "Ngày nhận"]],
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # --- 4. KHU VỰC THAO TÁC (HIỂN THỊ KHI CLICK VÀO 1 DÒNG) ---
    selected_rows = event.selection.rows
    if selected_rows:
        selected_index = selected_rows[0]
        selected_email = df.iloc[selected_index]
        
        with st.expander(f"⚙️ Khu vực xử lý: {selected_email['Tiêu đề']}", expanded=True):
            st.info(f"**Người gửi:** {selected_email['Người gửi']} | **Ngày nhận:** {selected_email['Ngày nhận']}")
            
            if selected_email['Trạng thái'] == 'Chưa xử lý':
                if st.button("🚀 Chuyển hóa thành Dự Án Mới", type="primary", use_container_width=True):
                    # KẾT NỐI NGHIỆP VỤ Ở ĐÂY
                    st.success("Đang gọi hàm tạo dự án mới... (Sẽ kết nối vào modules/projects)")
                    # TODO: Gọi hàm create_project(selected_email)
            else:
                st.success("✅ Email này đã được đưa vào luồng dự án.")

else:
    st.info("📭 Hộp thư trống hoặc không tìm thấy kết quả phù hợp.")

import streamlit as st
import pandas as pd
from services.email_service import get_emails
from modules.ai_processing.service import process_email_with_ai  # [ĐÃ SỬA] Đưa import lên đầu file

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
    
    # Dashboard Thống kê nhanh
    total_emails = len(df)
    pending_emails = len(df[df['processing_status'] == 'Chưa xử lý'])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng thư yêu cầu", total_emails)
    m2.metric("Chưa xử lý (Cần duyệt)", pending_emails, delta="- Cần làm ngay" if pending_emails > 0 else "Hoàn tất", delta_color="inverse")
    st.divider()

    # Chuẩn hóa dữ liệu hiển thị
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
        
        # [ĐÃ SỬA] Gom lại thành 1 khối Expander duy nhất, gọn gàng và logic
        with st.expander(f"⚙️ Khu vực xử lý: {selected_email['Tiêu đề']}", expanded=True):
            st.info(f"**Người gửi:** {selected_email['Người gửi']} | **Ngày nhận:** {selected_email['Ngày nhận']}")
            
            if selected_email['Trạng thái'] == 'Chưa xử lý':
                st.warning("⚠️ Email này chưa được phân tích. Hãy để AI đọc và trích xuất dữ liệu tự động.")
                
                if st.button("✨ Phân tích bằng Trí tuệ Nhân tạo", type="primary", use_container_width=True):
                    with st.spinner("🤖 AI đang đọc và phân tích email..."):
                        # Kích hoạt Siêu não Gemini
                        result = process_email_with_ai(
                            email_id=selected_email['ID'],
                            subject=selected_email['Tiêu đề'],
                            sender=selected_email['Người gửi'],
                            content="" # Sẵn sàng cho nâng cấp lấy body email sau này
                        )
                        
                        if result["success"]:
                            st.success(f"✅ Đã phân tích xong! (Độ tự tin: {result['confidence'] * 100:.0f}%)")
                            st.json(result["data"])
                            st.info("👉 Dữ liệu đã được chuyển sang tab 'Chờ xác nhận'.")
                            
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(result["message"])
            
            elif selected_email['Trạng thái'] == 'Chờ duyệt AI':
                st.success("🤖 AI đã xử lý email này. Vui lòng chuyển sang menu 'Chờ xác nhận' để duyệt tạo dự án.")
            
            else:
                # Bắt các trạng thái khác (Đã xử lý, Đã hủy...)
                st.success(f"✅ Email đang ở trạng thái: {selected_email['Trạng thái']}")

else:
    st.info("📭 Hộp thư trống hoặc không tìm thấy kết quả phù hợp.")

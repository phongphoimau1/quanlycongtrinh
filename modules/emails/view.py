import streamlit as st
import pandas as pd
from services.email_service import get_emails
from modules.ai_processing.service import create_project_directly_from_email

st.title("📧 Quản lý Email Yêu Cầu")

# --- 1. THANH CÔNG CỤ: TÌM KIẾM & LÀM MỚI ---
col1, col2 = st.columns([4, 1])
with col1:
    search = st.text_input("🔍 Tìm kiếm email theo tiêu đề hoặc người gửi...", placeholder="Nhập từ khóa...")
with col2:
    st.write("") 
    st.write("")
    if st.button("🔄 Làm mới", width='stretch'):
        st.cache_data.clear()
        st.rerun()
# Tô màu trực quan cho cột Trạng thái trên bảng danh sách email
    def highlight_status(val):
        if val == 'Đã tạo dự án':
            return 'background-color: #d4edda; color: #155724;' # Xanh lá nhẹ
        elif val == 'Chưa xử lý':
            return 'background-color: #fff3cd; color: #856404;' # Vàng nhẹ
        return ''

    # Hiển thị dataframe với định dạng màu sắc chuyên nghiệp
    st.dataframe(
        df[["Người gửi", "Tiêu đề", "Phân loại", "Trạng thái", "Ngày nhận"]].style.applymap(
            highlight_status, subset=['Trạng thái']
        ),
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )
# --- 2. TẢI VÀ XỬ LÝ DỮ LIỆU ---
with st.spinner("Đang đồng bộ dữ liệu..."):
    try:
        data = get_emails(search_term=search)
    except Exception as e:
        st.error(f"❌ Lỗi kết nối CSDL: {e}")
        data = None

if data:
    df = pd.DataFrame(data)
    
    total_emails = len(df)
    pending_emails = len(df[df['processing_status'] == 'Chưa xử lý'])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng thư yêu cầu", total_emails)
    m2.metric("Chưa xử lý (Cần duyệt)", pending_emails, delta="- Cần làm ngay" if pending_emails > 0 else "Hoàn tất", delta_color="inverse")
    st.divider()

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
    
    event = st.dataframe(
        df[["Người gửi", "Tiêu đề", "Phân loại", "Trạng thái", "Ngày nhận"]],
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # --- 3. KHU VỰC THAO TÁC (HIỂN THỊ KHI CLICK VÀO 1 DÒNG) ---
    selected_rows = event.selection.rows
    if selected_rows:
        selected_index = selected_rows[0]
        selected_email = df.iloc[selected_index]
        
        with st.expander(f"⚙️ Khu vực xử lý: {selected_email['Tiêu đề']}", expanded=True):
            st.info(f"**Người gửi:** {selected_email['Người gửi']} | **Ngày nhận gốc:** {selected_email['Ngày nhận']}")
            
            st.markdown("#### ⚡ Giao nhiệm vụ & Khởi tạo Dự án trực tiếp")
            
            with st.form(f"project_form_{selected_email['ID']}"):
                cust_name = st.text_input("Tên khách hàng", value="")
                cust_phone = st.text_input("Số điện thoại liên hệ", value="")
                proj_address = st.text_input("Địa chỉ công trình", value="")
                proj_type = st.selectbox("Phân loại dự án", ["Nhà phố", "Biệt thự", "Quán Cafe", "Nhà ống", "Chưa rõ"])
                
                # Bổ sung các trường: Ngày nhận, Ngày đến hạn, Phân công nhân viên
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    received_date = st.text_input("Ngày nhận", value=selected_email['Ngày nhận'])
                with col_d2:
                    due_date = st.date_input("Ngày đến hạn hoàn thành")
                
                assigned_to = st.selectbox(
                    "Giao cho nhân viên phụ trách", 
                    ["Kỹ sư Nguyễn Văn A", "Kỹ sư Trần Văn B", "Kiến trúc sư Lê Thị C", "Quản lý dự án - Hoàng Minh"]
                )
                
                requirements = st.text_area("Yêu cầu chi tiết từ email", value=selected_email['Tiêu đề'])
                
                submitted = st.form_submit_button("🚀 Xác nhận & Khởi tạo Dự án Ngay", type="primary", width='stretch')
                
                if submitted:
                    if not cust_name or not proj_address:
                        st.warning("⚠️ Vui lòng nhập đầy đủ Tên khách hàng và Địa chỉ công trình!")
                    else:
                        result = create_project_directly_from_email(
                            email_id=selected_email['ID'],
                            customer_name=cust_name,
                            customer_phone=cust_phone,
                            project_address=proj_address,
                            project_type=proj_type,
                            requirements=requirements,
                            received_date=received_date,
                            due_date=str(due_date),
                            assigned_to=assigned_to
                        )
                        
                        if result["success"]:
                            st.success(result["message"])
                            st.balloons()
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(result["message"])
else:
    st.info("📭 Hộp thư trống hoặc không tìm thấy kết quả phù hợp.")

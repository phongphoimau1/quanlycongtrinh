import streamlit as st
import pandas as pd
from services.email_service import get_emails
from modules.ai_processing.service import create_project_directly_from_email
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📧 Quản lý Email Yêu Cầu")

# --- 1. THANH CÔNG CỤ ---
col1, col2 = st.columns([4, 1])
with col1:
    search = st.text_input("🔍 Tìm kiếm email theo tiêu đề hoặc người gửi...", placeholder="Nhập từ khóa...")
with col2:
    st.write("") 
    st.write("")
    if st.button("🔄 Làm mới", width='stretch'):
        st.cache_data.clear()
        st.rerun()

# --- 2. TẢI DỮ LIỆU ---
with st.spinner("Đang đồng bộ dữ liệu..."):
    try:
        data = get_emails(search_term=search)
    except Exception as e:
        st.error(f"❌ Lỗi kết nối CSDL: {e}")
        data = None

if data:
    df = pd.DataFrame(data)
    
    total_emails = len(df)
    pending_emails = len(df[df['processing_status'] != 'Đã giao'])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng thư yêu cầu", total_emails)
    m2.metric("Chưa giao việc", pending_emails, delta="- Cần xử lý" if pending_emails > 0 else "Hoàn tất", delta_color="inverse")
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
    
    # Tô màu trạng thái trực quan
    def highlight_status(val):
        if val == 'Đã giao':
            return 'background-color: #d4edda; color: #155724;' # Xanh lá (Đã giao)
        elif val == 'Chưa xử lý':
            return 'background-color: #fff3cd; color: #856404;' # Vàng (Chưa xử lý)
        return ''

    # Hiển thị bảng kèm Styler tô màu chuẩn xác
    event = st.dataframe(
        df[["Người gửi", "Tiêu đề", "Phân loại", "Trạng thái", "Ngày nhận"]].style.map(
            highlight_status, subset=['Trạng thái']
        ),
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # --- 3. KHU VỰC THAO TÁC KHI CLICK ---
    selected_rows = event.selection.rows
    if selected_rows:
        selected_index = selected_rows[0]
        selected_email = df.iloc[selected_index]
        
        with st.expander(f"⚙️ Khu vực xử lý: {selected_email['Tiêu đề']}", expanded=True):
            st.info(f"**Người gửi:** {selected_email['Người gửi']} | **Ngày nhận:** {selected_email['Ngày nhận']} | **Trạng thái hiện tại:** `{selected_email['Trạng thái']}`")
            
            col_act1, col_act2 = st.columns([3, 1])
            with col_act2:
                # NÚT XÁC NHẬN THỦ CÔNG: Đánh dấu đã giao ngay lập tức
                if selected_email['Trạng thái'] != 'Đã giao':
                    if st.button("✅ Đánh dấu Đã giao", type="secondary", width='stretch'):
                        try:
                            res_update = supabase.table('emails').update({
                                "processing_status": "Đã giao"
                            }).eq("id", selected_email['ID']).execute()
                            
                            st.success("🎉 Đã cập nhật trạng thái email thành 'Đã giao'!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as err:
                            st.error(f"❌ Lỗi cập nhật: {err}")

            # Kiểm tra nếu đã giao rồi thì cảnh báo
            if selected_email['Trạng thái'] == 'Đã giao':
                st.success("✅ Email này đã được xử lý / bàn giao trên hệ thống.")
            else:
                st.markdown("#### ⚡ Giao nhiệm vụ & Khởi tạo Dự án")
                
                # Truy vấn categories để chọn loại công trình nếu cần
                cat_res = supabase.table('categories').select('id, category_name').execute()
                categories_list = cat_res.data if cat_res.data else []
                cat_dict = {c['category_name']: c['id'] for c in categories_list}

                with st.form(f"project_form_{selected_email['ID']}"):
                    customer_name = st.text_input("Tên khách hàng", value="")
                    project_name = st.text_input("Tên công trình", value=selected_email['Tiêu đề'])
                    project_code = st.text_input("Mã công trình (VD: CT-2026-001)", value="")
                    
                    category_name = st.selectbox("Danh mục dự án", list(cat_dict.keys()) if cat_dict else ["Mặc định"])
                    category_id = cat_dict.get(category_name)

                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        received_date = st.text_input("Ngày nhận", value=selected_email['Ngày nhận'])
                    with col_d2:
                        due_date = st.date_input("Ngày đến hạn hoàn thành (Completed Date)")
                    
                    # DANH SÁCH NHÂN SỰ CỐ ĐỊNH (Hardcode trực tiếp theo yêu cầu)
                    staff_options = [
                        "Chưa phân nhân sự",
                        "Ms Hân", 
                        "Mr Peter", 
                        "Mr Thịnh", 
                        "Ms Hương", 
                        "Ms Hiếu"
                    ]
                    staff_name = st.selectbox("Giao cho nhân viên phụ trách", staff_options)
                    # Nếu chọn "Chưa phân nhân sự" thì truyền None, ngược lại truyền thẳng tên chuỗi
                    assigned_to_value = staff_name if staff_name != "Chưa phân nhân sự" else None

                    status = st.selectbox("Trạng thái công trình", ["Đang thực hiện", "Đã hoàn thành", "Tạm dừng"])
                    request_content = st.text_area("Nội dung yêu cầu chi tiết", value=selected_email['Tiêu đề'])
                    
                    submitted = st.form_submit_button("🚀 Xác nhận & Khởi tạo Công trình", type="primary", width='stretch')
                    
                    if submitted:
                        if not customer_name:
                            st.warning("⚠️ Vui lòng nhập Tên khách hàng!")
                        else:
                            # 1. Xác định giá trị nhân viên phụ trách ngay khi submit form
                            assigned_to_value = staff_name if staff_name != "Chưa phân nhân sự" else None

                            # 2. Gọi hàm tạo dự án với đầy đủ tham số
                            result = create_project_directly_from_email(
                                email_id=selected_email['ID'],
                                customer_name=customer_name,
                                project_name=project_name,
                                project_code=project_code,
                                category_id=category_id,
                                assigned_to_uuid=assigned_to_value, # Truyền thẳng tên nhân viên đã chọn
                                received_date=received_date,
                                due_date=str(due_date),
                                request_content=request_content,
                                status=status
                            )
                            
                            if result["success"]:
                                st.success(result["message"])
                                if result.get("project_id"):
                                    st.info(f"🔑 ID Công trình trên hệ thống: `{result['project_id']}`")
                                st.balloons()
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(result["message"])
else:
    st.info("📭 Hộp thư trống hoặc không tìm thấy kết quả phù hợp.")

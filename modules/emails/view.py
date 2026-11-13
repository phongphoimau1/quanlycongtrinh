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
            st.info(f"**Người gửi:** {selected_email['Người gửi']} | **Ngày nhận:** {selected_email['Ngày nhận']}")
            
            # Kiểm tra nếu đã giao rồi thì cảnh báo
            if selected_email['Trạng thái'] == 'Đã giao':
                st.success("✅ Email này đã được bàn giao và tạo công trình trên hệ thống. Không thể giao trùng.")
            else:
                st.markdown("#### ⚡ Giao nhiệm vụ & Khởi tạo Dự án")
                
                # Truy vấn danh sách nhân sự từ bảng profiles để lấy đúng UUID
                profiles_res = supabase.table('profiles').select('id, full_name').execute()
                profiles_list = profiles_res.data if profiles_res.data else []
                profile_dict = {p['full_name']: p['id'] for p in profiles_list}
                
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
                    
                    # Chọn nhân viên và lấy đúng UUID
                    staff_name = st.selectbox("Giao cho nhân viên phụ trách", list(profile_dict.keys()) if profile_dict else ["Chưa phân nhân sự"])
                    assigned_to_uuid = profile_dict.get(staff_name)

                    status = st.selectbox("Trạng thái công trình", ["Đang thực hiện", "Đã hoàn thành", "Tạm dừng"])
                    request_content = st.text_area("Nội dung yêu cầu chi tiết", value=selected_email['Tiêu đề'])
                    
                    submitted = st.form_submit_button("🚀 Xác nhận & Khởi tạo Công trình", type="primary", width='stretch')
                    
                    if submitted:
                        if not customer_name:
                            st.warning("⚠️ Vui lòng nhập Tên khách hàng!")
                        else:
                            result = create_project_directly_from_email(
                                email_id=selected_email['ID'],
                                customer_name=customer_name,
                                project_name=project_name,
                                project_code=project_code,
                                category_id=category_id,
                                assigned_to_uuid=assigned_to_uuid,
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

import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📥 Tiếp nhận & Xử lý Email Công trình")

# 1. Bộ lọc trạng thái email
col_f1, col_f2 = st.columns([3, 1])
with col_f1:
    search_email = st.text_input("🔍 Tìm kiếm email (Tiêu đề, người gửi)...", placeholder="Nhập từ khóa...")
with col_f2:
    status_filter = st.selectbox("Trạng thái xử lý", ["Tất cả", "Chưa xử lý", "Đã giao", "Đang xử lý"])

# 2. Truy vấn danh sách email từ CSDL Supabase
try:
    query = supabase.table('emails').select('*').order('received_at', desc=True)
    if status_filter != "Tất cả":
        query = query.eq('processing_status', status_filter)
    
    res = query.execute()
    emails_data = res.data if res.data else []
except Exception as e:
    st.error(f"❌ Lỗi tải danh sách email: {e}")
    emails_data = []

if emails_data:
    df_emails = pd.DataFrame(emails_data)
    
    # Làm sạch dữ liệu hiển thị
    df_emails['sender_email'] = df_emails.get('sender_email', '').fillna("Chưa rõ")
    df_emails['subject'] = df_emails.get('subject', 'Không có tiêu đề').fillna("Không có tiêu đề")
    df_emails['received_at'] = df_emails.get('received_at', '').fillna("Chưa cập nhật")
    df_emails['processing_status'] = df_emails.get('processing_status', 'Chưa xử lý').fillna("Chưa xử lý")

    # Lọc theo từ khóa tìm kiếm
    if search_email:
        kw = search_email.lower()
        df_emails = df_emails[
            df_emails['subject'].astype(str).str.lower().str.contains(kw, na=False) |
            df_emails['sender_email'].astype(str).str.lower().str.contains(kw, na=False)
        ]

    st.markdown(f"### 📋 Danh sách Email ({len(df_emails)} bản ghi) - Chọn email để khởi tạo công trình")

    # Chuẩn hóa bảng hiển thị
    display_email_df = df_emails[[
        "id", "sender_email", "subject", "received_at", "processing_status"
    ]].rename(columns={
        "id": "ID",
        "sender_email": "Người gửi",
        "subject": "Tiêu đề email",
        "received_at": "Thời gian nhận",
        "processing_status": "Trạng thái"
    })

    # Hiển thị bảng tương tác
    event = st.dataframe(
        display_email_df,
        width='stretch',
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # 3. Khu vực xử lý chi tiết & Khởi tạo công trình khi chọn 1 email
    selected_rows = event.selection.rows
    if selected_rows:
        selected_index = selected_rows[0]
        selected_email = df_emails.iloc[selected_index]
        
        st.divider()
        st.markdown(f"### 🚀 Khởi tạo Công trình từ Email: `{selected_email['subject']}`")
        
        # Lấy danh mục dự án từ bảng categories
        try:
            cat_res = supabase.table('categories').select('id, category_name').execute()
            categories = cat_res.data if cat_res.data else []
            cat_dict = {c['category_name']: c['id'] for c in categories}
        except Exception:
            cat_dict = {}

        with st.form(f"form_init_project_{selected_email['id']}"):
            col1, col2 = st.columns(2)
            with col1:
                customer_name = st.text_input("Tên khách hàng", value=selected_email.get('sender_email', ''))
                project_name = st.text_input("Tên công trình", value=selected_email.get('subject', ''))
            with col2:
                project_code = st.text_input("Mã công trình (VD: CT-2026-001)", value="")
                category_name = st.selectbox("Danh mục dự án", list(cat_dict.keys()) if cat_dict else ["Mặc định"])
                category_id = cat_dict.get(category_name)

            col3, col4 = st.columns(2)
            with col3:
                received_date = st.text_input("Ngày nhận", value=str(selected_email.get('received_at', ''))[:10])
            with col4:
                due_date = st.date_input("Ngày đến hạn hoàn thành")

            # Danh sách nhân sự chuẩn xác khớp tuyệt đối với hệ thống
            staff_options = ["Chưa phân nhân sự", "Ms Hân", "Mr Thái", "Mr Thịnh", "Ms Hương", "Ms Hiếu"]
            staff_name = st.selectbox("Giao cho nhân viên phụ trách", staff_options)

            status = st.selectbox("Trạng thái công trình", ["Đang thực hiện", "Đã hoàn thành", "Tạm dừng"])
            request_content = st.text_area("Nội dung yêu cầu chi tiết", value=selected_email.get('subject', ''))

            submitted = st.form_submit_button("🚀 Xác nhận & Khởi tạo Công trình", type="primary", use_container_width=True)

            if submitted:
                if not customer_name:
                    st.warning("⚠️ Vui lòng nhập Tên khách hàng!")
                else:
                    # Gọi hàm service tạo công trình trực tiếp lưu thẳng tên nhân sự dạng text
                    from services.project_service import create_project_directly_from_email
                    
                    result = create_project_directly_from_email(
                        email_id=selected_email['id'],
                        customer_name=customer_name,
                        project_name=project_name,
                        project_code=project_code,
                        category_id=category_id,
                        assigned_to_uuid=staff_name if staff_name != "Chưa phân nhân sự" else None,
                        received_date=received_date,
                        due_date=str(due_date),
                        request_content=request_content,
                        status=status
                    )

                    if result["success"]:
                        st.success(result["message"])
                        if result.get("project_id"):
                            st.info(f"🔑 ID Công trình: `{result['project_id']}`")
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(result["message"])
else:
    st.info("📭 Không có email nào trong hệ thống.")

import streamlit as st
from services.admin_service import log_system_action

st.title("✉️ Cấu hình Kết nối & Đồng bộ Gmail")

has_gmail_user = "GMAIL_USER" in st.secrets or "GMAIL_ADDRESS" in st.secrets
has_gmail_pass = "GMAIL_APP_PASSWORD" in st.secrets or "GOOGLE_CREDENTIALS" in st.secrets

c1, c2 = st.columns(2)
c1.metric("🔌 Trạng thái Tài khoản Gmail", "Đã cấu hình Secrets" if has_gmail_user else "Cấu hình qua Giao diện")
c2.metric("🔑 Xác thực App Password / OAuth", "Sẵn sàng" if has_gmail_pass else "Đang dùng chế độ Webhook / Thủ công")

st.divider()

with st.form("gmail_config_form"):
    st.subheader("⚙️ Thiết lập Thông số Thu thập Email Công trình")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        gmail_account = st.text_input(
            "Địa chỉ Gmail tiếp nhận yêu cầu",
            value=st.session_state.get("cfg_gmail_account", "tiepnhan.congtrinh@gmail.com"),
        )
        imap_server = st.text_input("Máy chủ IMAP", value="imap.gmail.com")
    with col_g2:
        sync_interval = st.selectbox("Chu kỳ quét tự động", ["5 phút/lần", "15 phút/lần", "30 phút/lần", "Chỉ quét khi bấm nút"])
        filter_label = st.text_input("Nhãn (Label) hoặc Từ khóa lọc tiêu đề", value="PHỐI MÀU, CÔNG TRÌNH, Fwd:, v252, f343")

    auto_attachment = st.checkbox("Tự động tải và lưu đường dẫn file đính kèm vào bảng `email_attachments`", value=True)

    if st.form_submit_button("💾 Lưu Cấu hình Gmail", type="primary", width="stretch"):
        st.session_state["cfg_gmail_account"] = gmail_account
        log_system_action(
            "UPDATE_GMAIL_CONFIG",
            "system_config",
            details={"gmail_account": gmail_account, "sync_interval": sync_interval, "filter": filter_label},
        )
        st.success("✅ Đã lưu thông số cấu hình Gmail và ghi nhận vào Nhật ký hệ thống!")

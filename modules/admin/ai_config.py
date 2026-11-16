import streamlit as st
from services.admin_service import log_system_action

st.title("🤖 Cấu hình Trí tuệ Nhân tạo (AI Extraction & Auto-Routing)")

has_gemini = "GEMINI_API_KEY" in st.secrets or "GOOGLE_API_KEY" in st.secrets
has_openai = "OPENAI_API_KEY" in st.secrets

k1, k2, k3 = st.columns(3)
k1.metric("🧠 Mô hình AI Đang kích hoạt", "Gemini 2.5 Flash" if has_gemini else ("GPT-4o-mini" if has_openai else "Smart Heuristic Engine"))
k2.metric("🎯 Ngưỡng tự động duyệt (Confidence)", f"{st.session_state.get('cfg_ai_threshold', 80)}%")
k3.metric("⚡ Trạng thái Pipeline", "Đang hoạt động")

st.divider()

with st.form("ai_config_form"):
    st.subheader("🛠️ Tinh chỉnh Tham số Bóc tách & Điều phối Công trình")
    c1, c2 = st.columns(2)
    with c1:
        ai_model = st.selectbox(
            "Lựa chọn Mô hình Ngôn ngữ (LLM)",
            ["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4o-mini", "Smart Rule-based Extractor"],
        )
        confidence_threshold = st.slider(
            "Ngưỡng độ tin cậy tối thiểu để gợi ý ghép nối (%)",
            min_value=50,
            max_value=95,
            value=st.session_state.get("cfg_ai_threshold", 80),
            step=5,
        )
    with c2:
        auto_assign_mode = st.selectbox(
            "Chế độ gợi ý phân công nhân sự",
            ["Cân bằng tải tự động (Workload Balancing)", "Theo khách hàng quen thuộc", "Để trống chờ Quản lý phân công"],
        )
        extract_fields = st.multiselect(
            "Các trường thông tin bắt buộc AI bóc tách",
            ["customer_name", "project_name", "project_code", "brand", "project_address", "request_content"],
            default=["customer_name", "project_name", "project_code", "request_content"],
        )

    system_prompt = st.text_area(
        "System Prompt hướng dẫn AI bóc tách Email công trình:",
        value=(
            "Bạn là trợ lý điều phối công trình xây dựng và phối màu sơn. "
            "Hãy trích xuất chính xác Tên khách hàng (Anh/Chị/Đại lý), Tên công trình, Mã số (VD: v252, f343, z263) "
            "và yêu cầu chi tiết từ tiêu đề và nội dung email trả về định dạng JSON chuẩn."
        ),
        height=120,
    )

    if st.form_submit_button("💾 Lưu Cấu hình AI", type="primary", width="stretch"):
        st.session_state["cfg_ai_threshold"] = confidence_threshold
        log_system_action(
            "UPDATE_AI_CONFIG",
            "system_config",
            details={"model": ai_model, "threshold": confidence_threshold, "mode": auto_assign_mode},
        )
        st.success("✅ Đã cập nhật cấu hình AI thành công!")

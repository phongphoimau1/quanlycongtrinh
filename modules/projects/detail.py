import streamlit as st
from services.project_service import get_project_by_code, update_project_status
from supabase import create_client
import time

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🔎 Chi tiết Công trình")

# 1. Lấy mã công trình từ Session State an toàn
project_code = st.session_state.get("selected_project_code")

# Fallback dự phòng nếu người dùng bấm trực tiếp vào trang chi tiết mà chưa chọn từ danh sách
if not project_code:
    st.warning("⚠️ Chưa chọn công trình cụ thể. Vui lòng chọn công trình từ danh sách hoặc nhập mã bên dưới để tra cứu:")
    input_code = st.text_input("Nhập Mã công trình (Project Code):")
    if input_code:
        project_code = input_code
        st.session_state["selected_project_code"] = input_code
        st.rerun()

if project_code:
    # 2. Lấy dữ liệu công trình từ DB chuẩn xác
    project = get_project_by_code(project_code)
    
    if not project:
        st.error(f"❌ Không tìm thấy dữ liệu cho mã công trình: `{project_code}`")
        if st.button("⬅️ Trở về danh sách"):
            st.session_state["selected_project_code"] = None
            st.switch_page("modules/projects/view.py")
    else:
        # Lấy ID công trình để phục vụ cập nhật trạng thái
        project_id = project.get('id')
        
        # 3. Hiển thị UI chia 2 cột chuẩn Enterprise
        col_info, col_action = st.columns([6, 4])
        
        with col_info:
            st.subheader("📋 Thông tin chung")
            st.write(f"**Mã CT:** {project.get('project_code', 'Chưa có mã')}")
            st.write(f"**Tên công trình:** {project.get('project_name', 'Chưa đặt tên')}")
            st.write(f"**Khách hàng:** {project.get('customer_name', 'Chưa cập nhật')}")
            st.write(f"**Thương hiệu:** {project.get('brand', 'Không có')}")
            st.write(f"**Ngày nhận:** {project.get('received_date', 'Chưa xác định')}")
            st.write(f"**Ngày hoàn thành dự kiến:** {project.get('completed_date', 'Chưa xác định')}")
            st.markdown("---")
            st.write(f"**📝 Nội dung yêu cầu:**")
            st.info(project.get('request_content', 'Không có nội dung yêu cầu chi tiết.'))
            
        with col_action:
            st.subheader("⏳ Quản lý Tiến độ")
            current_status = project.get('status', 'Mới tiếp nhận')
            st.write(f"Trạng thái hiện tại: **{current_status}**")
            
            status_options = ["Mới tiếp nhận", "Đang thực hiện", "Chờ bổ sung", "Hoàn thành", "Đã hủy"]
            try:
                default_idx = status_options.index(current_status)
            except ValueError:
                default_idx = 0
                
            new_status = st.selectbox("Cập nhật trạng thái mới:", status_options, index=default_idx)
            
            if st.button("💾 Lưu thay đổi trạng thái", type="primary", width='stretch'):
                if new_status == current_status:
                    st.info("ℹ️ Trạng thái không thay đổi.")
                else:
                    with st.spinner("Đang cập nhật CSDL..."):
                        try:
                            # Gọi service cập nhật
                            update_project_status(project.get('id'), new_status)
                            
                            st.success(f"✅ Đã cập nhật thành công sang: **{new_status}**!")
                            st.balloons()
                            time.sleep(1)
                            st.cache_data.clear()
                            st.rerun() # Làm mới lại trang ngay lập tức
                        except Exception as update_err:
                            st.error(f"❌ {str(update_err)}")
                            
                            # Ghi log lịch sử thay đổi (Chặn lỗi nếu bảng lịch sử chưa sẵn sàng)
                            try:
                                supabase.table('project_status_history').insert({
                                    "project_id": project_id,
                                    "old_status": current_status,
                                    "new_status": new_status,
                                    "note": "Cập nhật từ trang chi tiết công trình"
                                }).execute()
                            except Exception:
                                pass

                            st.success(f"✅ Đã cập nhật thành công sang: **{new_status}**!")
                            st.balloons()
                            time.sleep(1)
                            st.cache_data.clear()
                            st.rerun() # Làm mới lại trang
                        except Exception as update_err:
                            st.error(f"❌ Lỗi cập nhật: {str(update_err)}")
                            
        st.write("---")
        if st.button("⬅️ Trở về danh sách công trình"):
            st.session_state["selected_project_code"] = None 
            st.switch_page("modules/projects/view.py")
else:
    if st.button("⬅️ Trở về danh sách"):
        st.switch_page("modules/projects/view.py")

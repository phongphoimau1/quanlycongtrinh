import os
import json
import google.generativeai as genai
from supabase import create_client, Client
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# --- KHÓA CHẶT VÀO MODEL FLASH MIỄN PHÍ AN TOÀN 100% ---
# Tuyệt đối không quét bừa bãi để tránh vớ phải các model Pro/Research bị tính phí hoặc giới hạn ngặt nghèo.
TARGET_MODEL_NAME = 'gemini-1.5-flash'

print(f"🚀 Hệ thống sử dụng model miễn phí: {TARGET_MODEL_NAME}")
model = genai.GenerativeModel(TARGET_MODEL_NAME)
# -----------------------------------------------------

def process_email_with_ai(email_id: str, subject: str, sender: str, content: str = "") -> dict:
    try:
        prompt = f"""
        Bạn là một Trợ lý Kiến trúc sư trưởng xuất sắc. Nhiệm vụ của bạn là đọc email yêu cầu của khách hàng 
        và bóc tách các thông tin cốt lõi để tạo Dự án thi công/phối màu.
        
        THÔNG TIN EMAIL:
        - Tiêu đề: {subject}
        - Người gửi: {sender}
        - Nội dung: {content if content else subject}

        YÊU CẦU BẮT BUỘC: 
        Trả về DUY NHẤT một chuỗi JSON chuẩn xác (không markdown, không text thừa) theo cấu trúc:
        {{
            "customer_name": "Tên khách hàng hoặc null",
            "customer_phone": "Số điện thoại hoặc null",
            "project_address": "Địa chỉ hoặc null",
            "project_type": "Phân loại (Nhà phố, Biệt thự... hoặc Chưa rõ)",
            "detailed_requirements": "Tóm tắt yêu cầu chi tiết",
            "confidence_score": 0.95
        }}
        """

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json")
        )
        
        ai_data = json.loads(response.text)
        confidence = float(ai_data.pop("confidence_score", 0.5))

        # Đẩy dữ liệu vào Database như cũ
        supabase.table('ai_extractions').insert({
            "email_id": email_id,
            "extracted_data": ai_data,
            "confidence": confidence,
            "decision": "pending"
        }).execute()
        
        supabase.table('confirmation_queue').insert({
            "email_id": email_id,
            "status": "Chờ duyệt",
            "decision": "pending",
        }).execute()

        supabase.table('emails').update({
            "processing_status": "Chờ duyệt AI"
        }).eq("id", email_id).execute()

        return {
            "success": True, 
            "message": "AI đã bóc tách thành công!", 
            "data": ai_data, 
            "confidence": confidence
        }

    except Exception as e:
        error_msg = f"Lỗi xử lý AI: {str(e)}"
        print(error_msg)
        return {"success": False, "message": error_msg}
    """
    Hàm lõi IQ 2000: Đọc email, gọi AI bóc tách, và phân phối vào 3 bảng Database.
    """
    try:
        # ==========================================
        # BƯỚC 1: ÉP KHUÔN AI (PROMPT ENGINEERING)
        # ==========================================
        prompt = f"""
        Bạn là một Trợ lý Kiến trúc sư trưởng xuất sắc. Nhiệm vụ của bạn là đọc email yêu cầu của khách hàng 
        và bóc tách các thông tin cốt lõi để tạo Dự án thi công/phối màu.
        
        THÔNG TIN EMAIL:
        - Tiêu đề: {subject}
        - Người gửi: {sender}
        - Nội dung: {content if content else subject} (Nếu không có nội dung, hãy tự suy luận từ tiêu đề)

        YÊU CẦU BẮT BUỘC: 
        Trả về DUY NHẤT một chuỗi JSON chuẩn xác (không có markdown, không có text thừa) theo đúng cấu trúc sau:
        {{
            "customer_name": "Tên khách hàng (Nếu không thấy, trả về null)",
            "customer_phone": "Số điện thoại (Nếu không thấy, trả về null)",
            "project_address": "Địa chỉ thi công/phối màu (Nếu không thấy, trả về null)",
            "project_type": "Phân loại (VD: Nhà phố, Biệt thự, Quán Cafe, Nhà ống... Mặc định: Chưa rõ)",
            "detailed_requirements": "Tóm tắt yêu cầu chi tiết của khách hàng (Màu sắc, phong thủy, kích thước...)",
            "confidence_score": 0.95 (Thang điểm từ 0.0 đến 1.0 đánh giá mức độ tự tin của bạn vào việc bóc tách này)
        }}
        """

        # Bắt buộc AI nhả JSON (Tính năng siêu việt của Gemini)
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json")
        )
        
        # Parse chuỗi JSON AI trả về
        ai_data = json.loads(response.text)
        confidence = float(ai_data.pop("confidence_score", 0.5)) # Tách điểm tự tin ra khỏi cục data

        # ==========================================
        # BƯỚC 2: RẢI THẢM DỮ LIỆU VÀO DATABASE
        # ==========================================
        
        # 2.1. Đẩy vào kho chứa kết quả AI (AI_EXTRACTIONS)
        ai_ext_res = supabase.table('ai_extractions').insert({
            "email_id": email_id,
            "extracted_data": ai_data,
            "confidence": confidence,
            "decision": "pending"
        }).execute()
        
        # 2.2. Đẩy vào hàng đợi chờ con người duyệt (CONFIRMATION_QUEUE)
        supabase.table('confirmation_queue').insert({
            "email_id": email_id,
            "status": "Chờ duyệt",
            "decision": "pending",
            # candidate_project_id: Chưa tạo nên để null
        }).execute()

        # 2.3. Cập nhật trạng thái email gốc
        supabase.table('emails').update({
            "processing_status": "Chờ duyệt AI"
        }).eq("id", email_id).execute()

        return {
            "success": True, 
            "message": "AI đã bóc tách thành công!", 
            "data": ai_data, 
            "confidence": confidence
        }

    except Exception as e:
        # Bắt lỗi chuẩn kỹ sư: Không crash app, chỉ ghi nhận lỗi
        error_msg = f"Lỗi xử lý AI: {str(e)}"
        print(error_msg)
        return {"success": False, "message": error_msg}

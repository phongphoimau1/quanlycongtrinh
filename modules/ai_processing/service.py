import os
import json
import concurrent.futures
import google.generativeai as genai
from supabase import create_client, Client
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel('gemini-3.8-flash')

def _call_gemini_with_timeout(prompt):
    """Hàm phụ trợ gọi AI bên trong một luồng độc lập để chống treo mạng"""
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=400
        )
    )
    return response.text

def process_email_with_ai(email_id: str, subject: str, sender: str, content: str = "") -> dict:
    try:
        prompt = f"""
        Đọc tiêu đề email và trích xuất JSON:
        - Tiêu đề: {subject}
        - Người gửi: {sender}
        
        Trả về DUY NHẤT chuỗi JSON chuẩn xác:
        {{
            "customer_name": "Tên khách hàng hoặc null",
            "customer_phone": "Số điện thoại hoặc null",
            "project_address": "Địa chỉ hoặc null",
            "project_type": "Nhà phố / Biệt thự / Chưa rõ",
            "detailed_requirements": "Yêu cầu tóm tắt",
            "confidence_score": 0.95
        }}
        """

        # 🛡️ DÙNG THREAD POOL ĐỂ ÉP TIMEOUT 8 GIÂY (Chống treo vĩnh viễn)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_gemini_with_timeout, prompt)
            try:
                # Nếu sau 8 giây Google không trả lời -> Cưỡng chế ngắt
                response_text = future.result(timeout=8.0) 
            except concurrent.futures.TimeoutError:
                return {
                    "success": False, 
                    "message": "⏱️ Quá thời gian chờ phản hồi từ Google AI (Timeout > 8s). Đường truyền mạng từ máy chủ Cloud đang bị nghẽn."
                }

        if not response_text:
            return {"success": False, "message": "Google Gemini trả về phản hồi rỗng."}

        ai_data = json.loads(response_text)
        confidence = float(ai_data.pop("confidence_score", 0.5))

        # Ghi nhận vào Database Supabase
        supabase.table('ai_extractions').insert({
            "email_id": email_id, 
            "extracted_data": ai_data, 
            "confidence": confidence, 
            "decision": "pending"
        }).execute()
        
        supabase.table('confirmation_queue').insert({
            "email_id": email_id, 
            "status": "Chờ duyệt", 
            "decision": "pending"
        }).execute()

        supabase.table('emails').update({
            "processing_status": "Chờ duyệt AI"
        }).eq("id", email_id).execute()

        return {
            "success": True, 
            "message": "Bóc tách tốc độ cao thành công!", 
            "data": ai_data, 
            "confidence": confidence
        }

    except Exception as e:
        error_msg = f"Lỗi hệ thống: {str(e)}"
        print(error_msg)
        return {"success": False, "message": error_msg}

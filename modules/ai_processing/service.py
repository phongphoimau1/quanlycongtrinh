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

# ⚡ GHIM THẲNG VÀO MODEL CHUẨN XÁC MÀ GOOGLE KHUYẾN CÁO TRONG LỖI
model = genai.GenerativeModel('gemini-3.8-flash')

def process_email_with_ai(email_id: str, subject: str, sender: str, content: str = "") -> dict:
    try:
        prompt = f"""
        Đọc tiêu đề email sau và trích xuất JSON:
        - Tiêu đề: {subject}
        - Người gửi: {sender}
        
        Trả về DUY NHẤT một chuỗi JSON chuẩn xác theo cấu trúc:
        {{
            "customer_name": "Tên khách hàng hoặc null",
            "customer_phone": "Số điện thoại hoặc null",
            "project_address": "Địa chỉ hoặc null",
            "project_type": "Nhà phố / Biệt thự / Chưa rõ",
            "detailed_requirements": "Yêu cầu tóm tắt",
            "confidence_score": 0.95
        }}
        """

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json")
        )
        
        ai_data = json.loads(response.text)
        confidence = float(ai_data.pop("confidence_score", 0.5))

        # Lưu Database
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
            "message": "AI đã bóc tách thành công!", 
            "data": ai_data, 
            "confidence": confidence
        }

    except Exception as e:
        error_msg = f"Lỗi xử lý AI: {str(e)}"
        print(error_msg)
        return {"success": False, "message": error_msg}

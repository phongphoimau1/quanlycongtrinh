import os
import json
from google import genai
from google.genai import types
from supabase import create_client, Client
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

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

        # Model chuẩn duy nhất được Google cho phép trên Free Tier hiện tại
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=400
            ),
        )
        
        if not response or not response.text:
            return {"success": False, "message": "Google Gemini trả về phản hồi rỗng."}

        ai_data = json.loads(response.text)
        confidence = float(ai_data.pop("confidence_score", 0.5))

        # Ghi dữ liệu xuống Supabase
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
            "message": "Bóc tách siêu tốc thành công!", 
            "data": ai_data, 
            "confidence": confidence
        }

    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            error_msg = "⚠️ Đã vượt quá hạn mức miễn phí (20 lần/ngày) của model gemini-3.8-flash. Vui lòng tạo API Key mới trên Google AI Studio hoặc chờ reset sau vài giờ."
        else:
            error_msg = f"Lỗi hệ thống GenAI: {err_str}"
            
        print(error_msg)
        return {"success": False, "message": error_msg}

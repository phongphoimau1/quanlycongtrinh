import os
import json
import time
import google.generativeai as genai
from supabase import create_client, Client
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel('gemini-3.8-flash')

def process_email_with_ai(email_id: str, subject: str, sender: str, content: str = "") -> dict:
    start_time = time.time()
    print(f"\n[TELEMETRY] ⏱️ Bắt đầu xử lý email ID: {email_id} lúc {time.strftime('%H:%M:%S')}")
    
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

        # BƯỚC 1: Đo lường thời gian gọi AI
        t1 = time.time()
        print("[TELEMETRY] 🤖 Đang gửi request tới Google Gemini...")
        
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=400
            )
        )
        print(f"[TELEMETRY] ✅ Gemini phản hồi xong sau {time.time() - t1:.2f} giây.")

        # BƯỚC 2: Parse JSON
        t2 = time.time()
        ai_data = json.loads(response.text)
        confidence = float(ai_data.pop("confidence_score", 0.5))
        print(f"[TELEMETRY] ✅ Parse JSON xong sau {time.time() - t2:.2f} giây.")

        # BƯỚC 3: Đo lường thời gian ghi Database Supabase
        t3 = time.time()
        print("[TELEMETRY] 💾 Đang ghi dữ liệu xuống Supabase...")
        
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
        
        print(f"[TELEMETRY] ✅ Ghi Supabase xong sau {time.time() - t3:.2f} giây.")
        print(f"[TELEMETRY] 🚀 Tổng thời gian hoàn thành: {time.time() - start_time:.2f} giây.\n")

        return {
            "success": True, 
            "message": "Bóc tách thành công!", 
            "data": ai_data, 
            "confidence": confidence
        }

    except Exception as e:
        print(f"[TELEMETRY ERROR] ❌ Treo/Lỗi tại giây thứ {time.time() - start_time:.2f}: {str(e)}")
        return {"success": False, "message": f"Lỗi hệ thống: {str(e)}"}

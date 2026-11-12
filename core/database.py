import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    try:
        # Bắt buộc phải dùng đúng tên key đã khai báo trong khung Secrets
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except KeyError:
        raise ValueError("Chưa thiết lập SUPABASE_URL hoặc SUPABASE_KEY trong phần cài đặt Secrets của Streamlit.")
        
    return create_client(url, key)

supabase = get_supabase_client()

import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    # Sử dụng st.secrets chuyên dụng cho Streamlit Cloud thay vì os.environ
    try:
        url = st.secrets["https://nhwlsysypdtzrxgavfzh.supabase.co"]
        key = st.secrets["sb_publishable_sUuay5FTqW97qv23ioVB2g_ANb7j5-O"]
    except KeyError:
        raise ValueError("Chưa thiết lập SUPABASE_URL hoặc SUPABASE_KEY trong phần cài đặt Secrets của Streamlit.")
        
    return create_client(url, key)

supabase = get_supabase_client()

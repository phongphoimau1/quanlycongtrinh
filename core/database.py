import os
from supabase import create_client, Client
import streamlit as st

@st.cache_resource
def get_supabase_client() -> Client:
    url = os.environ.get("https://nhwlsysypdtzrxgavfzh.supabase.co")
    key = os.environ.get("sb_publishable_sUuay5FTqW97qv23ioVB2g_ANb7j5-O")
    if not url or not key:
        raise ValueError("Thiếu cấu hình Supabase trong Secrets")
    return create_client(url, key)

supabase = get_supabase_client()

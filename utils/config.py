import os
import streamlit as st

def setup_config():
    """Configure l'application Streamlit"""
    st.set_page_config(
        page_title="Simandou-GN-IA",
        page_icon="🏔️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def get_api_key():
    """Récupère la clé API Google"""
    return os.getenv("GOOGLE_API_KEY")

def get_db_config():
    """Récupère la configuration de la base de données"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'simandou_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
        'port': os.getenv('DB_PORT', '5432')
    }

def get_max_free_requests():
    """Récupère le nombre maximum de requêtes gratuites"""
    return int(os.getenv('MAX_FREE_REQUESTS', 15))
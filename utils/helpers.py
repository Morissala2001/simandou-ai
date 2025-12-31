import streamlit as st


def load_css():
    """Version simplifiée - Sidebar toujours accessible"""
    css = """
    <style>
        :root {
            --primary-color: #009460;
            --primary-hover: #007a4d;
            --sidebar-width: 350px;
        }

        /* Bandeau drapeau */
        .stApp::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 6px;
            background: linear-gradient(90deg, 
                #CE1126 0%, #CE1126 33.3%, 
                #FCD116 33.3%, #FCD116 66.6%, 
                #009460 66.6%, #009460 100%);
            z-index: 999999;
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        /* Sidebar - NE JAMAIS LA CACHER COMPLÈTEMENT */
        [data-testid="stSidebar"] {
            background-color: #f8f8f8;
            width: var(--sidebar-width) !important;
            min-width: 280px !important;
            transition: width 0.3s ease;
        }

        /* Quand sidebar réduite, on garde juste le bouton */
        [data-testid="stSidebar"][aria-expanded="false"] {
            width: 60px !important;
            min-width: 60px !important;
        }

        /* Cacher le contenu mais pas le bouton hamburger */
        [data-testid="stSidebar"][aria-expanded="false"] > div:first-child > div:not(:first-child) {
            opacity: 0;
            pointer-events: none;
        }

        /* Garder le bouton hamburger visible */
        [data-testid="stSidebar"] button[kind="header"] {
            margin: 10px auto !important;
            display: block !important;
        }

        /* Ajuster le contenu quand sidebar réduite */
        [data-testid="stSidebar"][aria-expanded="false"] ~ .main .block-container {
            margin-left: 60px !important;
            transition: margin-left 0.3s ease;
        }

        .main .block-container {
            max-width: 950px !important;
            margin: 0 auto !important;
            padding: 2rem 1rem !important;
        }

        /* Boutons principaux */
        .stButton > button {
            background-color: #009460;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: all 0.2s ease-in-out;
        }

        .stButton > button:hover {
            background-color: var(--primary-hover);
            transform: translateY(-2px);
        }

        /* Boutons spécifiques dans la sidebar - Couleur grise avec effet de survol */
        [data-testid="stSidebar"] .stButton > button {
            background-color: transparent; 
            color: #4a4a4a; 
            border: none;
            text-align: left;
            padding: 5px 10px;
            margin-bottom: 5px;
            width: 100%;
            border-radius: 4px;
            font-weight: 400; 
            transition: background-color 0.2s;
        }

        [data-testid="stSidebar"] .stButton > button:hover {
            background-color: #e6e6e6; 
            color: #1f2937;
            box-shadow: none;
            transform: none;
        }

        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        .stDeployButton { display: none; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
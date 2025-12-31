import streamlit as st


def load_css():
    """Charge les styles CSS compatibles multi-appareils"""
    css = """
    <style>
        /* Reset de compatibilité */
        :root {
            --primary-color: #009460;
            --primary-hover: #007a4d;
            --text-color: #1f2937;
            --sidebar-width: 350px;
            --content-max-width: 950px;
            --mobile-breakpoint: 768px;
        }

        /* Header transparent */
        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        /* Bandeau supérieur avec drapeau */
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

        /* Système de polices universel */
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 
                         "Helvetica Neue", Arial, "Noto Sans", sans-serif, 
                         "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", 
                         "Noto Color Emoji";
            font-size: 16px;
            color: var(--text-color);
            font-weight: 400;
            line-height: 1.5;
        }

        /* Responsive typography */
        @media (max-width: 768px) {
            html, body, [class*="css"] {
                font-size: 14px;
            }

            h1 { font-size: 1.8rem; }
            h2 { font-size: 1.5rem; }
            h3 { font-size: 1.25rem; }
        }

        /* Titres responsives */
        h1, h2, h3 {
            color: var(--text-color);
            font-weight: 600;
            line-height: 1.2;
        }

        /* Sidebar responsive avec état fermé/ouvert */
        [data-testid="stSidebar"] {
            background-color: #f8f8f8;
            min-width: 280px !important;
            max-width: 400px !important;
            width: var(--sidebar-width) !important;
            transition: all 0.3s ease;
        }

        /* Style pour desktop */
        @media (min-width: 769px) {
            /* Quand sidebar est ouverte sur desktop */
            [data-testid="stSidebar"][aria-expanded="true"] {
                transform: translateX(0);
            }

            /* Quand sidebar est fermée sur desktop */
            [data-testid="stSidebar"][aria-expanded="false"] {
                transform: translateX(-100%);
                width: 0 !important;
                min-width: 0 !important;
                max-width: 0 !important;
                padding: 0 !important;
                margin: 0 !important;
                border: none !important;
            }
        }

        /* Style pour mobile */
        @media (max-width: 768px) {
            [data-testid="stSidebar"] {
                width: 85% !important;
                max-width: 400px !important;
                position: fixed !important;
                height: 100vh;
                z-index: 999999;
                top: 0;
                left: 0;
                box-shadow: 4px 0 20px rgba(0, 0, 0, 0.15);
            }

            /* Cacher la sidebar par défaut sur mobile */
            [data-testid="stSidebar"][aria-expanded="false"] {
                transform: translateX(-100%);
                visibility: hidden;
            }

            [data-testid="stSidebar"][aria-expanded="true"] {
                transform: translateX(0);
                visibility: visible;
            }

            /* Overlay semi-transparent quand sidebar ouverte */
            [data-testid="stSidebar"][aria-expanded="true"]::before {
                content: "";
                position: fixed;
                top: 0;
                left: 85%;
                right: 0;
                bottom: 0;
                background-color: rgba(0, 0, 0, 0.4);
                z-index: -1;
            }
        }

        /* Conteneur principal responsive qui s'adapte à 100% quand sidebar fermée */
        .main .block-container {
            max-width: var(--content-max-width) !important;
            margin: 0 auto !important;
            padding: 2rem 1rem !important;
            transition: all 0.3s ease;
        }

        /* Desktop: Quand sidebar ouverte */
        @media (min-width: 769px) {
            [data-testid="stSidebar"][aria-expanded="true"] ~ .main .block-container {
                width: calc(100% - var(--sidebar-width)) !important;
                max-width: calc(var(--content-max-width) - 100px) !important;
                margin-left: var(--sidebar-width) !important;
                margin-right: auto !important;
            }

            /* Desktop: Quand sidebar fermée - occupe 100% */
            [data-testid="stSidebar"][aria-expanded="false"] ~ .main .block-container {
                width: 100% !important;
                max-width: var(--content-max-width) !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding-left: 2rem !important;
                padding-right: 2rem !important;
            }
        }

        @media (max-width: 1200px) {
            .main .block-container {
                max-width: 90% !important;
                padding: 1.5rem 1rem !important;
            }
        }

        @media (max-width: 768px) {
            .main .block-container {
                max-width: 100% !important;
                width: 100% !important;
                padding: 1rem 0.75rem !important;
                margin-top: 1rem !important;
                margin-left: 0 !important;
                margin-right: 0 !important;
            }

            /* Mobile: Quand sidebar ouverte, désactiver le contenu */
            [data-testid="stSidebar"][aria-expanded="true"] ~ .main .block-container {
                pointer-events: none;
                user-select: none;
                overflow: hidden;
            }

            /* Mobile: Quand sidebar fermée - occupe 100% normalement */
            [data-testid="stSidebar"][aria-expanded="false"] ~ .main .block-container {
                pointer-events: auto;
                user-select: auto;
            }
        }

        /* Boutons universels */
        .stButton > button {
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.625rem 1.25rem;
            font-weight: 600;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
            min-height: 44px; /* Taille tactile minimum */
            font-size: 1rem;
        }

        .stButton > button:hover, 
        .stButton > button:focus {
            background-color: var(--primary-hover);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transform: translateY(-2px);
            color: white;
            outline: 2px solid var(--primary-hover);
            outline-offset: 2px;
        }

        @media (max-width: 768px) {
            .stButton > button {
                padding: 0.75rem 1rem;
                width: 100%;
                margin: 0.25rem 0;
            }
        }

        /* Boutons sidebar */
        [data-testid="stSidebar"] .stButton > button {
            background-color: transparent;
            color: #4a4a4a;
            border: none;
            text-align: left;
            padding: 0.75rem 1rem;
            margin: 0.25rem 0;
            width: 100%;
            border-radius: 6px;
            font-weight: 500;
            transition: background-color 0.2s;
            min-height: 44px;
        }

        [data-testid="stSidebar"] .stButton > button:hover,
        [data-testid="stSidebar"] .stButton > button:focus {
            background-color: #e6e6e6;
            color: var(--text-color);
            box-shadow: none;
            transform: none;
            outline: 2px solid #e6e6e6;
        }

        /* Messages de chat */
        .stChatMessage {
            padding: 1rem 0;
            border-bottom: 1px solid #e5e7eb;
        }

        @media (max-width: 768px) {
            .stChatMessage {
                padding: 0.75rem 0;
            }
        }

        /* Avatars de chat */
        [data-testid="chatAvatar"] {
            font-size: 1.25rem !important;
            width: 36px !important;
            height: 36px !important;
            line-height: 36px !important;
            border-radius: 50%;
            background-color: #e8f0fe;
        }

        @media (max-width: 768px) {
            [data-testid="chatAvatar"] {
                width: 32px !important;
                height: 32px !important;
                line-height: 32px !important;
                font-size: 1.1rem !important;
            }
        }

        /* Zone de saisie responsive qui s'adapte aussi */
        div[data-testid="stChatInput"] {
            max-width: var(--content-max-width) !important;
            margin: 0 auto !important;
            padding: 1rem 0 !important;
            transition: all 0.3s ease;
        }

        /* Desktop: Quand sidebar ouverte */
        @media (min-width: 769px) {
            [data-testid="stSidebar"][aria-expanded="true"] ~ .main div[data-testid="stChatInput"] {
                width: calc(100% - var(--sidebar-width)) !important;
                max-width: calc(var(--content-max-width) - 100px) !important;
                margin-left: var(--sidebar-width) !important;
                margin-right: auto !important;
            }

            /* Desktop: Quand sidebar fermée - occupe 100% */
            [data-testid="stSidebar"][aria-expanded="false"] ~ .main div[data-testid="stChatInput"] {
                width: 100% !important;
                max-width: var(--content-max-width) !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }
        }

        @media (max-width: 1200px) {
            div[data-testid="stChatInput"] {
                max-width: 90% !important;
            }
        }

        @media (max-width: 768px) {
            div[data-testid="stChatInput"] {
                max-width: 100% !important;
                width: 100% !important;
                padding: 0.75rem 0.5rem !important;
                position: sticky;
                bottom: 0;
                background: white;
                z-index: 100;
                margin-left: 0 !important;
                margin-right: 0 !important;
            }

            /* Cacher la zone de saisie quand sidebar ouverte sur mobile */
            [data-testid="stSidebar"][aria-expanded="true"] ~ .main div[data-testid="stChatInput"] {
                display: none !important;
            }
        }

        div[data-testid="stChatInput"] > div > label + div > div > textarea {
            border-radius: 25px !important;
            border: 1px solid #d1d5db !important;
            padding: 0.75rem 1.25rem !important;
            font-size: 1rem !important;
            font-family: inherit !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
            transition: all 0.2s !important;
            min-height: 56px !important;
            resize: vertical !important;
        }

        div[data-testid="stChatInput"] > div > label + div > div > textarea:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15) !important;
            outline: 2px solid transparent;
        }

        @media (max-width: 768px) {
            div[data-testid="stChatInput"] > div > label + div > div > textarea {
                padding: 0.75rem 1rem !important;
                font-size: 0.95rem !important;
                min-height: 48px !important;
            }
        }

        /* Carte de bienvenue */
        .welcome-card {
            background-color: #f8fafc;
            padding: 2rem;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            text-align: center;
            margin: 1.5rem 0 2rem 0;
        }

        @media (max-width: 768px) {
            .welcome-card {
                padding: 1.5rem 1rem;
                margin: 1rem 0 1.5rem 0;
            }

            .welcome-card h2 {
                font-size: 1.5rem !important;
                margin-bottom: 0.75rem !important;
            }

            .welcome-card p {
                font-size: 1rem !important;
                line-height: 1.6 !important;
            }
        }

        /* Cache les éléments Streamlit par défaut */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        .stDeployButton { display: none; }

        /* Améliorations pour le contraste et l'accessibilité */
        @media (prefers-reduced-motion: reduce) {
            .stButton > button,
            [data-testid="stSidebar"] .stButton > button,
            div[data-testid="stChatInput"] > div > label + div > div > textarea {
                transition: none !important;
            }
        }

        /* Support pour le mode sombre */
        @media (prefers-color-scheme: dark) {
            html, body, [class*="css"] {
                color: #f3f4f6;
            }

            .welcome-card {
                background-color: #1f2937;
                border-color: #374151;
            }

            [data-testid="stSidebar"] {
                background-color: #111827;
            }

            .stChatMessage {
                border-color: #374151;
            }
        }

        /* Correction pour les iframes et contenus externes */
        iframe, video, img {
            max-width: 100% !important;
            height: auto !important;
        }

        /* Amélioration des onglets */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
        }

        @media (max-width: 768px) {
            .stTabs [data-baseweb="tab-list"] {
                flex-wrap: wrap;
                justify-content: center;
            }

            .stTabs [data-baseweb="tab"] {
                padding: 0.5rem 1rem;
                font-size: 0.9rem;
                flex: 1;
                min-width: 120px;
                text-align: center;
            }
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def format_timestamp(timestamp):
    """Formate un timestamp pour l'affichage"""
    from datetime import datetime
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)
    return timestamp.strftime("%d/%m/%Y %H:%M")
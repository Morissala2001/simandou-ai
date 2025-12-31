import streamlit as st
import time
from datetime import datetime
import os

# Importations conditionnelles pour éviter les erreurs sur Streamlit Cloud
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # Sur Streamlit Cloud, on utilise les secrets

# Import des modules
from modules.auth import AuthManager
from modules.database_sqlite import SQLiteDatabase as Database
from modules.chat_handler import ChatHandler
from modules.ui_components import render_sidebar
from modules.archive_manager import ArchiveManager
from modules.request_counter import RequestCounter
from modules.tab_manager import TabManager
from modules.model_manager import ModelManager
from utils.config import setup_config
from utils.helpers import load_css

# ============================================
# CONFIGURATION STREAMLIT CLOUD
# ============================================

# Chemin pour la base de données (adapté pour Streamlit Cloud)
if 'STREAMLIT_DB_PATH' in os.environ:
    DB_PATH = os.environ['STREAMLIT_DB_PATH']
else:
    # Sur Streamlit Cloud, on utilise un chemin dans le répertoire courant
    DB_PATH = os.path.join(os.path.dirname(__file__), "simandou_data.db")

# Configuration API - Utiliser les secrets Streamlit
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    print("Clé API chargée depuis les secrets Streamlit")
except (KeyError, AttributeError):
    # Fallback sur .env ou variables d'environnement
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    print("Clé API chargée depuis les variables d'environnement")

# ============================================
# INITIALISATION
# ============================================

# Configuration initiale
setup_config()

# Charger les styles CSS
load_css()

MAX_FREE_REQUESTS = int(os.getenv('MAX_FREE_REQUESTS', 15))

if not GOOGLE_API_KEY:
    st.warning("⚠️ Clé API manquante. Veuillez configurer votre clé API dans les secrets Streamlit.")
    st.info("Comment configurer :\n1. Allez dans Settings → Secrets\n2. Ajoutez `GOOGLE_API_KEY = 'votre-clé'`")
    st.stop()

# Initialiser le gestionnaire de modèles
try:
    model_manager = ModelManager(GOOGLE_API_KEY)
except Exception as e:
    st.error(f"Erreur d'initialisation du modèle : {str(e)[:200]}")
    st.stop()

# Initialiser les managers avec le chemin adapté
try:
    db = Database()  # Assure-toi que Database accepte un paramètre de chemin
    # Si ta classe Database a besoin du chemin, modifie l'import ou passe-le en paramètre
except Exception as e:
    st.error(f"Erreur d'initialisation de la base de données : {str(e)[:200]}")
    st.stop()

try:
    auth = AuthManager(db, model_manager)
    chat_handler = ChatHandler(model_manager, db)
    archive_manager = ArchiveManager(db, chat_handler)
    request_counter = RequestCounter(db)
    tab_manager = TabManager()
except Exception as e:
    st.error(f"Erreur d'initialisation des modules : {str(e)[:200]}")
    st.stop()


# ============================================
# VALIDATION DE SESSION AVANT TOUT
# ============================================

def validate_and_restore_session():
    """Valide et restaure la session si un token valide existe"""

    # Si déjà connecté dans la session, vérifier la validité
    if st.session_state.get('logged_in'):
        # Utiliser la méthode de validation d'AuthManager si disponible
        if hasattr(auth, 'check_session_validity'):
            if auth.check_session_validity():
                return True
            else:
                # Session invalide, nettoyer
                st.session_state.logged_in = False
                st.session_state.username = None
                if 'auth_token' in st.session_state:
                    del st.session_state.auth_token
                if 'login_time' in st.session_state:
                    del st.session_state.login_time
                return False
        return True  # Si pas de méthode de validation, accepter la session

    # Sinon, vérifier si un token existe pour restaurer la session
    if 'auth_token' in st.session_state and st.session_state.auth_token:
        if 'login_time' in st.session_state:
            # Session valide 4 heures (14400 secondes)
            session_age = time.time() - st.session_state.login_time
            if session_age < 14400:
                st.session_state.logged_in = True
                return True
            else:
                # Token expiré
                st.session_state.auth_token = None
                st.session_state.login_time = None

    return False


# ============================================
# GESTION DE SESSION
# ============================================

# Initialiser les variables de session si elles n'existent pas
session_defaults = {
    "logged_in": False,
    "username": None,
    "current_file": None,
    "viewing_archive_id": None,
    "forgot_state": 0,
    "user_stats": None,
    "active_tab": "💬 Chat",
    "auth_token": None,
    "login_time": None,
    "chat_session": None
}

for key, default in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Valider et restaurer la session avant de continuer
is_session_valid = validate_and_restore_session()

# Initialisation du chat session (seulement si session valide)
if is_session_valid and st.session_state.chat_session is None:
    try:
        default_model = model_manager.get_default_model()
        st.session_state.chat_session = default_model.start_chat(history=[])

        # Charger l'historique si l'utilisateur a un nom
        if st.session_state.username:
            loaded_history = db.load_history(st.session_state.username)
            if loaded_history:
                for msg in loaded_history:
                    if msg['role'] == 'user':
                        st.session_state.chat_session.history.append(
                            chat_handler._create_message_object('user', msg['text'])
                        )
                    elif msg['role'] == 'model':
                        st.session_state.chat_session.history.append(
                            chat_handler._create_message_object('model', msg['text'])
                        )
    except Exception as e:
        st.error(f"Erreur d'initialisation du chat: {str(e)[:100]}")
        # Réinitialiser le chat
        st.session_state.chat_session = None


# ============================================
# FONCTIONS D'INTERFACE
# ============================================

def _render_chat_interface():
    """Affiche l'interface de chat sans informations techniques"""
    #st.title("🤖 Assistant Simandou-gn-ia")

    # Affichage du nom d'utilisateur seulement
    if st.session_state.username:
        st.caption(f"👤 {st.session_state.username}")

    if st.session_state.viewing_archive_id is not None:
        st.info("📖 Consultation d'une ancienne conversation")

    # Message d'accueil
    if st.session_state.chat_session and not st.session_state.chat_session.history:
        st.markdown("""
        <div class="welcome-card">
            <h2 style="margin-bottom: 1rem; font-size: clamp(1.5rem, 4vw, 2rem);">👋 Wontanara !</h2>
            <p style="color: #666; font-size: clamp(1rem, 2vw, 1.1rem); line-height: 1.6;">
                Bienvenue sur l'interface intelligente <b>Simandou-GN-IA</b>.
                <br>Posez une question ou importez un document/média via le menu de gauche.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Afficher l'historique du chat
    if st.session_state.chat_session:
        for message in st.session_state.chat_session.history:
            role = message.role
            avatar = "👤" if role == "user" else "🤖"

            with st.chat_message(role, avatar=avatar):
                if hasattr(message, 'parts'):
                    text_part = next((part.text for part in message.parts if hasattr(part, 'text')), "")
                elif hasattr(message, 'text'):
                    text_part = message.text
                else:
                    text_part = str(message)

                if text_part:
                    st.markdown(text_part)

    # Zone de saisie
    user_input = st.chat_input("Posez une question à Simandou...")

    # Traitement de la requête
    if user_input:
        chat_handler.process_user_query(user_input)


def _render_settings_interface():
    """Affiche l'interface des paramètres sans détails techniques"""
    st.header("Paramètres")
#
#     # Option d'export
#     st.subheader("Export des données")
#     if st.button("Exporter les archives", use_container_width=True):
#         if hasattr(db, 'export_to_json'):
#             data = db.export_to_json(st.session_state.username)
#             filename = f"archives_{st.session_state.username}_{datetime.now().strftime('%Y%m%d')}.json"
#
#             st.download_button(
#                 label="Télécharger",
#                 data=data,
#                 file_name=filename,
#                 mime="application/json"
#             )

def render_main_interface():
    """Affiche l'interface principale"""

    def render_chat():
        _render_chat_interface()

    def render_archives():
        archive_manager.render_archive_management(st.session_state.username)
 ##Les parametres
    def render_settings():
        _render_settings_interface()

    # Afficher les onglets
    tab_manager.render_tabs(render_chat, render_archives,render_settings)


# ============================================
# LOGIQUE PRINCIPALE
# ============================================

if not is_session_valid:
    # Utilisateur non connecté ou session invalide
    render_sidebar(auth, chat_handler, request_counter)
    st.stop()
else:
    try:
        model_manager.reset_daily_counters()
    except:
        pass

    # Charger les statistiques utilisateur
    if st.session_state.username and not st.session_state.user_stats:
        st.session_state.user_stats = db.get_user_stats(st.session_state.username)

    render_sidebar(auth, chat_handler, request_counter)
    render_main_interface()
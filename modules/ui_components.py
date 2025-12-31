import streamlit as st
from datetime import datetime
from modules.file_processing import FileProcessor
from modules.media_extraction import MediaExtractor
import google.generativeai as genai


def render_sidebar(auth_manager, chat_handler=None, request_counter=None):
    """Affiche la barre latérale sans détails techniques"""
    with st.sidebar:
        st.title("SIMANDOU-GN-IA")
        st.markdown("*L'excellence IA made in Africa.*")
        # st.markdown("---")

        if not st.session_state.logged_in:
            _render_auth_section(auth_manager)
        else:
            _render_logged_in_sidebar(auth_manager, chat_handler, request_counter)


def _render_auth_section(auth_manager):
    """Affiche la section d'authentification"""
    st.subheader("🔑 Connexion / Inscription")
    tab_login, tab_signup, tab_forgot = st.tabs(["Connexion", "Inscription", "Mot de passe oublié"])

    with tab_login:
        login_user = st.text_input("Nom d'utilisateur", key="login_user")
        login_pass = st.text_input("Mot de passe", type="password", key="login_pass")
        if st.button("Se connecter", use_container_width=True, key="btn_login"):
            if login_user and login_pass:
                auth_manager.login(login_user, login_pass)

    with tab_signup:
        signup_user = st.text_input("Nouveau nom d'utilisateur", key="signup_user")
        signup_pass = st.text_input("Nouveau mot de passe", type="password", key="signup_pass")
        st.caption("Question de sécurité (pour la récupération) :")
        security_q_index = st.selectbox(
            "Choisir une question",
            options=range(len(auth_manager.SECURITY_QUESTIONS)),
            format_func=lambda i: auth_manager.SECURITY_QUESTIONS[i],
            key="signup_q_index"
        )
        security_answer = st.text_input("Réponse à la question", key="signup_answer")

        if st.button("S'inscrire", use_container_width=True, key="btn_signup"):
            if signup_user and signup_pass and security_answer:
                auth_manager.signup(signup_user, signup_pass, security_q_index, security_answer)

    with tab_forgot:
        forgot_user = st.text_input("Nom d'utilisateur", key="forgot_user")

        if st.session_state.forgot_state == 0:
            if st.button("Valider l'utilisateur", key="btn_check_user"):
                user_data = auth_manager.db.get_user(forgot_user)

                if user_data:
                    if user_data.get('security_q_index', -1) == -1:
                        st.error("Ce compte n'a pas de question de sécurité configurée.")
                    else:
                        st.session_state.forgot_q_index = user_data.get('security_q_index')
                        st.session_state.forgot_state = 1
                        st.rerun()
                else:
                    st.error("Utilisateur non trouvé.")

        elif st.session_state.forgot_state == 1:
            st.write(f"Question : {auth_manager.SECURITY_QUESTIONS[st.session_state.forgot_q_index]}")
            forgot_answer = st.text_input("Votre réponse", key="forgot_answer")

            if st.button("Vérifier la réponse", key="btn_check_answer"):
                success, user = auth_manager.forgot_password(
                    forgot_user,
                    st.session_state.forgot_q_index,
                    forgot_answer
                )
                if success:
                    st.session_state.forgot_state = 2
                    st.rerun()

        elif st.session_state.forgot_state == 2:
            new_pass = st.text_input("Nouveau mot de passe (min 6 chars)", type="password", key="new_pass")
            if st.button("Définir le nouveau mot de passe", key="btn_set_new_pass"):
                if len(new_pass) >= 6:
                    success, message = auth_manager.reset_password(forgot_user, new_pass)
                    if success:
                        st.success(message)
                        st.session_state.forgot_state = 0
                        for key in ['forgot_q_index', 'new_pass', 'forgot_answer', 'forgot_user']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Le mot de passe est trop court.")


def _render_logged_in_sidebar(auth_manager, chat_handler, request_counter):
    """Affiche la barre latérale sans options techniques"""

    # Afficher le compteur de requêtes
    if request_counter:
        request_counter.display_counter(st.session_state.username, position="sidebar")

    # Bouton nouvelle discussion
    if st.button("➕ Nouvelle Discussion", use_container_width=True):
        chat_handler.archive_and_start_new_chat(st.session_state.username)
        st.rerun()


    # Importation de données
    st.subheader("📂 Importer des données")
    _render_data_import_section()

    # Document actif
    _render_active_document()

    # Section Premium
    _render_premium_section(auth_manager.db)

    # Bouton de déconnexion
    if st.button("🚪 Se déconnecter", use_container_width=True):
        auth_manager.logout()


def _render_chat_archives(chat_handler):
    """Affiche les archives de chat"""
    if st.session_state.username:
        archives_data = chat_handler.db.get_user_archives(st.session_state.username, limit=50)

        if archives_data:
            for archive in archives_data:
                title = archive.get('title', f"Discussion archivée #{archive['id']}")
                timestamp_str = archive.get('timestamp')
                timestamp = datetime.fromisoformat(timestamp_str).strftime(
                    "%d/%m/%y %H:%M") if timestamp_str else "Date inconnue"

                st.markdown(f"*{timestamp}*", help="Date d'archivage")

                if st.button(
                        f"💬 {title.split('...')[0]}",
                        key=f"archive_{archive['id']}",
                        use_container_width=True
                ):
                    chat_handler.load_archive_chat(st.session_state.username, archive['id'])
        else:
            st.info("Aucune ancienne discussion archivée.")
    else:
        st.info("Chargement des archives...")


def _render_data_import_section():
    """Affiche la section d'importation de données"""
    tab_local, tab_media_link, tab_webpage = st.tabs(["📤 Fichier", "🎬 Sources", "📄 Page Web"])

    with tab_local:
        uploaded_file = st.file_uploader(
            "Choisir un fichier",
            type=['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'mp4', 'avi', 'mov', 'mkv',
                  'mp3', 'wav', 'ogg', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'],
            label_visibility="collapsed"
        )
        if uploaded_file:
            if st.button("🚀 Analyser le fichier", use_container_width=True, key="btn_analyze_file"):
                with st.spinner("Traitement du fichier..."):
                    processor = FileProcessor()
                    result = processor.process_uploaded_file(uploaded_file)
                    if result:
                        st.session_state.current_file = result
                        st.toast(f"✅ Fichier analysé: {uploaded_file.name}", icon="✅")
                        st.rerun()

    with tab_media_link:
        st.info("Importez du contenu depuis YouTube ou des liens directs")

        url_input = st.text_input(
            "Collez une URL",
            placeholder="https://www.youtube.com/... ou https://exemple.com/fichier.mp4",
            key="input_media"
        )

        if url_input:
            col1, col2 = st.columns(2)
            extractor = MediaExtractor()

            with col1:
                if st.button("🎬 Analyser YouTube", use_container_width=True, key="btn_youtube"):
                    with st.spinner("Traitement..."):
                        if 'youtube.com' in url_input or 'youtu.be' in url_input:
                            path, name, mime_type = extractor.extract_youtube_transcript(url_input)

                            if path:
                                processor = FileProcessor()
                                ref = processor.upload_to_gemini(path, name, mime_type_hint=mime_type)
                                if ref:
                                    st.session_state.current_file = ref
                                    st.toast(f"✅ YouTube analysé: {name}", icon="✅")
                                    st.rerun()
                            else:
                                st.error("Impossible d'analyser cette vidéo.")
                        else:
                            st.error("URL YouTube invalide.")

            with col2:
                if st.button("🔗 Analyser lien", use_container_width=True, key="btn_direct"):
                    with st.spinner("Téléchargement..."):
                        path, name, mime_type = extractor.download_file_from_url(url_input)

                        if path:
                            processor = FileProcessor()
                            ref = processor.upload_to_gemini(path, name, mime_type_hint=mime_type)
                            if ref:
                                st.session_state.current_file = ref
                                st.toast(f"✅ Fichier analysé: {name}", icon="✅")
                                st.rerun()
                        else:
                            st.error("Impossible de télécharger.")

    with tab_webpage:
        st.info("Analysez le contenu d'une page web")

        url_input_web = st.text_input(
            "URL de la page web",
            placeholder="https://www.exemple.com/article",
            key="input_web"
        )

        if url_input_web:
            if st.button("🔎 Analyser la page", use_container_width=True, key="btn_analyze_webpage"):
                with st.spinner("Extraction..."):
                    extractor = MediaExtractor()
                    path, name, mime_type = extractor.analyze_webpage_content(url_input_web)

                    if path:
                        processor = FileProcessor()
                        ref = processor.upload_to_gemini(path, name, mime_type_hint=mime_type)

                        if ref:
                            st.session_state.current_file = ref
                            st.toast(f"✅ Contenu extrait: {name}", icon="✅")
                            st.rerun()
                    else:
                        st.error("Impossible d'analyser cette page.")


def _render_active_document():
    """Affiche le document actif"""
    if st.session_state.current_file:
        col1, col2 = st.columns([3, 1])

        with col1:
            st.success(f"📄 **Document Actif :** {st.session_state.current_file.display_name}")

        with col2:
            if st.button("❌", key="detach_file", use_container_width=True, help="Détacher le fichier"):
                try:
                    genai.delete_file(name=st.session_state.current_file.name)
                except Exception:
                    pass
                finally:
                    st.session_state.current_file = None
                    st.rerun()


def _render_premium_section(database):
    """Affiche la section premium"""
    st.subheader("🚀 Compte Premium")

    if st.session_state.username:
        user_data = database.get_user(st.session_state.username)
        account_type = user_data.get('account_type', 'free') if user_data else 'free'

        # Afficher les statistiques
        # if st.session_state.user_stats:
        #     stats = st.session_state.user_stats
        #     st.metric("Archives", stats.get('archive_count', 0))

        if account_type == 'free':
            # can_request, max_requests, current_count = database.check_and_update_requests(
            #     st.session_state.username
            # )
            # st.warning(f"Version **Gratuite** ({current_count}/{max_requests} requêtes/jour).")
            st.markdown("Passez au Premium pour :")
            st.markdown("""
            * Requêtes illimitées.
            * Priorité d'exécution.
            * Support étendu.
            * Historique illimité.
            """)
            if st.button("Passer au Premium", key="btn_premium", use_container_width=True):
                database.update_account_type(st.session_state.username, 'premium')
                st.session_state.user_stats = database.get_user_stats(st.session_state.username)
                st.success("✅ Compte mis à jour !")
                st.rerun()
        else:
            st.success("Type de compte : **Premium** (Requêtes illimitées)")

import streamlit as st
import google.generativeai as genai
from datetime import datetime


class ChatHandler:
    def __init__(self, model_manager, database):
        self.model_manager = model_manager
        self.db = database

    def process_user_query(self, query):
        """Traite une requête utilisateur de manière transparente"""

        # Vérification de base
        if st.session_state.viewing_archive_id is not None:
            st.error("Mode lecture seule activé")
            return

        # Vérifier la limite de requêtes
        can_request, max_requests, current_count = self.db.check_and_update_requests(
            st.session_state.username
        )

        if not can_request:
            st.error(f"❌ Limite journalière atteinte ({current_count}/{max_requests} requêtes)")
            return

        # Analyser le type de fichier
        file_type = self._get_file_type()

        # Sélection automatique et transparente du modèle
        model, model_type = self.model_manager.select_model(query, file_type)

        # Afficher le message utilisateur
        with st.chat_message("user", avatar="👤"):
            st.markdown(query)

        # Traitement de la réponse
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()

            with st.spinner("Simandou réfléchit..."):
                try:
                    # Vérifier et préparer le fichier
                    valid_file = self._validate_current_file()

                    # Préparer la session de chat
                    history = st.session_state.chat_session.history[:] if hasattr(st.session_state.chat_session,
                                                                                  'history') else []
                    new_chat = model.start_chat(history=history)
                    st.session_state.chat_session = new_chat

                    # Envoyer la requête
                    if valid_file:
                        response = new_chat.send_message([query, valid_file])
                    else:
                        response = new_chat.send_message(query)

                    # Afficher la réponse
                    message_placeholder.markdown(response.text)

                    # Mettre à jour les compteurs (transparent)
                    self.model_manager.update_counter(model_type)

                    # Incrémenter le compteur utilisateur
                    if hasattr(self.db, 'increment_request_count'):
                        self.db.increment_request_count(st.session_state.username)

                    # Sauvegarder le chat
                    self.db.save_active_chat(st.session_state.username, new_chat)

                    # Mettre à jour les statistiques
                    if st.session_state.username:
                        st.session_state.user_stats = self.db.get_user_stats(st.session_state.username)

                except Exception as e:
                    # Gestion d'erreur discrète
                    self._handle_error(e)

    def _get_file_type(self):
        """Détection rapide du type de fichier"""
        if not st.session_state.current_file:
            return None

        file_name = st.session_state.current_file.display_name.lower()

        # Vérifications rapides
        if any(ext in file_name for ext in ['.pdf', '.doc', '.docx']):
            return 'document'
        elif any(ext in file_name for ext in ['.py', '.js', '.java', '.cpp']):
            return 'code'

        return 'other'

    def _validate_current_file(self):
        """Vérification rapide de validité du fichier"""
        if not st.session_state.current_file:
            return None

        try:
            genai.get_file(st.session_state.current_file.name)
            return st.session_state.current_file
        except Exception:
            st.session_state.current_file = None
            return None

    def _handle_error(self, error):
        """Gestion d'erreur sans détails techniques"""
        error_msg = str(error).lower()

        if "quota" in error_msg or "limit" in error_msg:
            st.warning("⚠️ Veuillez patienter un instant avant de réessayer.")
        elif "safety" in error_msg:
            st.error("⚠️ Cette requête ne peut pas être traitée.")
        else:
            st.error("⚠️ Une erreur est survenue. Veuillez réessayer.")

    # Méthodes pour la gestion des archives

    def create_chat_session_from_history(self, history_data):
        """Crée une session de chat à partir de l'historique"""
        model = self.model_manager.get_default_model()
        new_chat = model.start_chat(history=[])

        for msg in history_data:
            if msg['role'] == 'user':
                new_chat.history.append(self._create_message_object('user', msg['text']))
            elif msg['role'] == 'model':
                new_chat.history.append(self._create_message_object('model', msg['text']))

        return new_chat

    def _create_message_object(self, role, text):
        """Crée un objet message compatible avec Gemini"""

        class Parts:
            def __init__(self, text):
                self.text = text

        class Message:
            def __init__(self, role, text):
                self.role = role
                self.parts = [Parts(text)]

        return Message(role, text)

    def archive_and_start_new_chat(self, username):
        """Archive le chat actuel et commence une nouvelle conversation"""
        if 'chat_session' in st.session_state:
            self.db.archive_chat(username, st.session_state.chat_session)

        # Réinitialiser avec le modèle par défaut
        default_model = self.model_manager.get_default_model()
        st.session_state.chat_session = default_model.start_chat(history=[])
        st.session_state.current_file = None
        st.session_state.viewing_archive_id = None

        # Mettre à jour les statistiques
        if st.session_state.username:
            st.session_state.user_stats = self.db.get_user_stats(st.session_state.username)

        st.rerun()


    def load_archive_chat(self, username, archive_id):
        """Charge une conversation archivée"""
        # Sauvegarder le chat actif d'abord
        if 'chat_session' in st.session_state and st.session_state.viewing_archive_id is None:
            self.db.save_active_chat(username, st.session_state.chat_session)

        # Charger l'historique archivé
        loaded_history = self.db.load_history(username, archive_id=archive_id)

        # Créer une nouvelle session avec l'historique
        st.session_state.chat_session = self.create_chat_session_from_history(loaded_history)
        st.session_state.viewing_archive_id = archive_id

        # Nettoyer le fichier actuel
        if st.session_state.current_file:
            try:
                genai.delete_file(name=st.session_state.current_file.name)
            except Exception:
                pass
            st.session_state.current_file = None

        st.rerun()

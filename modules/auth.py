import streamlit as st
import hashlib
import json
import time
import secrets
from datetime import datetime


class AuthManager:
    # Questions de sécurité
    SECURITY_QUESTIONS = [
        "Quel est le nom de votre ville de naissance ?",
        "Quel est votre film préféré ?",
        "Quel est votre sport préféré ?",
        "Quelle est votre école primaire ?"
    ]

    def __init__(self, database, model_manager):
        self.db = database
        self.model_manager = model_manager
        # Utiliser le modèle par défaut
        self.default_model = model_manager.get_default_model()

    def login(self, username, password):
        """Gère la connexion d'un utilisateur avec création de token"""
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = self.db.get_user(username)

        if user and user.get('password_hash') == hashed_password:
            # Charger l'historique utilisateur
            self._load_user_history(username)

            st.session_state.logged_in = True
            st.session_state.username = username

            # ============ CRÉATION DU TOKEN DE SESSION ============
            # Générer un token sécurisé
            token = secrets.token_urlsafe(32)
            timestamp = time.time()

            # Sauvegarder dans la session
            st.session_state.auth_token = token
            st.session_state.login_time = timestamp

            # Optionnel: sauvegarder dans la base de données
            if hasattr(self.db, 'save_session_token'):
                self.db.save_session_token(username, token, timestamp)
            # ======================================================

            st.success(f"Bienvenue, {username} !")
            st.rerun()
            return True
        else:
            st.error("Nom d'utilisateur ou mot de passe incorrect")
            return False

    def _load_user_history(self, username):
        """Charge l'historique de l'utilisateur"""
        loaded_history = self.db.load_history(username)

        if loaded_history:
            # Utiliser le modèle par défaut
            history_content = []

            for msg in loaded_history:
                if msg['role'] == 'user':
                    history_content.append({"role": "user", "parts": [{"text": msg['text']}]})
                elif msg['role'] == 'model':
                    history_content.append({"role": "model", "parts": [{"text": msg['text']}]})

            # Créer une nouvelle session de chat avec le modèle par défaut
            st.session_state.chat_session = self.default_model.start_chat(history=[])

            # Reconstruire l'historique
            for content in history_content:
                if content["role"] == "user":
                    st.session_state.chat_session.history.append(self._create_message_object(
                        'user', content["parts"][0]["text"]
                    ))
                else:
                    st.session_state.chat_session.history.append(self._create_message_object(
                        'model', content["parts"][0]["text"]
                    ))
        else:
            # Nouvel utilisateur - créer une session vide
            st.session_state.chat_session = self.default_model.start_chat(history=[])

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

    def signup(self, username, password, security_q_index=None, security_answer=None):
        """Gère l'inscription d'un nouvel utilisateur"""
        if self.db.user_exists(username):
            st.error("Ce nom d'utilisateur est déjà pris")
            return False

        if len(password) < 6:
            st.error("Le mot de passe doit contenir au moins 6 caractères")
            return False

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        user_data = {
            'password_hash': hashed_password,
            'security_q_index': security_q_index if security_q_index is not None else -1,
            'security_a_hash': hashlib.sha256(
                (security_answer or "").encode()
            ).hexdigest(),
            'account_type': 'free'
        }

        if self.db.save_user(username, user_data):
            st.success("Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
            return True
        else:
            st.error("Erreur lors de la création du compte")
            return False

    def forgot_password(self, username, question_index, answer):
        """Vérifie la réponse à la question de sécurité"""
        user = self.db.get_user(username)

        if not user:
            st.error("Utilisateur non trouvé")
            return False, None

        # Vérifier la question de sécurité
        if user.get('security_q_index') != question_index:
            st.error("Question de sécurité incorrecte")
            return False, None

        hashed_answer = hashlib.sha256(answer.encode()).hexdigest()

        if user.get('security_a_hash') != hashed_answer:
            st.error("Réponse à la question de sécurité incorrecte")
            return False, None

        return True, user

    def reset_password(self, username, new_password):
        """Réinitialise le mot de passe"""
        if len(new_password) < 6:
            return False, "Le mot de passe doit contenir au moins 6 caractères"

        new_hashed_password = hashlib.sha256(new_password.encode()).hexdigest()

        if self.db.update_password(username, new_hashed_password):
            return True, "Mot de passe mis à jour avec succès !"
        else:
            return False, "Erreur lors de la mise à jour du mot de passe"

    def update_security_question(self, username, question_index, answer):
        """Met à jour la question de sécurité"""
        hashed_answer = hashlib.sha256(answer.encode()).hexdigest()

        if self.db.update_security_data(username, question_index, hashed_answer):
            st.success("Question de sécurité mise à jour")
            return True
        else:
            st.error("Erreur lors de la mise à jour")
            return False

    def logout(self):
        """Gère la déconnexion avec suppression du token"""
        # ============ SUPPRESSION DU TOKEN ============
        # Récupérer le token avant nettoyage
        auth_token = st.session_state.get('auth_token')
        username = st.session_state.get('username')

        # Supprimer de la base de données si fonction disponible
        if auth_token and username and hasattr(self.db, 'delete_session_token'):
            self.db.delete_session_token(username, auth_token)
        # ==============================================

        # Sauvegarder le chat actif avant de déconnecter
        if st.session_state.logged_in and 'chat_session' in st.session_state:
            self.db.save_active_chat(st.session_state.username, st.session_state.chat_session)

        # Nettoyer les fichiers
        if st.session_state.current_file:
            try:
                import google.generativeai as genai
                genai.delete_file(name=st.session_state.current_file.name)
            except Exception:
                pass

        # ============ NETTOYAGE COMPLET DE LA SESSION ============
        # Liste de toutes les variables de session à supprimer
        session_vars = [
            'auth_token', 'login_time',  # Tokens de session
            'logged_in', 'username', 'chat_session',  # Authentification
            'current_file', 'viewing_archive_id',  # Données chat
            'forgot_state', 'user_stats',  # État utilisateur
            'active_tab'  # Interface
        ]

        for var in session_vars:
            if var in st.session_state:
                del st.session_state[var]
        # ========================================================

        st.rerun()

    # ============ NOUVELLES MÉTHODES POUR LA VALIDATION ============

    def check_session_validity(self):
        """Vérifie si la session courante est valide"""
        if not st.session_state.get('logged_in'):
            return False

        # Vérifier la présence du token
        if 'auth_token' not in st.session_state or not st.session_state.auth_token:
            return False

        # Vérifier la présence du timestamp
        if 'login_time' not in st.session_state:
            return False

        # Vérifier l'âge de la session (4 heures max)
        session_age = time.time() - st.session_state.login_time
        if session_age >= 14400:  # 4 heures = 14400 secondes
            # Session expirée, nettoyer
            self._clean_expired_session()
            return False

        # Optionnel: vérifier dans la base de données
        if hasattr(self.db, 'validate_session_token'):
            username = st.session_state.get('username')
            token = st.session_state.get('auth_token')
            if username and token:
                return self.db.validate_session_token(username, token)

        return True

    def _clean_expired_session(self):
        """Nettoie une session expirée"""
        expired_vars = ['auth_token', 'login_time', 'logged_in', 'username']
        for var in expired_vars:
            if var in st.session_state:
                del st.session_state[var]

    def validate_session_token(self, username, token):
        """Valide un token de session spécifique"""
        # Vérifier d'abord dans la session courante
        if (st.session_state.get('auth_token') == token and
                st.session_state.get('username') == username):

            # Vérifier l'âge
            if 'login_time' in st.session_state:
                session_age = time.time() - st.session_state.login_time
                return session_age < 14400  # 4 heures

        # Vérifier dans la base de données (optionnel)
        if hasattr(self.db, 'validate_session_token'):
            return self.db.validate_session_token(username, token)

        return False
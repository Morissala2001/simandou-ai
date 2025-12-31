import os
import json
import hashlib
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
from contextlib import contextmanager


class PostgreSQLDatabase:
    MAX_FREE_REQUESTS = 15

    def __init__(self):
        self._init_connection()
        self._create_tables()

    def _init_connection(self):
        """Initialise la connexion à PostgreSQL"""
        self.conn_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'simandou_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'port': os.getenv('DB_PORT', '5432'),
            # FORCER L'ENCODAGE UTF-8
            'client_encoding': 'UTF8',
            'options': '-c client_encoding=UTF8'
        }

    @contextmanager
    def _get_connection(self):
        """Gestionnaire de contexte pour les connexions avec encodage UTF-8"""
        conn = None
        try:
            conn = psycopg2.connect(**self.conn_params)
            # Définir l'encodage explicitement
            conn.set_client_encoding('UTF8')
            yield conn
        except psycopg2.OperationalError as e:
            error_msg = self._safe_encode(str(e))
            st.error(f"Erreur de connexion à la base de données: {error_msg}")
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def _get_cursor(self, conn=None):
        """Gestionnaire de contexte pour les curseurs avec encodage UTF-8"""
        if conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
            finally:
                cursor.close()
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    yield cursor
                finally:
                    cursor.close()
                    conn.commit()

    def _safe_encode(self, text):
        """Encode un texte en UTF-8 de manière sécurisée"""
        if isinstance(text, str):
            try:
                return text.encode('utf-8', errors='replace').decode('utf-8')
            except:
                return str(text)
        return str(text)

    def _create_tables(self):
        """Crée les tables nécessaires si elles n'existent pas - version simplifiée"""
        create_tables_sql = """
        -- Table des utilisateurs
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            account_type VARCHAR(20) DEFAULT 'free',
            security_q_index INTEGER DEFAULT -1,
            security_a_hash VARCHAR(255) DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_reset_date DATE DEFAULT CURRENT_DATE
        );

        -- Table des requêtes journalières
        CREATE TABLE IF NOT EXISTS daily_requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            request_date DATE NOT NULL,
            request_count INTEGER DEFAULT 0,
            UNIQUE(user_id, request_date)
        );

        -- Table des chats actifs
        CREATE TABLE IF NOT EXISTS active_chats (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            chat_data TEXT NOT NULL DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Table des archives
        CREATE TABLE IF NOT EXISTS chat_archives (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255),
            chat_data TEXT NOT NULL DEFAULT '[]',
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        try:
            with self._get_cursor() as cursor:
                # Exécuter les créations de tables avec encodage sécurisé
                cursor.execute(create_tables_sql)
                st.success("Tables PostgreSQL creees avec succes")
        except Exception as e:
            error_msg = self._safe_encode(str(e))
            st.warning(f"Note sur la creation des tables: {error_msg}")
            # Continuer même en cas d'erreur (les tables peuvent déjà exister)

    def user_exists(self, username):
        """Vérifie si un utilisateur existe"""
        sql = "SELECT id FROM users WHERE username = %s"

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (username,))
                return cursor.fetchone() is not None
        except Exception as e:
            error_msg = self._safe_encode(str(e))
            st.warning(f"Erreur verification utilisateur: {error_msg}")
            return False

    def get_user(self, username):
        """Récupère les données d'un utilisateur"""
        sql = """
        SELECT u.*, COALESCE(dr.request_count, 0) as daily_requests
        FROM users u
        LEFT JOIN daily_requests dr ON u.id = dr.user_id 
            AND dr.request_date = CURRENT_DATE
        WHERE u.username = %s
        """

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (username,))
                user = cursor.fetchone()

                if user:
                    return dict(user)
                return None
        except Exception as e:
            error_msg = self._safe_encode(str(e))
            st.warning(f"Erreur recuperation utilisateur: {error_msg}")
            return None

    def save_user(self, username, user_data):
        """Crée ou met à jour un utilisateur"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Vérifier si l'utilisateur existe déjà
                    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                    existing = cursor.fetchone()

                    if existing:
                        # Mise à jour
                        user_id = existing[0]
                        sql = """
                        UPDATE users 
                        SET password_hash = %s, 
                            security_q_index = %s, 
                            security_a_hash = %s,
                            account_type = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """
                        cursor.execute(sql, (
                            user_data['password_hash'],
                            user_data['security_q_index'],
                            user_data['security_a_hash'],
                            user_data.get('account_type', 'free'),
                            user_id
                        ))
                    else:
                        # Insertion
                        sql = """
                        INSERT INTO users 
                        (username, password_hash, security_q_index, security_a_hash, account_type)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """
                        cursor.execute(sql, (
                            username,
                            user_data['password_hash'],
                            user_data['security_q_index'],
                            user_data['security_a_hash'],
                            user_data.get('account_type', 'free')
                        ))
                        user_id = cursor.fetchone()[0]

                    # Créer l'entrée de chat actif
                    cursor.execute(
                        "SELECT id FROM active_chats WHERE user_id = %s",
                        (user_id,)
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO active_chats (user_id, chat_data) VALUES (%s, %s)",
                            (user_id, '[]')
                        )

                    conn.commit()
                    return user_id
        except Exception as e:
            error_msg = self._safe_encode(str(e))
            st.warning(f"Erreur sauvegarde utilisateur: {error_msg}")
            return None

    def load_history(self, username, archive_id=None):
        """Charge l'historique d'un utilisateur"""
        user = self.get_user(username)
        if not user:
            return []

        try:
            if archive_id is None:
                # Chat actif
                sql = "SELECT chat_data FROM active_chats WHERE user_id = %s"

                with self._get_cursor() as cursor:
                    cursor.execute(sql, (user['id'],))
                    result = cursor.fetchone()
                    if result and result['chat_data']:
                        try:
                            return json.loads(result['chat_data'])
                        except:
                            return []
                    return []
            else:
                # Archive spécifique
                sql = "SELECT chat_data FROM chat_archives WHERE id = %s AND user_id = %s"

                with self._get_cursor() as cursor:
                    cursor.execute(sql, (archive_id, user['id']))
                    result = cursor.fetchone()
                    if result and result['chat_data']:
                        try:
                            return json.loads(result['chat_data'])
                        except:
                            return []
                    return []
        except Exception as e:
            error_msg = self._safe_encode(str(e))
            st.warning(f"Erreur chargement historique: {error_msg}")
            return []

    def save_active_chat(self, username, chat_session):
        """Sauvegarde le chat actif"""
        user = self.get_user(username)
        if not user:
            return

        # Convertir l'historique en JSON
        history_data = []
        try:
            if hasattr(chat_session, 'history'):
                for msg in chat_session.history:
                    if hasattr(msg, 'parts'):
                        text_part = next((part.text for part in msg.parts if hasattr(part, 'text')), None)
                    elif hasattr(msg, 'text'):
                        text_part = msg.text
                    else:
                        text_part = str(msg)

                    if text_part:
                        history_data.append({'role': msg.role, 'text': text_part})
        except Exception as e:
            error_msg = self._safe_encode(str(e))
            st.warning(f"Erreur conversion historique: {error_msg}")
            return

        sql = """
        UPDATE active_chats 
        SET chat_data = %s, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
        """

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (json.dumps(history_data), user['id']))
                return True
        except Exception as e:
            error_msg = self._safe_encode(str(e))
            st.warning(f"Erreur sauvegarde chat actif: {error_msg}")
            return False

    def archive_chat(self, username, chat_session):
        """Archive le chat actuel"""
        user = self.get_user(username)
        if not user:
            return

        # Extraire l'historique
        history_data = []
        try:
            if hasattr(chat_session, 'history'):
                for msg in chat_session.history:
                    if hasattr(msg, 'parts'):
                        text_part = next((part.text for part in msg.parts if hasattr(part, 'text')), None)
                    else:
                        text_part = getattr(msg, 'text', str(msg))

                    if text_part:
                        history_data.append({'role': msg.role, 'text': text_part})
        except Exception as e:
            error_msg = self._safe_encode(str(e))
            st.warning(f"Erreur extraction historique pour archivage: {error_msg}")
            return

        if history_data:
            # Déterminer le titre de l'archive
            first_user_question = next(
                (item['text'] for item in history_data if item['role'] == 'user'),
                'Nouvelle conversation'
            )
            title = first_user_question[:50] + ("..." if len(first_user_question) > 50 else "")

            # Insérer l'archive
            sql = """
            INSERT INTO chat_archives (user_id, title, chat_data)
            VALUES (%s, %s, %s)
            """

            try:
                with self._get_cursor() as cursor:
                    cursor.execute(sql, (user['id'], title, json.dumps(history_data)))

                # Vider le chat actif
                self._clear_active_chat(user['id'])

                return True
            except Exception as e:
                error_msg = self._safe_encode(str(e))
                st.warning(f"Erreur archivage: {error_msg}")
                return False
        return False

    def _clear_active_chat(self, user_id):
        """Vide le chat actif"""
        sql = "UPDATE active_chats SET chat_data = %s WHERE user_id = %s"

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, ('[]', user_id))
                return True
        except Exception:
            return False

    def get_user_archives(self, username, limit=50):
        """Récupère les archives d'un utilisateur"""
        user = self.get_user(username)
        if not user:
            return []

        sql = """
        SELECT id, title, archived_at, chat_data
        FROM chat_archives
        WHERE user_id = %s
        ORDER BY archived_at DESC
        LIMIT %s
        """

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (user['id'], limit))
                archives = cursor.fetchall()

                result = []
                for archive in archives:
                    try:
                        result.append({
                            'id': archive['id'],
                            'title': archive['title'],
                            'timestamp': archive['archived_at'].isoformat() if archive['archived_at'] else '',
                            'history': json.loads(archive['chat_data']) if archive['chat_data'] else []
                        })
                    except:
                        continue
                return result
        except Exception as e:
            error_msg = self._safe_encode(str(e))
            st.warning(f"Erreur recuperation archives: {error_msg}")
            return []

    def check_and_update_requests(self, username):
        """Vérifie et met à jour le compteur de requêtes"""
        user = self.get_user(username)
        if not user:
            return False, self.MAX_FREE_REQUESTS, 0

        account_type = user.get('account_type', 'free')

        if account_type == 'premium':
            return True, self.MAX_FREE_REQUESTS, 0

        # Vérifier les requêtes du jour
        today = date.today()

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Vérifier la dernière date de réinitialisation
                    if user.get('last_reset_date') != today:
                        cursor.execute(
                            "UPDATE users SET last_reset_date = %s WHERE id = %s",
                            (today, user['id'])
                        )
                        conn.commit()
                        return True, self.MAX_FREE_REQUESTS, 1

                    # Récupérer ou créer l'entrée du jour
                    sql = """
                    INSERT INTO daily_requests (user_id, request_date, request_count)
                    VALUES (%s, %s, 1)
                    ON CONFLICT (user_id, request_date)
                    DO UPDATE SET request_count = daily_requests.request_count + 1
                    RETURNING request_count
                    """
                    cursor.execute(sql, (user['id'], today))

                    result = cursor.fetchone()
                    current_count = result[0] if result else 1

                    conn.commit()

                    can_request = current_count <= self.MAX_FREE_REQUESTS
                    return can_request, self.MAX_FREE_REQUESTS, current_count

        except Exception as e:
            error_msg = self._safe_encode(str(e))
            st.warning(f"Erreur verification requetes: {error_msg}")
            return False, self.MAX_FREE_REQUESTS, 0

    def test_connection(self):
        """Teste la connexion à la base de données"""
        try:
            with self._get_cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                version_str = self._safe_encode(str(version['version']))
                return True, f"Connexion PostgreSQL reussie - Version: {version_str[:100]}"
        except Exception as e:
            error_msg = self._safe_encode(str(e))
            return False, f"Erreur connexion PostgreSQL: {error_msg}"
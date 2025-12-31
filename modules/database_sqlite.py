# modules/database_sqlite.py
import os
import json
import hashlib
import sqlite3
from datetime import datetime, date
import streamlit as st
from contextlib import contextmanager


class SQLiteDatabase:
    MAX_FREE_REQUESTS = 15

    def __init__(self, db_path="simandou_data.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Gestionnaire de contexte pour les connexions SQLite"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Pour avoir des dictionnaires
            yield conn
        except Exception as e:
            st.error(f"Erreur de connexion SQLite: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def _get_cursor(self, conn=None):
        """Gestionnaire de contexte pour les curseurs SQLite"""
        if conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
        else:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                try:
                    yield cursor
                    conn.commit()
                finally:
                    cursor.close()

    def _init_db(self):
        """Initialise la base SQLite avec toutes les tables"""
        try:
            with self._get_cursor() as cursor:
                # Table des utilisateurs
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    account_type TEXT DEFAULT 'free',
                    security_q_index INTEGER DEFAULT -1,
                    security_a_hash TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_reset_date DATE DEFAULT CURRENT_DATE
                )
                ''')

                # Table des requêtes journalières
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    request_date DATE NOT NULL,
                    request_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, request_date)
                )
                ''')

                # Table des chats actifs
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS active_chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    chat_data TEXT NOT NULL DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                ''')

                # Table des archives
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_archives (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT,
                    chat_data TEXT NOT NULL DEFAULT '[]',
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                ''')

                # Créer des index pour la performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_username ON users(username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_requests ON daily_requests(user_id, request_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_active ON active_chats(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_archive_user ON chat_archives(user_id)')

            #st.success("✅Succès")

        except Exception as e:
            st.error(f"Erreur initialisation SQLite: {e}")

    # === MÉTHODES IDENTIQUES À POSTGRESQL (interface compatible) ===

    def user_exists(self, username):
        """Vérifie si un utilisateur existe"""
        sql = "SELECT id FROM users WHERE username = ?"

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (username,))
                return cursor.fetchone() is not None
        except Exception as e:
            st.error(f"Erreur vérification utilisateur: {e}")
            return False

    def get_user(self, username):
        """Récupère les données d'un utilisateur"""
        sql = """
        SELECT u.*, COALESCE(dr.request_count, 0) as daily_requests
        FROM users u
        LEFT JOIN daily_requests dr ON u.id = dr.user_id 
            AND dr.request_date = DATE('now')
        WHERE u.username = ?
        """

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (username,))
                row = cursor.fetchone()

                if row:
                    # Convertir Row en dictionnaire
                    return dict(row)
                return None
        except Exception as e:
            st.error(f"Erreur récupération utilisateur: {e}")
            return None

    def save_user(self, username, user_data):
        """Crée ou met à jour un utilisateur"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Vérifier si l'utilisateur existe déjà
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                existing = cursor.fetchone()

                if existing:
                    # Mise à jour
                    user_id = existing[0]
                    sql = """
                    UPDATE users 
                    SET password_hash = ?, 
                        security_q_index = ?, 
                        security_a_hash = ?,
                        account_type = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
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
                    VALUES (?, ?, ?, ?, ?)
                    """
                    cursor.execute(sql, (
                        username,
                        user_data['password_hash'],
                        user_data['security_q_index'],
                        user_data['security_a_hash'],
                        user_data.get('account_type', 'free')
                    ))
                    user_id = cursor.lastrowid

                # Créer l'entrée de chat actif
                cursor.execute(
                    "SELECT id FROM active_chats WHERE user_id = ?",
                    (user_id,)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO active_chats (user_id, chat_data) VALUES (?, ?)",
                        (user_id, json.dumps([]))
                    )

                conn.commit()
                return user_id

        except Exception as e:
            st.error(f"Erreur sauvegarde utilisateur: {e}")
            return None

    def load_history(self, username, archive_id=None):
        """Charge l'historique d'un utilisateur"""
        user = self.get_user(username)
        if not user:
            return []

        try:
            if archive_id is None:
                # Chat actif
                sql = "SELECT chat_data FROM active_chats WHERE user_id = ?"

                with self._get_cursor() as cursor:
                    cursor.execute(sql, (user['id'],))
                    result = cursor.fetchone()
                    if result and result[0]:  # result[0] car tuple
                        return json.loads(result[0])
                    return []
            else:
                # Archive spécifique
                sql = "SELECT chat_data FROM chat_archives WHERE id = ? AND user_id = ?"

                with self._get_cursor() as cursor:
                    cursor.execute(sql, (archive_id, user['id']))
                    result = cursor.fetchone()
                    if result and result[0]:
                        return json.loads(result[0])
                    return []
        except Exception as e:
            st.error(f"Erreur chargement historique: {e}")
            return []

    def save_active_chat(self, username, chat_session):
        """Sauvegarde le chat actif"""
        user = self.get_user(username)
        if not user:
            return

        # Convertir l'historique en JSON
        history_data = []
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

        sql = """
        UPDATE active_chats 
        SET chat_data = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (json.dumps(history_data), user['id']))
                return True
        except Exception as e:
            st.error(f"Erreur sauvegarde chat actif: {e}")
            return False

    def archive_chat(self, username, chat_session):
        """Archive le chat actuel"""
        user = self.get_user(username)
        if not user:
            return

        # Extraire l'historique
        history_data = []
        if hasattr(chat_session, 'history'):
            for msg in chat_session.history:
                if hasattr(msg, 'parts'):
                    text_part = next((part.text for part in msg.parts if hasattr(part, 'text')), None)
                else:
                    text_part = getattr(msg, 'text', str(msg))

                if text_part:
                    history_data.append({'role': msg.role, 'text': text_part})

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
            VALUES (?, ?, ?)
            """

            try:
                with self._get_cursor() as cursor:
                    cursor.execute(sql, (user['id'], title, json.dumps(history_data)))

                # Vider le chat actif
                self._clear_active_chat(user['id'])

                return True
            except Exception as e:
                st.error(f"Erreur archivage: {e}")
                return False
        return False

    def _clear_active_chat(self, user_id):
        """Vide le chat actif"""
        sql = "UPDATE active_chats SET chat_data = ? WHERE user_id = ?"

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (json.dumps([]), user_id))
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
        WHERE user_id = ?
        ORDER BY archived_at DESC
        LIMIT ?
        """

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (user['id'], limit))
                archives = cursor.fetchall()

                result = []
                for archive in archives:
                    result.append({
                        'id': archive[0],
                        'title': archive[1] or f"Archive #{archive[0]}",
                        'timestamp': archive[2] or datetime.now().isoformat(),
                        'history': json.loads(archive[3]) if archive[3] else []
                    })
                return result
        except Exception as e:
            st.error(f"Erreur récupération archives: {e}")
            return []


    def check_and_update_requests(self, username):
        """Vérifie si l'utilisateur peut faire une requête SANS l'incrémenter"""
        user = self.get_user(username)
        if not user:
            return False, self.MAX_FREE_REQUESTS, 0

        account_type = user.get('account_type', 'free')

        # Les comptes premium ont des requêtes illimitées
        if account_type == 'premium':
            return True, self.MAX_FREE_REQUESTS, 0

        from datetime import date
        today = date.today().isoformat()

        try:
            with self._get_cursor() as cursor:
                # Vérifier si c'est un nouveau jour
                if user.get('last_reset_date') != today:
                    # Nouveau jour : réinitialiser le compteur
                    cursor.execute(
                        "UPDATE users SET last_reset_date = ? WHERE username = ?",
                        (today, username)
                    )
                    cursor.execute(
                        "DELETE FROM daily_requests WHERE user_id = ? AND request_date = ?",
                        (user['id'], today)
                    )
                    cursor.execute(
                        "INSERT INTO daily_requests (user_id, request_date, request_count) VALUES (?, ?, 0)",
                        (user['id'], today)
                    )
                    return True, self.MAX_FREE_REQUESTS, 0

                # Récupérer le compteur actuel
                cursor.execute(
                    "SELECT request_count FROM daily_requests WHERE user_id = ? AND request_date = ?",
                    (user['id'], today)
                )
                result = cursor.fetchone()
                current_count = result[0] if result else 0

                # Vérifier si la limite est atteinte
                if current_count >= self.MAX_FREE_REQUESTS:
                    return False, self.MAX_FREE_REQUESTS, current_count

                return True, self.MAX_FREE_REQUESTS, current_count

        except Exception as e:
            import streamlit as st
            st.warning(f"⚠️ Erreur vérification requêtes: {e}")
            return True, self.MAX_FREE_REQUESTS, 0

    def increment_request_count(self, username):
        """Incrémente le compteur de requêtes APRÈS une réponse réussie"""
        user = self.get_user(username)
        if not user:
            return False

        from datetime import date
        today = date.today().isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Vérifier si c'est un nouveau jour
                if user.get('last_reset_date') != today:
                    cursor.execute(
                        "UPDATE users SET last_reset_date = ? WHERE id = ?",
                        (today, user['id'])
                    )
                    cursor.execute(
                        "DELETE FROM daily_requests WHERE user_id = ? AND request_date = ?",
                        (user['id'], today)
                    )
                    cursor.execute(
                        "INSERT INTO daily_requests (user_id, request_date, request_count) VALUES (?, ?, 1)",
                        (user['id'], today)
                    )
                    conn.commit()
                    return True

                # Récupérer le compteur actuel et l'incrémenter
                cursor.execute(
                    "SELECT request_count FROM daily_requests WHERE user_id = ? AND request_date = ?",
                    (user['id'], today)
                )
                result = cursor.fetchone()

                if result:
                    current_count = result[0]
                    new_count = current_count + 1

                    cursor.execute(
                        "UPDATE daily_requests SET request_count = ? WHERE user_id = ? AND request_date = ?",
                        (new_count, user['id'], today)
                    )
                else:
                    # Première requête du jour
                    cursor.execute(
                        "INSERT INTO daily_requests (user_id, request_date, request_count) VALUES (?, ?, 1)",
                        (user['id'], today)
                    )
                    cursor.execute(
                        "UPDATE users SET last_reset_date = ? WHERE id = ?",
                        (today, user['id'])
                    )

                conn.commit()
                return True

        except Exception as e:
            import streamlit as st
            st.warning(f"⚠️ Erreur incrémentation requête: {e}")
            return False

    def get_daily_request_count(self, username):
        """Récupère le nombre de requêtes aujourd'hui SANS incrémenter"""
        user = self.get_user(username)
        if not user:
            return 0

        from datetime import date
        today = date.today().isoformat()

        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    "SELECT request_count FROM daily_requests WHERE user_id = ? AND request_date = ?",
                    (user['id'], today)
                )
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception:
            return 0


    def update_account_type(self, username, account_type):
        """Met à jour le type de compte"""
        sql = "UPDATE users SET account_type = ? WHERE username = ?"

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (account_type, username))
                return cursor.rowcount > 0
        except Exception as e:
            st.error(f"Erreur mise à jour type de compte: {e}")
            return False

    def get_user_stats(self, username):
        """Récupère les statistiques d'un utilisateur"""
        user = self.get_user(username)
        if not user:
            return None

        stats = {
            'account_type': user.get('account_type', 'free'),
            'created_at': user.get('created_at'),
            'archive_count': 0,
            'total_requests_today': 0
        }

        try:
            # Compter les archives
            with self._get_cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) as count FROM chat_archives WHERE user_id = ?",
                    (user['id'],)
                )
                result = cursor.fetchone()
                stats['archive_count'] = result[0] if result else 0
        except Exception:
            stats['archive_count'] = 0

        try:
            # Requêtes aujourd'hui
            with self._get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT SUM(request_count) as total 
                    FROM daily_requests 
                    WHERE user_id = ? AND request_date = DATE('now')
                    """,
                    (user['id'],)
                )
                result = cursor.fetchone()
                stats['total_requests_today'] = result[0] or 0 if result else 0
        except Exception:
            stats['total_requests_today'] = 0

        return stats


    def delete_archive(self, archive_id):
        """Supprime une archive"""
        try:
            with self._get_cursor() as cursor:
                cursor.execute("DELETE FROM chat_archives WHERE id = ?", (archive_id,))
                deleted = cursor.rowcount > 0
                return deleted

        except Exception as e:
            import streamlit as st
            st.error(f"Erreur suppression archive: {e}")
            return False

    def delete_all_archives(self, username):
        """Supprime toutes les archives d'un utilisateur"""
        user = self.get_user(username)
        if not user:
            return False

        try:
            with self._get_cursor() as cursor:
                cursor.execute("DELETE FROM chat_archives WHERE user_id = ?", (user['id'],))
                return True

        except Exception as e:
            import streamlit as st
            st.error(f"Erreur suppression archives: {e}")
            return False


    def export_to_json(self, username):
        """Exporte toutes les archives au format JSON"""
        user = self.get_user(username)
        if not user:
            return "{}"

        archives = self.get_user_archives(username, limit=1000)

        export_data = {
            'username': username,
            'export_date': datetime.now().isoformat(),
            'total_archives': len(archives),
            'archives': archives
        }

        import json
        return json.dumps(export_data, ensure_ascii=False, indent=2)

    def test_connection(self):
        """Teste la connexion à la base de données"""
        try:
            with self._get_cursor() as cursor:
                cursor.execute("SELECT sqlite_version()")
                version = cursor.fetchone()
                return True, f"✅ Connexion SQLite réussie - Version: {version[0]}"
        except Exception as e:
            return False, f"❌ Erreur connexion SQLite: {e}"

    # Méthodes supplémentaires pour compatibilité
    def update_password(self, username, new_password_hash):
        """Met à jour le mot de passe d'un utilisateur"""
        sql = "UPDATE users SET password_hash = ? WHERE username = ?"

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (new_password_hash, username))
                return cursor.rowcount > 0
        except Exception as e:
            st.error(f"Erreur mise à jour mot de passe: {e}")
            return False

    def update_security_data(self, username, q_index, answer_hash):
        """Met à jour les données de sécurité"""
        sql = "UPDATE users SET security_q_index = ?, security_a_hash = ? WHERE username = ?"

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, (q_index, answer_hash, username))
                return cursor.rowcount > 0
        except Exception as e:
            st.error(f"Erreur mise à jour sécurité: {e}")
            return False
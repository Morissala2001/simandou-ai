# modules/archive_manager.py - VERSION MODIFIÉE
import streamlit as st
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import tempfile
import os


class ArchiveManager:
    def __init__(self, database, chat_handler):
        self.db = database
        self.chat_handler = chat_handler

    def render_archive_management(self, username):
        """Affiche l'interface de gestion des archives avec chat"""
        st.header("🗂️ Archives de Conversation")

        archives = self.db.get_user_archives(username, limit=100)

        if not archives:
            st.info("Aucune archive disponible.")
            return

        # Sélection d'archive
        st.subheader("📁 Sélectionner une archive")

        # Créer une liste pour le selectbox
        archive_options = [f"{archive['title']} ({archive['timestamp'][:10]})"
                           for archive in archives]
        archive_ids = [archive['id'] for archive in archives]

        selected_index = st.selectbox(
            "Choisir une archive à consulter",
            range(len(archive_options)),
            format_func=lambda i: archive_options[i]
        )

        if selected_index is not None:
            selected_archive = archives[selected_index]
            self._render_archive_chat(selected_archive, username)

    def _render_archive_chat(self, archive, username):
        """Affiche une archive avec possibilité de poser des questions"""
        st.markdown("---")
        st.subheader(f"💬 {archive['title']}")
        st.caption(f"Archivée le: {archive['timestamp'][:19]}")

        # Boutons d'action
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📥 Télécharger en PDF", key=f"pdf_{archive['id']}"):
                self._generate_pdf(archive, username)

        with col2:
            if st.button("🗑️ Supprimer", key=f"delete_{archive['id']}"):
                if st.session_state.get(f"confirm_delete_{archive['id']}", False):
                    if self.db.delete_archive(archive['id']):
                        st.success("Archive supprimée")
                        st.rerun()
                else:
                    st.session_state[f"confirm_delete_{archive['id']}"] = True

        with col3:
            if st.button("🔙 Retour aux archives", key=f"back_{archive['id']}"):
                st.session_state['selected_archive'] = None
                st.rerun()

        # Confirmation de suppression
        if st.session_state.get(f"confirm_delete_{archive['id']}", False):
            st.warning("⚠️ Voulez-vous vraiment supprimer cette archive?")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Oui, supprimer", key=f"yes_del_{archive['id']}"):
                    if self.db.delete_archive(archive['id']):
                        st.session_state[f"confirm_delete_{archive['id']}"] = False
                        st.rerun()
            with col_no:
                if st.button("Annuler", key=f"no_del_{archive['id']}"):
                    st.session_state[f"confirm_delete_{archive['id']}"] = False
                    st.rerun()

        # Zone de chat pour poser des questions sur cette archive
        st.markdown("### 💭 Poser une question sur cette conversation")

        # Afficher l'historique original
        with st.expander("📜 Historique original de la conversation", expanded=True):
            for msg in archive['history']:
                avatar = "👤" if msg['role'] == 'user' else "🤖"
                with st.chat_message(msg['role'], avatar=avatar):
                    st.write(msg['text'])
                    if 'timestamp' in msg:
                        st.caption(f"_{msg['timestamp'][:19]}_")

        # Zone pour poser des questions
        user_question = st.chat_input(
            f"Posez une question sur cette conversation...",
            key=f"archive_chat_{archive['id']}"
        )

        # Traiter la question
        if user_question:
            self._process_archive_question(user_question, archive, username)

    def _process_archive_question(self, question, archive, username):
        """Traite une question sur une archive"""
        # Afficher la question de l'utilisateur
        with st.chat_message("user", avatar="👤"):
            st.markdown(question)

        try:
            # Préparer le contexte de l'archive
            archive_context = self._prepare_archive_context(archive)

            with st.chat_message("assistant", avatar="🤖"):
                message_placeholder = st.empty()

                with st.spinner("Analyse de l'archive..."):
                    # Créer une requête avec le contexte
                    full_prompt = f"""J'ai une question concernant une conversation archivée:

                    CONTEXTE DE LA CONVERSATION:
                    {archive_context}

                    QUESTION DE L'UTILISATEUR:
                    {question}

                    Veuillez répondre en vous basant uniquement sur le contenu de la conversation archivée.
                    Si la réponse n'est pas dans l'archive, dites-le clairement."""

                    # Utiliser le chat_handler pour la réponse
                    response = self.chat_handler.model.generate_content(full_prompt)

                    message_placeholder.markdown(response.text)

            # Optionnel: Sauvegarder cette interaction
            self._save_archive_interaction(archive['id'], question, response.text, username)

        except Exception as e:
            st.error(f"Erreur lors du traitement de la question: {e}")

    def _prepare_archive_context(self, archive):
        """Prépare le contexte à partir de l'archive"""
        context_lines = []
        for msg in archive['history']:
            role = "Utilisateur" if msg['role'] == 'user' else "Assistant"
            context_lines.append(f"{role}: {msg['text']}")

        return "\n".join(context_lines[:50])  # Limiter à 50 messages max

    def _save_archive_interaction(self, archive_id, question, answer, username):
        """Sauvegarde l'interaction avec l'archive"""
        # Pour l'instant, on ne sauvegarde pas, mais on pourrait le faire
        pass

    def _generate_pdf(self, archive, username):
        """Génère un PDF à partir d'une archive"""
        try:
            # Créer un fichier temporaire pour le PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', mode='wb') as tmp_file:
                pdf_path = tmp_file.name

                # Créer le PDF
                c = canvas.Canvas(pdf_path, pagesize=letter)
                width, height = letter

                # En-tête
                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, height - 50, "Archive Simandou-GN-IA")
                c.setFont("Helvetica", 12)
                c.drawString(50, height - 70, f"Titre: {archive['title']}")
                c.drawString(50, height - 85, f"Date: {archive['timestamp'][:19]}")
                c.drawString(50, height - 100, f"Utilisateur: {username}")

                # Ligne de séparation
                c.line(50, height - 110, width - 50, height - 110)

                # Contenu
                y_position = height - 130
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y_position, "Historique de la conversation:")
                y_position -= 20

                c.setFont("Helvetica", 10)
                for i, msg in enumerate(archive['history'], 1):
                    role = "UTILISATEUR" if msg['role'] == 'user' else "ASSISTANT"
                    text = msg['text']

                    # Vérifier si on doit changer de page
                    if y_position < 100:
                        c.showPage()
                        c.setFont("Helvetica", 10)
                        y_position = height - 50

                    # Écrire le rôle
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(50, y_position, f"{role}:")
                    y_position -= 15

                    # Écrire le texte avec retour à la ligne
                    c.setFont("Helvetica", 10)
                    lines = self._split_text(text, 100)
                    for line in lines:
                        if y_position < 50:
                            c.showPage()
                            c.setFont("Helvetica", 10)
                            y_position = height - 50
                        c.drawString(70, y_position, line)
                        y_position -= 15

                    y_position -= 10  # Espace entre les messages

                # Pied de page
                c.setFont("Helvetica-Oblique", 8)
                c.drawString(50, 30, f"Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                c.drawString(50, 20, "Simandou-GN-IA - L'excellence IA made in Guinée")

                c.save()

            # Proposer le téléchargement
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

            # Créer un bouton de téléchargement
            st.download_button(
                label="📥 Télécharger le PDF",
                data=pdf_bytes,
                file_name=f"archive_{archive['title'][:30]}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key=f"download_pdf_{archive['id']}"
            )

            # Nettoyer le fichier temporaire
            os.unlink(pdf_path)

        except Exception as e:
            st.error(f"Erreur lors de la génération du PDF: {e}")
            # Fallback: Exporter en texte
            self._export_as_text(archive, username)

    def _split_text(self, text, max_line_length):
        """Divise un texte en lignes de longueur maximale"""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            if len(' '.join(current_line + [word])) <= max_line_length:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def _export_as_text(self, archive, username):
        """Exporte l'archive en format texte (fallback)"""
        text_content = f"""Archive Simandou-GN-IA
Titre: {archive['title']}
Date: {archive['timestamp']}
Utilisateur: {username}

Historique de la conversation:
{"=" * 50}

"""

        for msg in archive['history']:
            role = "UTILISATEUR" if msg['role'] == 'user' else "ASSISTANT"
            text_content += f"{role}:\n{msg['text']}\n\n{'=' * 50}\n\n"

        st.download_button(
            label="📄 Télécharger en TXT (fallback)",
            data=text_content,
            file_name=f"archive_{archive['title'][:30]}.txt",
            mime="text/plain",
            key=f"download_txt_{archive['id']}"
        )
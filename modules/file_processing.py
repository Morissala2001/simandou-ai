import os
import time
import tempfile
import mimetypes
import google.generativeai as genai
import streamlit as st


class FileProcessor:
    @staticmethod
    def guess_mime_type(file_path, content_type=None):
        if content_type and content_type != 'application/octet-stream':
            return content_type
        guessed_type, _ = mimetypes.guess_type(file_path)
        if guessed_type:
            return guessed_type
        return 'application/octet-stream'

    @staticmethod
    def upload_to_gemini(file_path, display_name, mime_type_hint=None):
        """Envoie le fichier à l'API Google et gère le nettoyage."""
        temp_file_to_delete = file_path

        try:
            mime_type = FileProcessor.guess_mime_type(file_path, mime_type_hint)

            with st.status("Traitement intelligent en cours...", expanded=True) as status:
                st.write(f"📤 Envoi de **{display_name}** ({mime_type})...")

                gemini_file = genai.upload_file(
                    path=file_path,
                    display_name=display_name,
                    mime_type=mime_type
                )

                st.write("⚙️ Analyse multimodale...")
                while gemini_file.state.name == "PROCESSING":
                    time.sleep(1)
                    gemini_file = genai.get_file(gemini_file.name)

                if gemini_file.state.name == "FAILED":
                    status.update(label="Échec de l'analyse", state="error")
                    try:
                        genai.delete_file(gemini_file.name)
                    except Exception:
                        pass
                    return None

                status.update(label="Document prêt !", state="complete", expanded=False)
            return gemini_file

        except Exception as e:
            st.error(f"Erreur API : {e}")
            return None

        finally:
            # Nettoyer le fichier temporaire local
            if os.path.exists(temp_file_to_delete):
                try:
                    os.unlink(temp_file_to_delete)
                except Exception:
                    pass

    @staticmethod
    def process_uploaded_file(uploaded_file):
        """Traite un fichier uploadé"""
        with st.spinner("Traitement du fichier..."):
            with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=f".{uploaded_file.name.split('.')[-1]}"
            ) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                local_path = tmp_file.name

            ref = FileProcessor.upload_to_gemini(local_path, uploaded_file.name,
                                                 mime_type_hint=uploaded_file.type)

            if ref:
                return ref
        return None
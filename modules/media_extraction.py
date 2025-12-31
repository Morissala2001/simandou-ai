import os
import tempfile
import mimetypes
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import yt_dlp
import streamlit as st


class MediaExtractor:
    @staticmethod
    def extract_youtube_transcript(url):
        """Extrait la transcription/sous-titres d'une vidéo YouTube"""
        try:
            st.toast("Extraction des sous-titres YouTube...", icon="📝")

            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['fr', 'en', 'auto'],
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    st.error("Impossible de récupérer les informations de la vidéo")
                    return None, None, None

                title = info.get('title', 'YouTube_Video')
                subtitles = info.get('subtitles', {}) or info.get('automatic_captions', {})

                transcript_text = ""

                # Priorité: Français -> Anglais -> Première langue disponible
                for lang in ['fr', 'en', 'auto']:
                    if lang in subtitles:
                        for sub in subtitles[lang]:
                            if sub.get('ext') in ['vtt', 'srt']:
                                try:
                                    sub_url = sub.get('url')
                                    if sub_url:
                                        response = requests.get(sub_url, timeout=10)
                                        if response.status_code == 200:
                                            lines = response.text.split('\n')
                                            for line in lines:
                                                if '-->' not in line and line.strip() and not line.strip().isdigit():
                                                    transcript_text += line.strip() + ' '
                                            break
                                except:
                                    continue

                # Si pas de sous-titres, extraire la description
                if not transcript_text:
                    transcript_text = info.get('description', '')
                    if not transcript_text:
                        transcript_text = f"Vidéo YouTube: {title}\n\nPas de transcription disponible."

                # Créer un fichier texte
                with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as tmp_file:
                    tmp_file.write(f"Titre: {title}\n")
                    tmp_file.write(f"URL: {url}\n")
                    tmp_file.write(f"Durée: {info.get('duration', 0)} secondes\n")
                    tmp_file.write(f"Chaîne: {info.get('channel', 'Inconnue')}\n")
                    tmp_file.write(f"Vues: {info.get('view_count', 0)}\n")
                    tmp_file.write("\n" + "=" * 50 + "\n\n")
                    tmp_file.write("TRANSCRIPTION/SOUS-TITRES:\n\n")
                    tmp_file.write(transcript_text[:50000])

                    tmp_file_path = tmp_file.name

                return tmp_file_path, f"{title}_transcription.txt", 'text/plain'

        except Exception as e:
            st.error(f"Erreur d'extraction YouTube: {str(e)[:200]}")
            return None, None, None

    @staticmethod
    def download_youtube_audio(url):
        """Télécharge seulement l'audio YouTube"""
        try:
            st.toast("Téléchargement audio YouTube...", icon="🔊")

            temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(temp_dir, 'audio')

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'extractor_args': {
                    'youtube': {
                        'player_client': ['ios'],
                    }
                },
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if info:
                    title = info.get('title', 'YouTube_Audio')

                    # Chercher le fichier MP3
                    for file in os.listdir(temp_dir):
                        if file.endswith('.mp3'):
                            final_path = os.path.join(temp_dir, file)
                            return final_path, f"{title}.mp3", 'audio/mpeg'

            return None, None, None

        except Exception as e:
            error_msg = str(e)
            if "Sign in" in error_msg or "bot" in error_msg:
                # Essayer l'extraction de transcription à la place
                st.info("YouTube bloque le téléchargement. Extraction de la transcription à la place...")
                return MediaExtractor.extract_youtube_transcript(url)
            else:
                st.error(f"Erreur YouTube: {error_msg[:200]}")
                return None, None, None

    @staticmethod
    def download_file_from_url(url):
        """Télécharge un fichier depuis une URL directe"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }

            with st.spinner(f"Téléchargement depuis {url[:50]}..."):
                response = requests.get(url, stream=True, headers=headers, timeout=30)
                response.raise_for_status()

            content_type = response.headers.get('content-type', '').lower()

            if 'text/html' in content_type:
                st.error("🚫 Lien non direct (c'est une page web). Utilisez l'onglet 'Page Web'.")
                return None, None, None

            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path) or "downloaded_file"

            if not os.path.splitext(filename)[1] and content_type:
                ext = mimetypes.guess_extension(content_type)
                if ext:
                    filename += ext

            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename.replace('.', '_')}") as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
                return tmp_file.name, filename, content_type

        except requests.exceptions.Timeout:
            st.error("⏱️ Délai d'attente dépassé. Le serveur met trop de temps à répondre.")
            return None, None, None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erreur réseau : {str(e)[:100]}")
            return None, None, None
        except Exception as e:
            st.toast(f"❌ Erreur URL : {e}", icon="⚠️")
            return None, None, None

    @staticmethod
    def analyze_webpage_content(url):
        """Extrait le contenu textuel d'une page web"""
        try:
            st.toast("Téléchargement du contenu textuel de la page...", icon="📄")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Supprimer les éléments non pertinents
            for script_or_style in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'iframe', 'form']):
                script_or_style.decompose()

            content = soup.get_text(separator='\n', strip=True)

            if not content or len(content) < 100:
                st.warning("⚠️ Contenu de la page trop court ou non extractible.")
                return None, None, None

            parsed_url = urlparse(url)
            title = soup.title.string if soup.title else "Page Web"

            # Nettoyer le titre pour le nom de fichier
            filename = "".join(c for c in title[:50] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{filename}.txt".replace(' ', '_')

            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as tmp_file:
                tmp_file.write(f"Source URL: {url}\n")
                tmp_file.write(f"Titre: {title}\n")
                tmp_file.write(f"Date d'extraction: {st.session_state.get('extraction_time', '')}\n")
                tmp_file.write("\n" + "=" * 50 + "\n\n")
                tmp_file.write("CONTENU DE LA PAGE:\n\n")
                tmp_file.write(content[:100000])
                tmp_file_path = tmp_file.name

            return tmp_file_path, filename, 'text/plain'

        except requests.exceptions.Timeout:
            st.error("⏱️ Délai d'attente dépassé lors du chargement de la page.")
            return None, None, None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erreur réseau : {str(e)[:100]}")
            return None, None, None
        except Exception as e:
            st.error(f"Erreur d'analyse de la page web : {e}")
            return None, None, None

    @staticmethod
    def is_valid_url(url):
        """Vérifie si une URL est valide"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    @staticmethod
    def get_url_type(url):
        """Détermine le type d'URL"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif url.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            return 'video'
        elif url.endswith(('.mp3', '.wav', '.ogg', '.flac')):
            return 'audio'
        elif url.endswith(('.pdf', '.doc', '.docx', '.txt', '.rtf')):
            return 'document'
        elif url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
            return 'image'
        else:
            # Analyse le content-type
            try:
                response = requests.head(url, timeout=5)
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type:
                    return 'webpage'
                elif 'image/' in content_type:
                    return 'image'
                elif 'video/' in content_type:
                    return 'video'
                elif 'audio/' in content_type:
                    return 'audio'
                elif 'application/pdf' in content_type:
                    return 'pdf'
                else:
                    return 'unknown'
            except:
                return 'webpage'  # Par défaut, considère comme page web
# modules/request_counter.py
import streamlit as st
from datetime import datetime, time, timedelta


class RequestCounter:
    def __init__(self, database):
        self.db = database
        self.MAX_FREE_REQUESTS = 15

    def display_counter(self, username, position="sidebar"):
        """Affiche le compteur de requêtes"""
        if not hasattr(self.db, 'get_daily_request_count'):
            return

        count_today = self.db.get_daily_request_count(username)

        # Calculer le temps jusqu'à la réinitialisation
        now = datetime.now()
        midnight = datetime.combine(now.date() + timedelta(days=1), time.min)
        time_remaining = midnight - now
        hours = time_remaining.seconds // 3600
        minutes = (time_remaining.seconds % 3600) // 60

        # Déterminer la couleur en fonction de l'utilisation
        if count_today >= self.MAX_FREE_REQUESTS:
            color = "🔴"
        elif count_today >= self.MAX_FREE_REQUESTS * 0.8:
            color = "🟠"
        else:
            color = "🟢"

        if position == "sidebar":
            with st.sidebar:
                self._render_counter_widget(count_today, hours, minutes, color)
        else:
            self._render_counter_widget(count_today, hours, minutes, color)

    def _render_counter_widget(self, count, hours, minutes, color):
        """Rendu du widget de compteur"""
        st.markdown(f"### {color} Limite journalière")

        progress = min(count / self.MAX_FREE_REQUESTS, 1.0)
        st.progress(progress)

        st.markdown(f"**{count}/{self.MAX_FREE_REQUESTS}** requêtes utilisées")

        if count >= self.MAX_FREE_REQUESTS:
            st.warning("**Limite atteinte** - Revenez demain !")

        st.caption(f"🕐 Réinitialisation dans **{hours}h{minutes}m**")

    def can_make_request(self, username):
        """Vérifie si une nouvelle requête peut être faite"""
        if not hasattr(self.db, 'get_daily_request_count'):
            return True

        count = self.db.get_daily_request_count(username)
        return count < self.MAX_FREE_REQUESTS

    def get_remaining_requests(self, username):
        """Retourne le nombre de requêtes restantes"""
        if not hasattr(self.db, 'get_daily_request_count'):
            return self.MAX_FREE_REQUESTS

        count = self.db.get_daily_request_count(username)
        return max(0, self.MAX_FREE_REQUESTS - count)
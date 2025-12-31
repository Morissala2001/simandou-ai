# modules/tab_manager.py
import streamlit as st


class TabManager:
    def render_tabs(self, render_chat, render_archives, render_settings):
        """Affiche les onglets de navigation"""
        tabs = ["💬 Chat", "🗂️ Archives", "⚙️ Paramètres"]

        selected_tab = st.radio(
            "Navigation",
            tabs,
            horizontal=True,
            label_visibility="collapsed",
            key="tab_navigation"
        )

        st.divider()

        if selected_tab == "💬 Chat":
            render_chat()
        elif selected_tab == "🗂️ Archives":
            render_archives()
        elif selected_tab == "⚙️ Paramètres":
            render_settings()
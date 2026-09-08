#!/usr/bin/env python3
"""Senato AKN · Dashboard Streamlit"""

import streamlit as st
from lab_connectors.branding import apply_branding

st.set_page_config(
    page_title="Senato AKN · Dashboard",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_branding(
    repo_name="senato-akn",
    repo_url="https://github.com/dataciviclab/senato-akn",
)

pages = {
    "": [
        st.Page("pages/01_Panoramica.py", title="Panoramica", icon="📊", default=True),
    ],
    "Corpus": [
        st.Page("pages/02_Famiglie.py", title="Famiglie", icon="📁"),
        st.Page("pages/03_Emendamenti.py", title="Emendamenti", icon="✏️"),
        st.Page("pages/07_Scheda_Atto.py", title="Scheda Atto", icon="📜"),
    ],
    "Dibattito": [
        st.Page("pages/04_Sedute.py", title="Sedute", icon="🏛️"),
        st.Page("pages/05_Oratori.py", title="Chi Parla", icon="🎤"),
    ],
    "Strumenti": [
        st.Page("pages/06_SQL.py", title="Query SQL", icon="🧪"),
    ],
}

pg = st.navigation(pages, position="sidebar")

pg.run()

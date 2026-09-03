#!/usr/bin/env python3
"""
Senato AKN · Dashboard Streamlit
Il corpus legislativo del Senato italiano — documenti, discorsi, emendamenti.
"""

import streamlit as st

st.set_page_config(
    page_title="Senato AKN · Dashboard",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
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

st.sidebar.markdown("---")
st.sidebar.caption("Dati: [Senato AKoma Ntoso](https://github.com/SenatoDellaRepubblica/AkomaNtosoBulkData)")
st.sidebar.caption("Codice: [dataciviclab/senato-akn](https://github.com/dataciviclab/senato-akn)")
st.sidebar.caption("[DataCivicLab](https://dataciviclab.org/) · CC BY 4.0")

pg.run()

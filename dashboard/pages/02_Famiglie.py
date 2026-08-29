"""Famiglie — Analisi per famiglia legislativa."""

import streamlit as st
from sources import load_mart

st.title("📁 Famiglie Legislative")
st.markdown("Distribuzione degli atti per famiglia legislativa — conteggio vs peso testuale.")

# ── Carica dati ─────────────────────────────────────────────────────
df_fam = load_mart("senato_corpus", "mart_famiglie")
df_per_atto = load_mart("senato_corpus", "mart_per_atto")

if df_fam.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

# ── Treemap ─────────────────────────────────────────────────────────
st.subheader("Distribuzione per famiglia")

try:
    import plotly.express as px
    fig = px.treemap(
        df_fam,
        path=["famiglia"],
        values="testo_totale",
        color="n_documenti",
        title="Peso testuale per famiglia (colore = n. documenti)",
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, width='stretch')
except ImportError:
    st.bar_chart(df_fam.set_index("famiglia")["testo_totale"])

# ── Confronto conteggio vs peso ────────────────────────────────────
st.subheader("Conteggio vs Peso testuale")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Per numero di documenti**")
    st.dataframe(
        df_fam[["famiglia", "n_documenti", "pct_testo"]].rename(columns={
            "famiglia": "Famiglia",
            "n_documenti": "Documenti",
            "pct_testo": "% Testo",
        }),
        width='stretch',
        hide_index=True,
    )

with col2:
    st.markdown("**Per peso testuale**")
    df_sorted = df_fam.sort_values("testo_totale", ascending=False)
    st.dataframe(
        df_sorted[["famiglia", "testo_totale", "n_documenti"]].rename(columns={
            "famiglia": "Famiglia",
            "testo_totale": "Testo (caratteri)",
            "n_documenti": "Documenti",
        }),
        width='stretch',
        hide_index=True,
    )

# ── Dettaglio per famiglia ─────────────────────────────────────────
st.markdown("---")
st.subheader("Top atti per famiglia")

famiglia_sel = st.selectbox("Famiglia", df_fam["famiglia"].tolist())
df_filtered = df_per_atto[df_per_atto["famiglie"].str.contains(famiglia_sel, na=False)]

if not df_filtered.empty:
    st.dataframe(
        df_filtered[["atto_num", "tipologie", "n_documenti", "testo_totale", "articoli_totali"]]
        .sort_values("testo_totale", ascending=False)
        .head(20)
        .rename(columns={
            "atto_num": "Atto",
            "tipologie": "Tipologia",
            "n_documenti": "Documenti",
            "testo_totale": "Testo",
            "articoli_totali": "Articoli",
        }),
        width='stretch',
        hide_index=True,
    )
else:
    st.info("Nessun atto trovato per questa famiglia.")

st.caption("Dati: Senato della Repubblica · Akoma Ntoso Bulk Data · XIX Legislatura · CC BY 4.0")

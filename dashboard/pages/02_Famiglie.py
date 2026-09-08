"""Famiglie — Analisi per famiglia legislativa."""

import streamlit as st
from sources import load_mart, query_clean

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
    st.plotly_chart(fig, width="stretch")
except ImportError:
    st.bar_chart(df_fam.set_index("famiglia")["testo_totale"])

# ── Confronto conteggio vs peso ────────────────────────────────────
st.subheader("Conteggio vs Peso testuale")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Per numero di documenti**")
    st.dataframe(
        df_fam[["famiglia", "n_documenti", "pct_testo"]].rename(
            columns={
                "famiglia": "Famiglia",
                "n_documenti": "Documenti",
                "pct_testo": "% Testo",
            }
        ),
        width="stretch",
        hide_index=True,
    )

with col2:
    st.markdown("**Per peso testuale**")
    df_sorted = df_fam.sort_values("testo_totale", ascending=False)
    st.dataframe(
        df_sorted[["famiglia", "testo_totale", "n_documenti"]].rename(
            columns={
                "famiglia": "Famiglia",
                "testo_totale": "Testo (caratteri)",
                "n_documenti": "Documenti",
            }
        ),
        width="stretch",
        hide_index=True,
    )

# ── Dettaglio per famiglia ─────────────────────────────────────────
st.markdown("---")
st.subheader("Top atti per famiglia")

famiglia_sel = st.selectbox("Famiglia", df_fam["famiglia"].tolist())

df_per_atto = query_clean(
    "senato_corpus",
    "SELECT atto_num, tipologia, doc_title, text_len, articles_count, famiglia "
    "FROM clean_input WHERE famiglia IS NOT NULL AND famiglia != ''",
)
df_filtered = df_per_atto[df_per_atto["famiglia"].str.contains(famiglia_sel, na=False)]

if not df_filtered.empty:
    df_show = (
        df_filtered[["atto_num", "tipologia", "doc_title", "text_len", "articles_count"]]
        .head(20)
        .copy()
    )
    df_show.columns = ["Atto", "Tipo", "Titolo", "Testo", "Articoli"]
    df_show["Titolo"] = df_show["Titolo"].str[:60]
    st.dataframe(df_show, width="stretch", hide_index=True)

else:
    st.info("Nessun atto trovato per questa famiglia.")

st.caption("Dati: Senato della Repubblica · Akoma Ntoso Bulk Data · Leg14-Leg19 · CC BY 4.0")

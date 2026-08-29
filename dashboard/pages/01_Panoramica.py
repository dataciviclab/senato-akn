"""Panoramica — KPI del corpus legislativo del Senato."""

import streamlit as st
from lab_connectors.formatters import fmt_num
from sources import load_clean, load_mart

st.title("📊 Panoramica Corpus Senato")
st.markdown("Legislatura XIX — il corpus legislativo del Senato italiano da Akoma Ntoso.")

# ── Carica dati ─────────────────────────────────────────────────────
df_corpus = load_clean("senato_corpus")
df_dibattito = load_clean("senato_dibattito")
df_emendamenti = load_clean("senato_emendamenti")
df_famiglie = load_mart("senato_corpus", "mart_famiglie")

# ── KPI ─────────────────────────────────────────────────────────────
n_doc = len(df_corpus)
n_discorsi = len(df_dibattito)
n_emend = len(df_emendamenti)
testo_totale = df_corpus["text_len"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric("📄 Documenti", fmt_num(n_doc))
k2.metric("🎤 Discorsi", fmt_num(n_discorsi))
k3.metric("✏️ Emendamenti", fmt_num(n_emend))
k4.metric("📝 Testo totale", f"{testo_totale/1e6:,.1f} M caratteri")

st.markdown("---")

# ── Distribuzione per famiglia ──────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Documenti per famiglia")
    if not df_famiglie.empty:
        import altair as alt
        chart = (
            alt.Chart(df_famiglie)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("n_documenti:Q", title="N. documenti"),
                y=alt.Y("famiglia:N", title="", sort="-x"),
                color=alt.Color("famiglia:N", legend=None),
                tooltip=["famiglia", alt.Tooltip("n_documenti:Q", format=",")],
            )
            .properties(height=300)
        )
        st.altair_chart(chart, width='stretch')

with col_right:
    st.subheader("Peso testuale per famiglia")
    if not df_famiglie.empty:
        chart2 = (
            alt.Chart(df_famiglie)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#f59e0b")
            .encode(
                x=alt.X("testo_totale:Q", title="Testo (caratteri)", axis=alt.Axis(format="~s")),
                y=alt.Y("famiglia:N", title="", sort="-x"),
                tooltip=["famiglia", alt.Tooltip("testo_totale:Q", format=",")],
            )
            .properties(height=300)
        )
        st.altair_chart(chart2, width='stretch')

# ── Il finding chiave ──────────────────────────────────────────────
st.markdown("---")
st.subheader("Il peso nascosto dei bilanci")

if not df_famiglie.empty:
    bilanci = df_famiglie[df_famiglie["famiglia"] == "bilancio"]
    if not bilanci.empty:
        n_bilanci = int(bilanci["n_documenti"].iloc[0])
        pct_count = n_bilanci / n_doc * 100
        testo_bilanci = int(bilanci["testo_totale"].iloc[0])
        testo_medio = testo_bilanci / n_bilanci if n_bilanci else 0
        testo_medio_gen = testo_totale / n_doc if n_doc else 0
        peso_relativo = testo_medio / testo_medio_gen if testo_medio_gen else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Bilanci", f"{n_bilanci} ({pct_count:.1f}% degli atti)")
        c2.metric("Testo medio/bilancio", f"{testo_medio:,.0f} caratteri")
        c3.metric("Peso vs media", f"{peso_relativo:.1f}x")

        import pandas as pd
        import altair as alt

        df_confronto = pd.DataFrame({
            "Categoria": ["Bilanci", "Media generale"],
            "Testo medio (caratteri)": [testo_medio, testo_medio_gen],
        })
        chart_confronto = (
            alt.Chart(df_confronto)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Categoria:N", title=""),
                y=alt.Y("Testo medio (caratteri):Q", title="Testo medio per documento"),
                color=alt.Color(
                    "Categoria:N",
                    scale=alt.Scale(domain=["Bilanci", "Media generale"], range=["#f59e0b", "#6b7280"]),
                    legend=None,
                ),
                tooltip=["Categoria", alt.Tooltip("Testo medio (caratteri):Q", format=",")],
            )
            .properties(height=300)
        )
        st.altair_chart(chart_confronto, width='stretch')

st.caption("Dati: Senato della Repubblica · Akoma Ntoso Bulk Data · XIX Legislatura · CC BY 4.0")

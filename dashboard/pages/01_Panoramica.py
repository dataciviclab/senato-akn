"""Panoramica — KPI del corpus legislativo del Senato."""

import streamlit as st
from sources import load_mart

st.title("Panoramica Corpus Senato")
st.markdown("Legislature XIV–XIX — il corpus legislativo del Senato italiano da Akoma Ntoso.")

# ── Carica marts (leggeri) ─────────────────────────────────────────
df_corpus = load_mart("senato_corpus", "mart_per_atto")
df_famiglie = load_mart("senato_corpus", "mart_famiglie")
df_emend = load_mart("senato_emendamenti", "mart_emendamenti_per_fase")
df_leg = load_mart("senato_corpus", "mart_per_legislatura")
df_dib_sedute = load_mart("senato_dibattito", "mart_dibattito_per_seduta")
df_oratori = load_mart("senato_dibattito", "mart_interventi_per_persona")

# ── KPI ─────────────────────────────────────────────────────────────
n_doc = int(df_corpus["n_documenti"].sum())
testo_totale = int(df_corpus["testo_totale"].sum())
n_emend = int(df_emend["n_emend"].sum()) if not df_emend.empty else 0
n_discorsi = int(df_dib_sedute["n_interventi"].sum()) if not df_dib_sedute.empty else 0
n_oratori = len(df_oratori) if not df_oratori.empty else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Documenti", f"{n_doc:,}")
k2.metric("Emendamenti", f"{n_emend:,}")
k3.metric("Discorsi", f"{n_discorsi:,}")
k4.metric("Oratori", f"{n_oratori:,}")
k5.metric("Testo", f"{testo_totale/1e6:,.1f} M")

st.markdown("---")

# ── Distribuzione per famiglia ──────────────────────────────────────
top_n_fam = st.slider("Top famiglie", 5, 30, 15, key="top_fam")
df_top_fam = df_famiglie.nlargest(top_n_fam, "n_documenti")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Documenti per famiglia")
    if not df_top_fam.empty:
        import altair as alt
        chart = (
            alt.Chart(df_top_fam)
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
    if not df_top_fam.empty:
        chart2 = (
            alt.Chart(df_top_fam)
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

        import altair as alt
        import pandas as pd

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

st.caption("Dati: Senato della Repubblica · Akoma Ntoso Bulk Data · CC BY 4.0")

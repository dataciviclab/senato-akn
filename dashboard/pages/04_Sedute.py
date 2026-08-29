"""Sedute — Attività per sessione del Senato."""

import streamlit as st
from lab_connectors.formatters import fmt_num
from sources import load_mart

st.title("🏛️ Attività per Seduta")
st.markdown("Intensità dei dibattiti nel tempo — chi parla, quanto si discute.")

# ── Carica dati ─────────────────────────────────────────────────────
df = load_mart("senato_dibattito", "mart_dibattito_per_seduta")

if df.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

# ── KPI ─────────────────────────────────────────────────────────────
n_sedute = len(df)
tot_interventi = df["n_interventi"].sum()
tot_oratori = df["n_oratori"].sum()
media_interventi = tot_interventi / n_sedute if n_sedute else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Sedute", fmt_num(n_sedute))
k2.metric("Interventi totali", fmt_num(tot_interventi))
k3.metric("Oratori totali", fmt_num(tot_oratori))
k4.metric("Media interventi/seduta", f"{media_interventi:.0f}")

st.markdown("---")

# ── Trend nel tempo ────────────────────────────────────────────────
st.subheader("Interventi per seduta")

df_sorted = df.sort_values("data_seduta")

try:
    import altair as alt
    chart = (
        alt.Chart(df_sorted)
        .mark_line(point=True, color="#6366f1", strokeWidth=1.5)
        .encode(
            x=alt.X("data_seduta:T", title="Data"),
            y=alt.Y("n_interventi:Q", title="N. interventi"),
            tooltip=[
                alt.Tooltip("data_seduta:T", title="Data", format="%d/%m/%Y"),
                alt.Tooltip("n_interventi:Q", title="Interventi", format=","),
                alt.Tooltip("n_oratori:Q", title="Oratori"),
            ],
        )
        .properties(height=350)
    )
    st.altair_chart(chart, width='stretch')
except ImportError:
    st.line_chart(df_sorted.set_index("data_seduta")["n_interventi"])

# ── Top sedute ─────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Sedute più lunghe (per testo)")
    df_top_testo = df.nlargest(10, "testo_totale")
    st.dataframe(
        df_top_testo[["data_seduta", "n_interventi", "n_oratori", "testo_totale"]].rename(columns={
            "data_seduta": "Data",
            "n_interventi": "Interventi",
            "n_oratori": "Oratori",
            "testo_totale": "Testo",
        }),
        width='stretch',
        hide_index=True,
    )

with col2:
    st.subheader("Sedute più attive (per interventi)")
    df_top_n = df.nlargest(10, "n_interventi")
    st.dataframe(
        df_top_n[["data_seduta", "n_interventi", "n_oratori", "n_canali"]].rename(columns={
            "data_seduta": "Data",
            "n_interventi": "Interventi",
            "n_oratori": "Oratori",
            "n_canali": "Canali",
        }),
        width='stretch',
        hide_index=True,
    )

st.caption("Dati: Senato della Repubblica · Akoma Ntoso Bulk Data · XIX Legislatura · CC BY 4.0")

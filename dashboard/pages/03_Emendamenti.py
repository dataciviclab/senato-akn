"""Emendamenti — Intensità emendativa per atto e fase."""

import streamlit as st
from lab_connectors.formatters import fmt_num
from sources import load_mart

st.title("✏️ Emendamenti")
st.markdown("137k emendamenti — intensità per atto, split aula vs commissione.")

# ── Carica dati ─────────────────────────────────────────────────────
df = load_mart("senato_emendamenti", "mart_emendamenti_per_atto")

if df.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

# ── KPI ─────────────────────────────────────────────────────────────
n_emend = df["n_emend"].sum()
n_aula = df["n_aula"].sum()
n_commissione = df["n_commissione"].sum()
n_target = df["n_target_distinti"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Emendamenti totali", fmt_num(n_emend))
k2.metric("In Aula", fmt_num(n_aula))
k3.metric("In Commissione", fmt_num(n_commissione))
k4.metric("Atti emendati", fmt_num(n_target))

st.markdown("---")

# ── Top atti per emendamenti ────────────────────────────────────────
st.subheader("Top atti per intensità emendativa")

top_n = st.slider("Top N", 5, 30, 15)
df_top = df.nlargest(top_n, "n_emend")

try:
    import altair as alt
    df_melted = df_top[["fase", "n_aula", "n_commissione"]].melt(
        id_vars="fase", var_name="Camera", value_name="n_emend"
    )
    df_melted["Camera"] = df_melted["Camera"].map({"n_aula": "Aula", "n_commissione": "Commissione"})
    chart = (
        alt.Chart(df_melted)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("n_emend:Q", title="N. emendamenti", stack="zero"),
            y=alt.Y("fase:N", title="", sort="-x"),
            color=alt.Color(
                "Camera:N",
                scale=alt.Scale(domain=["Aula", "Commissione"], range=["#6366f1", "#10b981"]),
            ),
            tooltip=["fase", "Camera", alt.Tooltip("n_emend:Q", format=",")],
        )
        .properties(height=max(250, top_n * 25))
    )
    st.altair_chart(chart, width='stretch')
except ImportError:
    st.bar_chart(df_top.set_index("fase")["n_emend"])

# ── Dettaglio tabellare ────────────────────────────────────────────
st.subheader("Dettaglio")

df_display = df.nlargest(50, "n_emend")[
    ["fase", "n_emend", "testo_totale", "testo_medio", "n_aula", "n_commissione"]
].rename(columns={
    "fase": "Fase",
    "n_emend": "Emendamenti",
    "testo_totale": "Testo totale",
    "testo_medio": "Testo medio",
    "n_aula": "Aula",
    "n_commissione": "Commissione",
})

st.dataframe(df_display, width='stretch', hide_index=True)

st.caption("Dati: Senato della Repubblica · Akoma Ntoso Bulk Data · XIX Legislatura · CC BY 4.0")

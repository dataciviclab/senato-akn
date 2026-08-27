"""Chi Parla — Top oratori e distribuzione interventi."""

import streamlit as st
from lab_connectors.formatters import fmt_num
from sources import load_mart

st.title("🎤 Chi Parla")
st.markdown("250 senatori nel corpus dibattito — chi parla di più, dove, e quanto dice.")

# ── Carica dati ─────────────────────────────────────────────────────
df = load_mart("senato_dibattito", "mart_interventi_per_persona")

if df.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

# ── Filtri ──────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    min_interventi = st.slider("Min. interventi", 1, 100, 5)
with col2:
    sort_by = st.selectbox("Ordina per", ["n_interventi", "testo_totale", "n_sedute"])

df_f = df[df["n_interventi"] >= min_interventi].sort_values(sort_by, ascending=False)

# ── KPI ─────────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
k1.metric("Senatori attivi", fmt_num(len(df_f)))
k2.metric("Media interventi/senatore", f"{df_f['n_interventi'].mean():.0f}" if not df_f.empty else "—")
k3.metric("Media testo/senatore", f"{df_f['testo_totale'].mean():,.0f}" if not df_f.empty else "—")

st.markdown("---")

# ── Top oratori ─────────────────────────────────────────────────────
st.subheader("Top oratori")

try:
    import altair as alt
    top = df_f.head(20)
    chart = (
        alt.Chart(top)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#6366f1")
        .encode(
            x=alt.X(f"{sort_by}:Q", title=sort_by.replace("_", " ").title(), axis=alt.Axis(format="~s")),
            y=alt.Y("nome_oratore:N", title="", sort="-x"),
            tooltip=["nome_oratore", alt.Tooltip("n_interventi:Q", title="Interventi", format=",")],
        )
        .properties(height=max(300, 20 * 20))
    )
    st.altair_chart(chart, use_container_width=True)
except ImportError:
    st.bar_chart(df_f.head(20).set_index("nome_oratore")[sort_by])

# ── Aula vs Commissione ────────────────────────────────────────────
st.subheader("Distribuzione Aula vs Commissione")

df_ratio = df_f.head(30).copy()
df_ratio["pct_aula"] = df_ratio["n_aula"] / df_ratio["n_interventi"] * 100

st.dataframe(
    df_ratio[["nome_oratore", "n_interventi", "n_aula", "n_commissione", "pct_aula", "testo_totale"]]
    .rename(columns={
        "nome_oratore": "Senatore",
        "n_interventi": "Interventi",
        "n_aula": "Aula",
        "n_commissione": "Commissione",
        "pct_aula": "% Aula",
        "testo_totale": "Testo",
    }),
    use_container_width=True,
    hide_index=True,
)

st.caption("Dati: Senato della Repubblica · Akoma Ntoso Bulk Data · XIX Legislatura · CC BY 4.0")

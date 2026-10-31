"""Emendamenti — Intensità emendativa per atto (fase S.NNN)."""

import altair as alt
import pandas as pd
import streamlit as st
from lab_connectors.formatters import fmt_num
from sources import load_mart, query_clean

st.title("Emendamenti")
st.markdown("Intensità emendativa per atto — split aula vs commissione.")
st.caption(
    "Una riga per atto (`fase` S.NNN), deduplicata dalle copie che l'upstream "
    "replica in più directory Atto. `atto_num` è la directory, non l'atto."
)

# ── Carica dati (chiave canonica: fase S.NNN) ──────────────────────
per_fase = True
try:
    df = load_mart("senato_emendamenti", "mart_emendamenti_per_fase")
except Exception:
    # snapshot pubblicato prima del passaggio a fase: mart legacy per directory
    per_fase = False
    df = load_mart("senato_emendamenti", "mart_emendamenti_per_atto")

if df.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

# ── Arricchisci con il titolo dal corpus ───────────────────────────
if per_fase:
    df_titles = pd.DataFrame(columns=["legislatura", "fase", "doc_title"])
    try:
        df_titles = query_clean("senato_corpus",
            "SELECT legislatura, fase, MIN(doc_title) AS doc_title "
            "FROM clean_input WHERE fase IS NOT NULL GROUP BY 1, 2")
    except Exception:
        pass
    if not df_titles.empty:
        df = df.merge(df_titles, on=["legislatura", "fase"], how="left")
    df["label"] = df.apply(
        lambda r: f"{r['fase']} — {str(r.get('doc_title'))[:50]}"
        if pd.notna(r.get("doc_title")) else str(r["fase"]),
        axis=1,
    )
else:
    df_titles = query_clean("senato_corpus",
        "SELECT atto_num, MIN(doc_title) AS doc_title FROM clean_input "
        "WHERE atto_num IS NOT NULL GROUP BY atto_num")
    df = df.merge(df_titles, on="atto_num", how="left")
    df["label"] = df.apply(
        lambda r: f"S.{int(r['atto_num'])} — {str(r.get('doc_title', ''))[:50]}"
        if pd.notna(r.get("doc_title")) else f"S.{int(r['atto_num'])}",
        axis=1,
    )

# ── KPI ─────────────────────────────────────────────────────────────
n_emend = int(df["n_emend"].sum())
n_aula = int(df["n_aula"].sum())
n_commissione = int(df["n_commissione"].sum())
n_atti = len(df)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Emendamenti totali", fmt_num(n_emend))
k2.metric("In Aula", fmt_num(n_aula))
k3.metric("In Commissione", fmt_num(n_commissione))
k4.metric("Atti emendati", fmt_num(n_atti))

st.markdown("---")

# ── Top atti per emendamenti ────────────────────────────────────────
st.subheader("Top atti per intensità emendativa")

top_n = st.slider("Top N", 5, 30, 15)
df_top = df.nlargest(top_n, "n_emend").copy()

df_melted = df_top[["label", "n_aula", "n_commissione"]].melt(
    id_vars="label", var_name="Camera", value_name="n_emend"
)
df_melted["Camera"] = df_melted["Camera"].map({"n_aula": "Aula", "n_commissione": "Commissione"})

chart = (
    alt.Chart(df_melted)
    .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
    .encode(
        x=alt.X("n_emend:Q", title="N. emendamenti", stack="zero"),
        y=alt.Y("label:N", title="", sort="-x"),
        color=alt.Color("Camera:N",
                       scale=alt.Scale(domain=["Aula", "Commissione"],
                                       range=["#6366f1", "#10b981"])),
        tooltip=["label", "Camera", alt.Tooltip("n_emend:Q", format=",")],
    )
    .properties(height=max(250, top_n * 25))
)
st.altair_chart(chart, width='stretch')

# ── Dettaglio tabellare ────────────────────────────────────────────
st.subheader("Dettaglio")

df_display = df.nlargest(50, "n_emend").copy()
if per_fase:
    df_display["Atto"] = df_display["fase"]
else:
    df_display["Atto"] = df_display["atto_num"].apply(lambda x: f"S.{int(x)}")
df_display["Titolo"] = df_display.get("doc_title", pd.Series(dtype=str)).str[:50]

st.dataframe(
    df_display[["Atto", "Titolo", "n_emend", "n_aula", "n_commissione", "testo_totale"]]
    .rename(columns={
        "n_emend": "Emendamenti",
        "n_aula": "Aula",
        "n_commissione": "Commissione",
        "testo_totale": "Testo",
    }),
    width='stretch', hide_index=True
)

st.caption("Dati: Senato della Repubblica · Akoma Ntoso Bulk Data · CC BY 4.0")

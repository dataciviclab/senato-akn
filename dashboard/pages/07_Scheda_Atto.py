"""Scheda Atto — Vista completa di un singolo atto legislativo."""

import streamlit as st
from lab_connectors.formatters import fmt_num
from sources import load_mart, query_clean

# ── Selezione atto ─────────────────────────────────────────────────
df_mart = load_mart("senato_corpus", "mart_per_atto")
atti = df_mart[["atto_num"]].dropna().copy()
atti["atto_num"] = atti["atto_num"].astype(int)
atti = atti.sort_values("atto_num", ascending=False)

atto_num = int(st.selectbox("Seleziona atto", atti["atto_num"].tolist(),
                             format_func=lambda x: f"S.{x}"))

# ── Query: tutto filtrato per atto_num ─────────────────────────────
atto_corpus = query_clean("senato_corpus",
    f"SELECT doc_title, tipologia, famiglia, work_date, text_len, "
    f"articles_count, paragraphs_count "
    f"FROM clean_input WHERE atto_num = {atto_num} LIMIT 1")

atto_dib = query_clean("senato_dibattito",
    f"SELECT nome_oratore, senatore_id, tipologia, text_len, data_seduta "
    f"FROM clean_input WHERE atto_num = {atto_num}")

atto_emend = query_clean("senato_emendamenti",
    f"SELECT COUNT(*) as n_emend, "
    f"SUM(CASE WHEN tipologia='emend' THEN 1 ELSE 0 END) as n_aula, "
    f"SUM(CASE WHEN tipologia='emendc' THEN 1 ELSE 0 END) as n_commissione, "
    f"SUM(text_len) as testo_emend "
    f"FROM clean_input WHERE atto_num = {atto_num}")

# ── Estrai dati ────────────────────────────────────────────────────
if not atto_corpus.empty:
    r = atto_corpus.iloc[0]
    doc_title = str(r.get("doc_title", "")) or f"Atto S.{atto_num}"
    famiglia = str(r.get("famiglia", "")) or "—"
    work_date = str(r.get("work_date", ""))[:10] or "—"
    text_len = int(r["text_len"]) if r.get("text_len") else 0
    articles_count = int(r["articles_count"]) if r.get("articles_count") else 0
else:
    doc_title, famiglia, work_date, text_len, articles_count = f"Atto S.{atto_num}", "—", "—", 0, 0

n_interventi = len(atto_dib)
n_oratori = int(atto_dib["senatore_id"].nunique()) if n_interventi > 0 else 0
testo_dib = int(atto_dib["text_len"].sum()) if n_interventi > 0 else 0

n_emend = int(atto_emend["n_emend"].sum()) if not atto_emend.empty else 0
n_aula = int(atto_emend["n_aula"].sum()) if not atto_emend.empty else 0
n_commissione = int(atto_emend["n_commissione"].sum()) if not atto_emend.empty else 0
testo_emend = int(atto_emend["testo_emend"].sum()) if not atto_emend.empty else 0

# ── Header ─────────────────────────────────────────────────────────
st.title(f"S.{atto_num}")
st.subheader(doc_title)
st.caption(f"**{famiglia}** · {work_date} · {articles_count} articoli")
st.markdown("---")

# ── KPI ─────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Testo", f"{text_len:,} car." if text_len else "—")
k2.metric("Emendamenti", fmt_num(n_emend))
k3.metric("Interventi", fmt_num(n_interventi))
k4.metric("Oratori", fmt_num(n_oratori))
k5.metric("Emend aula/commiss.", f"{n_aula}/{n_commissione}")

st.markdown("---")

# ── Emendamenti ────────────────────────────────────────────────────
if n_emend > 0:
    st.subheader("Emendamenti")
    c1, c2, c3 = st.columns(3)
    c1.metric("Aula", fmt_num(n_aula))
    c2.metric("Commissione", fmt_num(n_commissione))
    if text_len > 0:
        c3.metric("Rapporto emend/testo", f"{testo_emend/text_len:.2f}x")

st.markdown("---")

# ── Dibattito ──────────────────────────────────────────────────────
if n_interventi > 0:
    st.subheader("Dibattito — Chi parla")

    top = (atto_dib.groupby("nome_oratore")
           .agg(n=("text_len", "count"), testo=("text_len", "sum"))
           .nlargest(10, "n"))

    import altair as alt
    chart = alt.Chart(top.reset_index()).mark_bar().encode(
        x=alt.X("n:Q", title="Interventi"),
        y=alt.Y("nome_oratore:N", title="", sort="-x"),
        tooltip=["nome_oratore", "n"],
    ).properties(height=max(200, len(top) * 25))
    st.altair_chart(chart, use_container_width=True)

    st.subheader("Dettaglio interventi")
    st.dataframe(
        atto_dib[["data_seduta", "nome_oratore", "tipologia", "text_len"]].rename(columns={
            "data_seduta": "Data", "nome_oratore": "Oratore",
            "tipologia": "Tipo", "text_len": "Car.",
        }),
        width="stretch", hide_index=True
    )
else:
    st.info("Nessun intervento di dibattito per questo atto.")

st.caption("Dati: Senato della Repubblica · Akoma Ntoso Bulk Data · CC BY 4.0")

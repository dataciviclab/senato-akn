"""Scheda Atto — Vista completa di un singolo atto legislativo."""

import re

import pandas as pd
import streamlit as st
from lab_connectors.formatters import fmt_num
from sources import load_clean, load_mart, load_senato_ddl

st.set_page_config(page_title="Scheda Atto · Senato AKN", page_icon="📜", layout="wide")

# ── Helper ──────────────────────────────────────────────────────────

def normalize_atto_num(raw) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    s = str(raw).strip()
    m = re.match(r"^S\.(\d+)$", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^Atto0+(\d+)$", s)
    if m:
        return int(m.group(1))
    try:
        return int(s)
    except ValueError:
        return None


# ── Carica dati ─────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _load_all():
    return (
        load_clean("senato_corpus"),
        load_clean("senato_emendamenti"),
        load_clean("senato_dibattito"),
        load_mart("senato_emendamenti", "mart_emendamenti_per_atto"),
        load_senato_ddl(),
    )

df_corpus, df_emend, df_dibattito, df_mart_emend, df_ddl = _load_all()

# Pre-elabora: estrai atto_num da dibattito
df_dibattito["_atto_num"] = df_dibattito["path"].apply(
    lambda x: normalize_atto_num(re.search(r"Atto0+(\d+)", str(x)).group(1))
    if re.search(r"Atto0+(\d+)", str(x)) else None
)

# Pre-elabora emendamenti: raggruppa per fase
emend_summary = (
    df_emend.groupby("fase")
    .agg(n_emend=("text_len", "count"),
         n_aula=("tipologia", lambda x: (x == "emend").sum()),
         n_commissione=("tipologia", lambda x: (x == "emendc").sum()),
         testo=("text_len", "sum"))
    .reset_index()
)

# Bridge: emendamenti ↔ senato_ddl (via fase)
df_ddl_s = df_ddl[df_ddl["fase"].str.startswith("S.", na=False)].copy()
emend_bridge = emend_summary.merge(
    df_ddl_s[["fase", "id_ddl", "titolo", "stato", "natura", "numero_legge",
              "data_legge", "ramo", "iniziativa", "descr_iniziativa",
              "data_presentazione", "data_stato_ddl"]],
    on="fase", how="left"
)

# ── Combina tutti gli atti per la selezione ────────────────────────

atti_corpus = df_corpus[["atto_num", "doc_title", "famiglia"]].drop_duplicates("atto_num")

atti_dib = (
    df_dibattito[["_atto_num"]]
    .dropna()
    .drop_duplicates()
    .rename(columns={"_atto_num": "atto_num"})
)

atti_emend = emend_bridge.copy()
atti_emend = atti_emend.rename(columns={"fase": "atto_fase"})
atti_emend["atto_num"] = atti_emend["id_ddl"]
atti_emend["doc_title"] = atti_emend["titolo"].fillna(
    atti_emend["atto_fase"].apply(lambda x: f"Emendamenti {x}")
)
atti_emend["famiglia"] = None

# Unisci: corpus + dibattito + emend-bridge (deduplicati)
atti_all = pd.concat([
    atti_corpus,
    atti_dib[["atto_num"]],
    atti_emend[["atto_num", "doc_title", "famiglia"]],
], ignore_index=True)
atti_all = atti_all.drop_duplicates(subset="atto_num", keep="first")
atti_options = atti_all.sort_values("atto_num", ascending=False)

# ── Sidebar / selezione ────────────────────────────────────────────

col_fam, col_atto = st.columns([1, 3])

with col_fam:
    famiglie = ["Tutte"] + sorted(
        atti_options["famiglia"].dropna().unique().tolist()
    )
    famiglia_sel = st.selectbox("Famiglia", famiglie, index=0)

if famiglia_sel != "Tutte":
    atti_filtrati = atti_options[atti_options["famiglia"] == famiglia_sel]
else:
    atti_filtrati = atti_options

def format_atto(row):
    title = str(row["doc_title"])[:70]
    return f"S.{int(row['atto_num'])} — {title}"

atti_filtrati = atti_filtrati.copy()
atti_filtrati["_label"] = atti_filtrati.apply(format_atto, axis=1)

with col_atto:
    atto_label = st.selectbox(
        "Seleziona atto",
        atti_filtrati["_label"].tolist(),
        index=0,
    )

atto_num = int(atti_filtrati.iloc[atti_filtrati["_label"] == atto_label]["atto_num"].iloc[0])

# ── Dati atto ───────────────────────────────────────────────────────

# Corpus
atto_corpus = df_corpus[df_corpus["atto_num"] == atto_num]

# Emendamenti via bridge: cerca fase in emend_summary dove id_ddl = atto_num
emend_atto = emend_bridge[emend_bridge["id_ddl"] == atto_num]
if emend_atto.empty:
    # Fallback: atto_num usato direttamente come fase (S.{atto_num})
    emend_atto = emend_summary[emend_summary["fase"] == f"S.{atto_num}"]

n_emend = int(emend_atto["n_emend"].sum()) if not emend_atto.empty else 0
n_aula = int(emend_atto["n_aula"].sum()) if not emend_atto.empty else 0
n_commissione = int(emend_atto["n_commissione"].sum()) if not emend_atto.empty else 0
testo_emend = int(emend_atto["testo"].sum()) if not emend_atto.empty else 0

# DDL metadata (stato, numero_legge, etc.)
atto_ddl = df_ddl[df_ddl["id_ddl"] == atto_num] if not atto_corpus.empty else pd.DataFrame()
if atto_ddl.empty:
    atto_ddl = df_ddl_s[df_ddl_s["fase"] == f"S.{atto_num}"]

stato_iter = atto_ddl["stato"].iloc[0] if not atto_ddl.empty else None
numero_legge = atto_ddl["numero_legge"].iloc[0] if not atto_ddl.empty else None
data_legge = atto_ddl["data_legge"].iloc[0] if not atto_ddl.empty else None
natura = atto_ddl["natura"].iloc[0] if not atto_ddl.empty else None
descr_iniziativa = atto_ddl["descr_iniziativa"].iloc[0] if not atto_ddl.empty else None

# Dibattito
dib_atto = df_dibattito[df_dibattito["_atto_num"] == atto_num]
n_interventi = len(dib_atto)
testo_dibattito = int(dib_atto["text_len"].sum()) if n_interventi > 0 else 0
n_oratori = dib_atto["senatore_id"].nunique() if n_interventi > 0 else 0

# Dati dal corpus (se disponibile)
if not atto_corpus.empty:
    atto_row = atto_corpus.iloc[0]
    doc_title = atto_row["doc_title"]
    famiglia = atto_row.get("famiglia", "—")
    work_date = atto_row.get("work_date", "—")
    text_len = int(atto_row.get("text_len", 0))
    articles_count = int(atto_row.get("articles_count", 0))
    paragraphs_count = int(atto_row.get("paragraphs_count", 0))
elif emend_atto is not None and not emend_atto.empty:
    # Titolo dal bridge senato_ddl
    doc_title = emend_atto["titolo"].iloc[0] if pd.notna(emend_atto["titolo"].iloc[0]) else f"Atto S.{atto_num}"
    famiglia = "—"
    work_date = str(emend_atto["data_presentazione"].iloc[0])[:10] if pd.notna(emend_atto["data_presentazione"].iloc[0]) else "—"
    text_len = 0
    articles_count = 0
    paragraphs_count = 0
else:
    doc_title = f"Atto S.{atto_num}"
    famiglia = "—"
    work_date = "—"
    text_len = 0
    articles_count = 0
    paragraphs_count = 0

# ── Header ─────────────────────────────────────────────────────────

st.title(f"📜 S.{atto_num}")
st.subheader(doc_title)

if atto_corpus.empty:
    st.caption("Dato da senato_ddl (open-politica) — non nel corpus ddlpres di senato-akn")

meta_cols = st.columns(3 if stato_iter else 4 if not atto_corpus.empty else 3)
idx = 0
meta_cols[idx].metric("Famiglia", famiglia)
idx += 1
meta_cols[idx].metric("Data presentazione", str(work_date)[:10] if work_date != "—" else "—")
idx += 1
meta_cols[idx].metric("Articoli", fmt_num(articles_count))
idx += 1

if stato_iter:
    leg_label = f"Legge n. {int(numero_legge)}" if numero_legge and int(numero_legge) > 0 else "—"
    meta_cols[idx].metric("Stato", stato_iter)
    if numero_legge and int(numero_legge) > 0:
        meta_cols[idx].metric("Esito", leg_label)
elif not atto_corpus.empty:
    meta_cols[idx].metric("Esito", "In iter")

st.markdown("---")

# ── KPI ─────────────────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📝 Peso testuale", f"{text_len:,} caratteri" if text_len > 0 else "—")
k2.metric("✏️ Emendamenti", fmt_num(n_emend))
k3.metric("🏛️ Interventi dibattito", fmt_num(n_interventi))
k4.metric("🎤 Oratori distinti", fmt_num(n_oratori))
k5.metric("📄 Paragrafi", fmt_num(paragraphs_count))

st.markdown("---")

# ── Sezione: Emendamenti + Dibattito ────────────────────────────────

col_em1, col_em2 = st.columns(2)

with col_em1:
    st.subheader("✏️ Emendamenti")
    if n_emend > 0:
        c1, c2 = st.columns(2)
        c1.metric("Aula", fmt_num(n_aula))
        c2.metric("Commissione", fmt_num(n_commissione))

        if text_len > 0:
            ratio = testo_emend / text_len
            st.metric("Rapporto testo emend / testo originale", f"{ratio:.2f}x")
        st.caption(f"Testo emendamenti: {testo_emend:,} caratteri")
    else:
        st.info("Nessun emendamento per questo atto.")

with col_em2:
    st.subheader("🏛️ Dibattito")
    if n_interventi > 0:
        c1, c2 = st.columns(2)
        c1.metric("Totale interventi", fmt_num(n_interventi))
        c2.metric("Oratori distinti", fmt_num(n_oratori))
        st.metric("Testo dibattito", f"{testo_dibattito:,} caratteri")

        top_oratori = (
            dib_atto.groupby("nome_oratore")
            .agg(n_interventi=("text_len", "count"), testo=("text_len", "sum"))
            .nlargest(5, "n_interventi")
        )
        if not top_oratori.empty:
            st.caption("Top oratori:")
            for nome, row in top_oratori.iterrows():
                st.write(f"  • **{nome}**: {int(row['n_interventi'])} interventi, {int(row['testo']):,} car.")
    else:
        st.info("Nessun intervento di dibattito per questo atto.")

st.markdown("---")

# ── Dettaglio tabellare ─────────────────────────────────────────────

tabs = st.tabs(["Emendamenti", "Dibattito", "DDL" if not atto_ddl.empty else ""])
tabs = [t for t in tabs if t.label != ""]

with tabs[0]:
    if n_emend > 0:
        df_em_display = df_emend[df_emend["fase"] == emend_atto["fase"].iloc[0]][
            ["fase", "emend_id", "tipologia", "active_ref", "text_len", "text_integrale"]
        ].copy()
        df_em_display["tipologia"] = df_em_display["tipologia"].map({"emend": "Aula", "emendc": "Commissione"})
        df_em_display = df_em_display.rename(columns={
            "fase": "Fase", "emend_id": "ID", "tipologia": "Tipo",
            "active_ref": "Riferimento", "text_len": "Car.",
            "text_integrale": "Testo",
        })
        st.dataframe(df_em_display, width="stretch", hide_index=True)
    else:
        st.info("Nessun emendamento.")

with tabs[1]:
    if n_interventi > 0:
        df_db_display = dib_atto[["data_seduta", "nome_oratore", "tipologia",
                                   "ordine_intervento", "text_len", "text_intervento"]].copy()
        df_db_display["tipologia"] = df_db_display["tipologia"].map(
            {"resaula": "Aula", "sommcomm": "Commissione"}
        )
        df_db_display = df_db_display.rename(columns={
            "data_seduta": "Data", "nome_oratore": "Oratore", "tipologia": "Tipo",
            "ordine_intervento": "Ordine", "text_len": "Car.",
            "text_intervento": "Testo",
        })
        st.dataframe(df_db_display, width="stretch", hide_index=True)
    else:
        st.info("Nessun intervento di dibattito.")

if len(tabs) > 2 and not atto_ddl.empty:
    with tabs[2]:
        ddl_info = atto_ddl.iloc[0]
        info_cols = st.columns(2)
        with info_cols[0]:
            st.write(f"**Stato:** {ddl_info['stato']}")
            st.write(f"**Natura:** {ddl_info['natura']}")
            st.write(f"**Ramo:** {ddl_info['ramo']}")
            st.write(f"**Iniziativa:** {ddl_info['descr_iniziativa']}")
        with info_cols[1]:
            if ddl_info['numero_legge'] and int(ddl_info['numero_legge']) > 0:
                st.write(f"**Legge:** n. {int(ddl_info['numero_legge'])} del {ddl_info['data_legge']}")
            st.write(f"**Data presentazione:** {ddl_info['data_presentazione']}")
            st.write(f"**Data stato:** {ddl_info['data_stato_ddl']}")

st.caption("Dati: Senato della Repubblica · Akoma Ntoso Bulk Data · XIX Legislatura · CC BY 4.0")
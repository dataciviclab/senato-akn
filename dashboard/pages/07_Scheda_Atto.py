"""Scheda Atto — Vista completa di un singolo atto legislativo."""

import re

import pandas as pd
import streamlit as st
from lab_connectors.formatters import fmt_num
from sources import load_clean, load_mart

st.set_page_config(page_title="Scheda Atto · Senato AKN", page_icon="📜", layout="wide")

# ── Helper: normalizza atto_num da fonti diverse ──────────────────────

def normalize_atto_num(raw) -> int | None:
    """Estrae atto_num da: int, 'S.12345', 'Atto00012345', '12345'."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    s = str(raw).strip()
    # "S.12345" → 12345
    m = re.match(r"^S\.(\d+)$", s)
    if m:
        return int(m.group(1))
    # "Atto00012345" → 12345
    m = re.match(r"^Atto0+(\d+)$", s)
    if m:
        return int(m.group(1))
    # bare number
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
    )

df_corpus, df_emend, df_dibattito, df_mart_emend = _load_all()

# Pre-elabora: estrai atto_num da emendamenti e dibattito
df_emend["_atto_num"] = df_emend["fase"].apply(lambda x: normalize_atto_num(x))
df_dibattito["_atto_num"] = df_dibattito["path"].apply(
    lambda x: normalize_atto_num(re.search(r"Atto0+(\d+)", str(x)).group(1))
    if re.search(r"Atto0+(\d+)", str(x)) else None
)

# ── Sidebar: selezione atto ──────────────────────────────────────────

st.sidebar.header("🔍 Cerca Atto")

# Combina atti da corpus, emendamenti e dibattito
atti_corpus = df_corpus[["atto_num", "doc_title", "famiglia"]].drop_duplicates("atto_num")
atti_emend = (
    df_emend[["_atto_num"]]
    .dropna()
    .drop_duplicates()
    .rename(columns={"_atto_num": "atto_num"})
)
atti_emend["doc_title"] = atti_emend["atto_num"].apply(lambda x: f"Emendamenti S.{int(x)}")
atti_emend["famiglia"] = None

atti_dib = (
    df_dibattito[["_atto_num"]]
    .dropna()
    .drop_duplicates()
    .rename(columns={"_atto_num": "atto_num"})
)
atti_dib["doc_title"] = atti_dib["atto_num"].apply(lambda x: f"Dibattito S.{int(x)}")
atti_dib["famiglia"] = None

# Unisci e deduplica
atti_all = pd.concat([atti_corpus, atti_emend, atti_dib], ignore_index=True)
atti_all = atti_all.drop_duplicates(subset="atto_num", keep="first")
atti_options = atti_all.sort_values("atto_num", ascending=False)

# Filtro per famiglia
famiglie = ["Tutte"] + sorted(
    atti_options["famiglia"].dropna().unique().tolist()
)
famiglia_sel = st.sidebar.selectbox("Famiglia", famiglie, index=0)

if famiglia_sel != "Tutte":
    atti_filtrati = atti_options[atti_options["famiglia"] == famiglia_sel]
else:
    atti_filtrati = atti_options

# Selector atto
def format_atto(row):
    title = str(row["doc_title"])[:60]
    return f"S.{int(row['atto_num'])} — {title}..."

atti_filtrati = atti_filtrati.copy()
atti_filtrati["_label"] = atti_filtrati.apply(format_atto, axis=1)

atto_label = st.sidebar.selectbox(
    "Seleziona atto",
    atti_filtrati["_label"].tolist(),
    index=0,
)

atto_num = int(atti_filtrati.iloc[atti_filtrati["_label"] == atto_label]["atto_num"].iloc[0])

# ── Dati atto ────────────────────────────────────────────────────────

# Corpus
atto_corpus = df_corpus[df_corpus["atto_num"] == atto_num]

# Emendamenti
emend_atto = df_emend[df_emend["_atto_num"] == atto_num]
n_emend = len(emend_atto)
n_aula = len(emend_atto[emend_atto["tipologia"] == "emend"]) if n_emend > 0 else 0
n_commissione = len(emend_atto[emend_atto["tipologia"] == "emendc"]) if n_emend > 0 else 0
testo_emend = int(emend_atto["text_len"].sum()) if n_emend > 0 else 0

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
else:
    # Atto non nel corpus ma presente in emendamenti/dibattito
    doc_title = f"Atto S.{atto_num} (non nel corpus ddlpres)"
    famiglia = "—"
    work_date = "—"
    text_len = 0
    articles_count = 0
    paragraphs_count = 0

# ── Header ───────────────────────────────────────────────────────────

st.title(f"📜 S.{atto_num}")
st.subheader(doc_title)

if atto_corpus.empty:
    st.warning("Atto non presente nel corpus ddlpres — dati da emendamenti e/o dibattito.")

col_meta1, col_meta2, col_meta3 = st.columns(3)
col_meta1.metric("Famiglia", famiglia)
col_meta2.metric("Data presentazione", str(work_date)[:10] if work_date != "—" else "—")
col_meta3.metric("Articoli", fmt_num(articles_count))

st.markdown("---")

# ── KPI ──────────────────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📝 Peso testuale", f"{text_len:,} caratteri")
k2.metric("✏️ Emendamenti", fmt_num(n_emend))
k3.metric("🏛️ Interventi dibattito", fmt_num(n_interventi))
k4.metric("🎤 Oratori distinti", fmt_num(n_oratori))
k5.metric("📄 Paragrafi", fmt_num(paragraphs_count))

st.markdown("---")

# ── Sezione: Emendamenti ─────────────────────────────────────────────

col_em1, col_em2 = st.columns(2)

with col_em1:
    st.subheader("✏️ Emendamenti")
    if n_emend > 0:
        c1, c2 = st.columns(2)
        c1.metric("Aula", fmt_num(n_aula))
        c2.metric("Commissione", fmt_num(n_commissione))

        # Testo emendamenti vs testo originale
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

        # Testo dibattito
        st.metric("Testo dibattito", f"{testo_dibattito:,} caratteri")

        # Top oratori
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

# ── Sezione: dettaglio tabellare ─────────────────────────────────────

tab1, tab2 = st.tabs(["Emendamenti", "Dibattito"])

with tab1:
    if n_emend > 0:
        df_em_display = emend_atto[["fase", "emend_id", "tipologia", "active_ref", "text_len", "text_integrale"]].copy()
        df_em_display["tipologia"] = df_em_display["tipologia"].map({"emend": "Aula", "emendc": "Commissione"})
        df_em_display = df_em_display.rename(columns={
            "fase": "Fase",
            "emend_id": "ID",
            "tipologia": "Tipo",
            "active_ref": "Riferimento",
            "text_len": "Testo (car.)",
            "text_integrale": "Testo",
        })
        st.dataframe(df_em_display, width="stretch", hide_index=True)
    else:
        st.info("Nessun emendamento.")

with tab2:
    if n_interventi > 0:
        df_db_display = dib_atto[["data_seduta", "nome_oratore", "tipologia", "ordine_intervento", "text_len", "text_intervento"]].copy()
        df_db_display["tipologia"] = df_db_display["tipologia"].map({"resaula": "Aula", "sommcomm": "Commissione"})
        df_db_display = df_db_display.rename(columns={
            "data_seduta": "Data",
            "nome_oratore": "Oratore",
            "tipologia": "Tipo",
            "ordine_intervento": "Ordine",
            "text_len": "Testo (car.)",
            "text_intervento": "Testo",
        })
        st.dataframe(df_db_display, width="stretch", hide_index=True)
    else:
        st.info("Nessun intervento di dibattito.")

st.caption("Dati: Senato della Repubblica · Akoma Ntoso Bulk Data · XIX Legislatura · CC BY 4.0")

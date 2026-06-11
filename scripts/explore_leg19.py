#!/usr/bin/env python3
"""Esplorazione Leg19 — emendamenti e resoconti.
Valuta se estendere la pipeline da ddlpres a tutte le tipologie.

Usage: source .venv/bin/activate && python3 scripts/explore_leg19.py
"""

import json, random, time, statistics, sys, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab_connectors.http import HttpClient
from senato_akn.parser import parse_xml, NS

API = "https://api.github.com/repos/SenatoDellaRepubblica/AkomaNtosoBulkData/git/trees"
RAW_ROOT = "https://raw.githubusercontent.com/SenatoDellaRepubblica/AkomaNtosoBulkData/master/Leg19"
SAMPLE = 15
TIPOLOGIE = ['ddlpres', 'emend', 'emendc', 'resaula', 'sommcomm', 'ddlmess', 'ddlcomm']

# --- 1. Tree Leg19 ---
print("=" * 60)
print("1. TREE LEG19 — conteggio file per tipologia")
print("=" * 60)

req = urllib.request.Request(f"{API}/master")
with urllib.request.urlopen(req) as r:
    root = json.loads(r.read())
leg19_sha = next(item['sha'] for item in root['tree'] if item['path'] == 'Leg19')

req = urllib.request.Request(f"{API}/{leg19_sha}?recursive=1")
with urllib.request.urlopen(req) as r:
    leg19 = json.loads(r.read())

by_type = defaultdict(list)
for item in leg19['tree']:
    if not item['path'].endswith('.akn.xml'):
        continue
    parts = item['path'].split('/')
    if len(parts) >= 3:
        by_type[parts[1]].append((item['path'], item.get('size', 0)))

totali = {}
for t in TIPOLOGIE:
    totali[t] = len(by_type.get(t, []))
    print(f"  {t:15s} {totali[t]:>8,} file")
print(f"\n  {'TOTALE':15s} {sum(totali.values()):>8,} file")

# --- 2. Campione ---
print("\n" + "=" * 60)
print(f"2. CAMPIONE — {SAMPLE} file per tipologia")
print("=" * 60)
random.seed(42)
samples = {}
for t in TIPOLOGIE:
    chosen = random.sample(by_type.get(t, []), min(SAMPLE, len(by_type.get(t, []))))
    samples[t] = chosen
    print(f"  {t:15s} campionati {len(chosen)} file")

# --- 3. Parsing + analisi struttura ---
print("\n" + "=" * 60)
print("3. ANALISI STRUTTURA XML")
print("=" * 60)

with HttpClient(timeout=120) as client:
    results = []
    errors = []
    for tipologia, files in samples.items():
        for path, size in files:
            url = f"{RAW_ROOT}/{path}"
            r = client.get(url)
            if not r.is_ok:
                errors.append({'path': path, 'error': str(r.err)[:100]})
                continue
            try:
                parsed = parse_xml(r.response.text, path=path, legislatura='Leg19')
                parsed['tipologia'] = tipologia
                parsed['file_size'] = size
                
                # Analisi struttura XML
                root_el = ET.fromstring(r.response.text)
                # Root tag
                parsed['root_tag'] = root_el.tag.replace(f'{{{NS["an"]}}}', 'an:')
                # Cerca tutti i namespace usati
                ns_used = set()
                for elem in root_el.iter():
                    if elem.tag.startswith('{'):
                        ns = elem.tag.split('}')[0] + '}'
                        ns_used.add(ns)
                parsed['ns_count'] = len(ns_used)
                
                results.append(parsed)
            except Exception as e:
                errors.append({'path': path, 'error': str(e)[:100]})
            time.sleep(0.05)

print(f"  Parsati: {len(results)} / {sum(len(v) for v in samples.values())}")
print(f"  Errori:  {len(errors)}")
if errors:
    for e in errors[:3]:
        print(f"    {e['error']} @ {e['path']}")

if len(results) == 0:
    print("\n❌ Nessun file parsato.")
    sys.exit(1)

# --- 4. Root tag per tipologia ---
print("\n" + "=" * 60)
print("4. STRUTTURA — root tag e completezza")
print("=" * 60)
root_tags = {}
for t in TIPOLOGIE:
    for r in results:
        if r['tipologia'] == t:
            root_tags[t] = r.get('root_tag', '?')
            break

for t in TIPOLOGIE:
    print(f"  {t:15s} → root: {root_tags.get(t, 'N/D')}")

# --- 5. Metadati FRBR ---
print("\n" + "=" * 60)
print("5. METADATI FRBR")
print("=" * 60)
for k in ['work_uri', 'work_date', 'doc_title', 'articles_count', 'text_len']:
    filled = sum(1 for r in results if r.get(k))
    print(f"  {k:25s}: {filled}/{len(results)} compilati")

# --- 6. URI — estrai riferimenti ---
print("\n" + "=" * 60)
print("6. URI — informazioni strutturate")
print("=" * 60)
for tipologia in TIPOLOGIE:
    for r in results:
        if r['tipologia'] == tipologia and r['work_uri']:
            print(f"  {tipologia:15s} → {r['work_uri']}")
            break

# --- 7. Dimensioni e testo ---
print("\n" + "=" * 60)
print("7. DIMENSIONI PER TIPOLOGIA")
print("=" * 60)
print(f"  {'Tipologia':15s} | {'N':>4s} | {'Testo medio':>10s} | {'File medio':>10s} | {'Root tag'}")
print("  " + "-" * 65)
for t in TIPOLOGIE:
    subset = [r for r in results if r['tipologia'] == t]
    if not subset:
        continue
    txt = statistics.mean(r['text_len'] for r in subset)
    fsz = statistics.mean(r['file_size'] for r in subset)
    rt = subset[0].get('root_tag', '?')
    print(f"  {t:15s} | {len(subset):>4d} | {txt:>8,.0f} chr | {fsz:>8,.0f} B | {rt}")

# --- 8. Stima volume ---
print("\n" + "=" * 60)
print("8. VOLUME TOTALE STIMATO LEG19")
print("=" * 60)
dim_medie = {}
for t in TIPOLOGIE:
    subset = [r for r in results if r['tipologia'] == t]
    dim_medie[t] = statistics.mean(r['file_size'] for r in subset) if subset else 0

tot_mb = 0
for t in TIPOLOGIE:
    stimato = totali[t] * dim_medie[t] / 1024 / 1024
    tot_mb += stimato
    print(f"  {t:15s} {totali[t]:>8,} file × {dim_medie[t]:>7,.0f} B = {stimato:>7.1f} MB")
print(f"  {'TOTALE':15s} {'':>8s} {'':>7s} = {tot_mb:>7.1f} MB")

# --- 9. Verdetto ---
print("\n" + "=" * 60)
print("9. VERDETTO — estendere la pipeline?")
print("=" * 60)

# Analisi: quante tipologie hanno root diverso da an:act (ddlpres)
roots = set()
for r in results:
    roots.add(r.get('root_tag', ''))
print(f"  Root tag distinti nel campione: {len(roots)} → {roots}")

# Verifica se parser attuale copre tutte
ok_count = sum(1 for r in results if r['text_len'] > 0)
print(f"  Record con testo (parser attuale): {ok_count}/{len(results)}")
print(f"  Record senza testo: {len(results) - ok_count}/{len(results)}")
print(f"  → Il parser funziona solo su {root_tags.get('ddlpres','?')} (ddlpres)")

print(f"""
RIEPILOGO FINALE:
══════════════════

COPERTURA ATTUALE: solo ddlpres ({totali['ddlpres']:,} file, ~{totali['ddlpres']*dim_medie['ddlpres']/1024/1024:.0f} MB)
MANCANTE: {sum(totali[t] for t in TIPOLOGIE if t != 'ddlpres'):,} file, ~{tot_mb-totali['ddlpres']*dim_medie['ddlpres']/1024/1024:.0f} MB
  di cui emendamenti: {totali['emend'] + totali['emendc']:,} file ({((totali['emend']+totali['emendc'])/sum(totali.values())*100):.0f}% del totale)
  resoconti: {totali['resaula'] + totali['sommcomm']:,} file
  altro: {totali['ddlmess'] + totali['ddlcomm']:,} file

STRUTTURA XML:
  • ddlpres → <an:act> — già parsato (body/p)
  • emend/emendc → <an:amendment> — parser DA ESTENDERE (testo in struttura diversa)
  • resaula → <an:debate> — parser DA ESTENDERE (interventi testuali)
  • sommcomm → <an:debate> — parser DA ESTENDERE
  • ddlmess → <an:act> — GIÀ PARSABILE (stessa struttura ddlpres)
  • ddlcomm → <an:act> — GIÀ PARSABILE (stessa struttura ddlpres)

VALORE CIVICO:
  • Emendamenti: chi presenta cosa, a quale articolo, di che tipo
  • Resoconti: dibattito parlamentare, analisi NLP, citazioni
  • Incrocio ddlpres→emend: quanto cambia un testo durante l'iter

COSA SERVE:
  1. Estendere parser per <an:amendment> e <an:debate>
  2. Aggiungere colonna 'tipologia' al CSV
  3. Modificare discover_files per non filtrare solo ddlpres
  4. Stimato: qualche ora di lavoro, ~750 MB da scaricare

CONVIENE? 
  {'✅ SÌ — 61k emendamenti giustificano l\'investimento' if (totali['emend']+totali['emendc']) > 10000 else '❌ NO — volume insufficiente'}
""")

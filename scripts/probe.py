#!/usr/bin/env python3
"""Probe del corpus AKN upstream: quali legislature sono cambiate?

Una chiamata API per legislatura, nessun clone e nessun blob scaricato: serve
a decidere *se* vale la pena costruire, non a costruire.

Output di default: le legislature da aggiornare, separate da spazio (così si
usa direttamente in ``$(shell)`` / ``for`` di make). Con ``--json`` stampa il
dettaglio (sha, data, precedente).

Convenzione di errore: se il probe di una legislatura fallisce, quella
legislatura è considerata **cambiata** (fail-open). Meglio ricostruire che
saltare in silenzio un aggiornamento: il costo di un rebuild è minuti, quello
di dati vecchi non dichiarati è un numero sbagliato pubblicato.

Exit code:
    0  probe eseguito (anche con singoli fallimenti, segnalati su stderr)
    2  nessun probe riuscito: rete o API inaccessibili
"""

from __future__ import annotations

import argparse
import json
import sys

from senato_akn.fingerprint import (
    STATE_PATH,
    ProbeError,
    changed,
    load_state,
    remote_fingerprint,
    save_state,
)

DEFAULT_LEGISLATURES = ("Leg14", "Leg15", "Leg16", "Leg17", "Leg18", "Leg19")


def _parse_legislatures(raw: str) -> tuple[str, ...]:
    """Accetta sia "Leg14,Leg15" sia "Leg14 Leg15" (make e shell)."""
    parts = raw.replace(",", " ").split()
    return tuple(dict.fromkeys(parts)) or DEFAULT_LEGISLATURES


def main() -> int:
    parser = argparse.ArgumentParser(description="Quali legislature AKN sono cambiate.")
    parser.add_argument(
        "--legislatures",
        default=" ".join(DEFAULT_LEGISLATURES),
        help="Legislature da controllare (default: tutte quelle del Makefile)",
    )
    parser.add_argument("--state", default=str(STATE_PATH), help="File di stato (legislatura → sha)")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Aggiorna lo stato dopo un probe riuscito (usare a pipeline conclusa)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON dettagliato")
    args = parser.parse_args()

    legislatures = _parse_legislatures(args.legislatures)
    previous = load_state(args.state)

    current: dict[str, dict[str, str]] = {}
    failures: list[str] = []
    for leg in legislatures:
        try:
            current[leg] = remote_fingerprint(leg)
        except ProbeError as exc:
            failures.append(leg)
            print(f"::warning::probe {leg} fallito ({exc}) → considerata cambiata", file=sys.stderr)

    if len(failures) == len(legislatures):
        print("probe: nessuna legislatura interrogabile (rete o API)", file=sys.stderr)
        return 2

    to_build = changed(current, previous)
    for leg in failures:
        if leg not in to_build:
            to_build.append(leg)

    if args.update:
        updated = {**previous}
        for leg, info in current.items():
            if info.get("sha"):
                updated[leg] = info["sha"]
        save_state(updated, args.state)

    if args.json:
        payload = {
            "changed": to_build,
            "legislatures": {
                leg: {
                    "sha": current.get(leg, {}).get("sha", ""),
                    "date": current.get(leg, {}).get("date", ""),
                    "previous": previous.get(leg, ""),
                    "changed": leg in to_build,
                    "probe_failed": leg in failures,
                }
                for leg in legislatures
            },
        }
        print(json.dumps(payload, indent=1, ensure_ascii=False))
    else:
        print(" ".join(to_build))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

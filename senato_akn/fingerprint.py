"""Fingerprint remoto del corpus AKN, per legislatura.

Perché non ``git ls-remote``: i commit orari dell'upstream toccano **solo i
README** (misurato il 2026-11-24: otto commit consecutivi, tutti README-only).
Lo sha del branch cambia quindi ogni ora anche quando i dati non cambiano, e
usarlo come guardia farebbe partire un build all'ora per niente.

Il fingerprint utile è l'ultimo commit che tocca la cartella di una
legislatura: se non cambia, i file XML di quella legislatura non sono cambiati.
Una chiamata API per legislatura, nessun clone, nessun blob scaricato.

Il fingerprint è *path-scoped*, non *content-addressed*: dice "questa cartella
non è stata toccata", non "questo blob ha lo stesso contenuto". Per il diff a
livello di file resta valido ``git ls-tree`` (vedi ``git_source``), che è la
chiave del ``--incremental``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO = "SenatoDellaRepubblica/AkomaNtosoBulkData"
API_BASE = "https://api.github.com"
STATE_PATH = Path("data/state/fingerprints.json")


class ProbeError(RuntimeError):
    """Fingerprint non ottenibile (rete, rate limit, risposta inattesa)."""


def _token() -> str | None:
    """Token da GITHUB_TOKEN/GH_TOKEN: alza il rate limit da 60/h a 5000/h."""
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None


def remote_fingerprint(
    legislatura: str,
    *,
    repo: str = REPO,
    token: str | None = None,
    timeout: float = 20.0,
) -> dict[str, str]:
    """Ultimo commit che tocca ``<legislatura>/`` nell'upstream.

    Returns:
        ``{"sha": ..., "date": ...}``; entrambi vuoti se la cartella non ha
        commit (legislatura inesistente nell'upstream).

    Raises:
        ProbeError: rete assente, rate limit, status inatteso.
    """
    query = urllib.parse.urlencode({"path": legislatura, "per_page": "1"})
    url = f"{API_BASE}/repos/{repo}/commits?{query}"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    bearer = token if token is not None else _token()
    if bearer:
        request.add_header("Authorization", f"Bearer {bearer}")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload: Any = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = json.loads(exc.read()).get("message", "")
        except Exception:
            pass
        raise ProbeError(f"HTTP {exc.code} su {url}: {detail}".strip()) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProbeError(f"rete non disponibile per {url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProbeError(f"risposta non JSON da {url}") from exc

    if not isinstance(payload, list) or not payload:
        return {"sha": "", "date": ""}
    commit = payload[0]
    return {
        "sha": str(commit.get("sha") or ""),
        "date": str((commit.get("commit") or {}).get("author", {}).get("date") or ""),
    }


def load_state(path: str | Path = STATE_PATH) -> dict[str, str]:
    """Stato ``legislatura -> sha`` dell'ultimo run riuscito (vuoto se assente)."""
    file = Path(path)
    if not file.exists():
        return {}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}


def save_state(state: dict[str, str], path: str | Path = STATE_PATH) -> None:
    """Scrive lo stato in modo atomico (un run interrotto non lascia JSON rotto)."""
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_suffix(file.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(file)


def changed(total: dict[str, dict[str, str]], previous: dict[str, str]) -> list[str]:
    """Legislature il cui fingerprint differisce dallo stato precedente.

    Una legislatura senza stato precedente è ``changed``: il primo run deve
    costruire tutto. L'ordine dell'input è preservato (stabile nei log).
    """
    return [leg for leg, info in total.items() if info.get("sha") and info["sha"] != previous.get(leg)]

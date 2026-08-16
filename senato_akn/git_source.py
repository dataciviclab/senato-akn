"""Sorgente git per il corpus Akoma Ntoso del Senato.

Sostituisce il download per-file via HTTP con il protocollo git:

- ``git clone --depth 1 --filter=blob:none --sparse``: scarica solo i blob
  della legislatura richiesta via pack (molto più veloce di N richieste
  HTTP, e *completo* — la GitHub tree API tronca oltre ~100k entry).
- ``git fetch`` + ``reset`` per l'aggiornamento (delta).
- ``git ls-tree`` per l'elenco path→sha (il blob sha = hash del contenuto:
  chiave del diff incrementale).

Non tocca la rete per i singoli file: dopo il clone/fetch i file XML sono
nel working tree locale e vengono letti da disco (parsing ~1 ms/file).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO_URL = "https://github.com/SenatoDellaRepubblica/AkomaNtosoBulkData.git"
REPO_BRANCH = "master"


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def ensure_repo(repo_dir: str | Path, legislatura: str) -> Path:
    """Clona (o aggiorna) il repo upstream e materializza la legislatura.

    Primo avvio: clone shallow ``blob:none`` + sparse-checkout della
    legislatura (scarica solo i suoi blob). Aggiornamento: ``git fetch``
    shallow + ``reset --hard`` (con sparse attivo aggiorna solo le path
    sparse, scaricando via pack i blob nuovi).

    Un repo git locale senza remote (es. nei test, o una copia manuale) è
    usato così com'è: la legislatura deve già essere nel working tree.

    Args:
        repo_dir: Directory del clone (creata se assente).
        legislatura: Directory legislatura da materializzare (es. ``Leg19``).

    Returns:
        Path del clone (con la legislatura nel working tree).
    """
    repo_dir = Path(repo_dir)
    if not (repo_dir / ".git").exists():
        repo_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git", "clone", "--depth", "1",
                "--filter=blob:none", "--sparse", "--no-checkout",
                REPO_URL, str(repo_dir),
            ],
            check=True,
        )
        _run(repo_dir, "sparse-checkout", "set", legislatura)
        _run(repo_dir, "checkout")
        return repo_dir

    has_remote = _run(repo_dir, "remote").stdout.strip() != ""
    if has_remote:
        _run(repo_dir, "fetch", "--depth", "1", "origin", REPO_BRANCH)
        _run(repo_dir, "reset", "--hard", "FETCH_HEAD")
        _run(repo_dir, "sparse-checkout", "set", legislatura)

    if not (repo_dir / legislatura).exists():
        raise FileNotFoundError(
            f"Legislatura '{legislatura}' non materializzata in {repo_dir}. "
            "Per un repo locale, clonala/sparse-checkout o usa un clone upstream."
        )
    return repo_dir


def list_entries(
    repo_dir: str | Path,
    legislatura: str,
    tipologie: list[str],
) -> list[dict[str, str]]:
    """Elenco (path, blob sha) dei file della legislatura, filtrato per tipologia.

    La tree API di GitHub tronca oltre ~100k entry: qui si usa
    ``git ls-tree`` locale (completo e autoritativo).

    Args:
        repo_dir: Directory del clone.
        legislatura: Directory legislatura (es. ``Leg19``).
        tipologie: Tipologie da includere (es. ``["ddlpres"]``).

    Returns:
        Lista ordinata di dict ``{"path", "sha"}``.
    """
    out = _run(repo_dir, "ls-tree", "-r", "-z", "HEAD", "--", legislatura)
    patterns = tuple(f"/{t}/" for t in tipologie)
    entries: list[dict[str, str]] = []
    for line in out.stdout.split("\0"):
        if not line:
            continue
        meta, path = line.split("\t", 1)
        sha = meta.split(" ")[2]
        if path.endswith(".akn.xml") and any(p in path for p in patterns):
            entries.append({"path": path, "sha": sha})
    return sorted(entries, key=lambda e: e["path"])


def read_local(repo_dir: str | Path, path: str) -> bytes:
    """Legge un file XML dal working tree locale."""
    return (Path(repo_dir) / path).read_bytes()

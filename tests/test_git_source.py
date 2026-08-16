"""Test per senato_akn.git_source — list_entries/read_local su un repo locale."""
import subprocess
from pathlib import Path

from senato_akn.git_source import ensure_repo, list_entries, read_local

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "Leg19" / "Atto00055177" / "ddlpres").mkdir(parents=True)
    (repo / "Leg19" / "Atto00055177" / "emendc").mkdir(parents=True)
    (repo / "Leg18" / "Atto00055177" / "ddlpres").mkdir(parents=True)
    xml = (FIXTURE_DIR / "sample.akn.xml").read_text()
    (repo / "Leg19/Atto00055177/ddlpres/a.akn.xml").write_text(xml)
    (repo / "Leg19/Atto00055177/ddlpres/b.akn.xml").write_text(xml)
    (repo / "Leg19/Atto00055177/emendc/c.akn.xml").write_text(xml)
    (repo / "Leg18/Atto00055177/ddlpres/d.akn.xml").write_text(xml)
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=t", "-c", "user.name=t", "commit", "-qm", "seed"],
        check=True,
    )
    return repo


class TestListEntries:
    def test_filtra_legislatura_e_tipologia(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        entries = list_entries(repo, "Leg19", ["ddlpres"])
        assert [e["path"] for e in entries] == [
            "Atto00055177/ddlpres/a.akn.xml",
            "Atto00055177/ddlpres/b.akn.xml",
        ]

    def test_tipologie_multiple(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        entries = list_entries(repo, "Leg19", ["ddlpres", "emendc"])
        assert len(entries) == 3

    def test_sha_e_hash_blob(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        entries = list_entries(repo, "Leg19", ["ddlpres"])
        # lo sha deve essere l'hash del blob git (40 hex)
        assert len(entries[0]["sha"]) == 40
        import hashlib
        content = (repo / "Leg19" / entries[0]["path"]).read_bytes()
        h = hashlib.sha1()
        h.update(f"blob {len(content)}\0".encode())
        h.update(content)
        assert entries[0]["sha"] == h.hexdigest()


class TestReadLocal:
    def test_legge_dal_working_tree(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        content = read_local(repo, "Leg19", "Atto00055177/ddlpres/a.akn.xml")
        assert b"akomaNtoso" in content


class TestEnsureRepo:
    def test_repo_locale_senza_remote(self, tmp_path: Path) -> None:
        """Un repo git locale (no remote) viene usato così com'è."""
        repo = _make_repo(tmp_path)
        result = ensure_repo(repo, "Leg19")
        assert result == repo
        assert (repo / "Leg19").exists()

"""Test per senato_akn.extract — usa FakeHttpClient, nessuna chiamata HTTP reale."""
from pathlib import Path

import pyarrow.parquet as pq
from lab_connectors.http.types import HttpResult
from lab_connectors.testing import FakeHttpClient, fake_response

from senato_akn.extract import (
    _all_tipologie,
    _default_out_path,
    _document_famiglie,
    _extract_tipologia,
    diff_manifest,
    discover_entries,
    discover_files,
    fetch_and_parse,
    fetch_content,
    load_manifest,
    raw_root,
    run_extract,
    save_manifest,
    write_output,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

REPO_API = "https://api.github.com/repos/SenatoDellaRepubblica/AkomaNtosoBulkData"


def _make_fake_client(tree_items: list[dict]) -> FakeHttpClient:
    """Crea un FakeHttpClient con risposte preconfigurate per GitHub API."""
    client = FakeHttpClient()

    # Risposta per /contents (trova Leg19)
    client.responses[f"{REPO_API}/contents?ref=master"] = HttpResult(
        response=fake_response(200, json_data=[
            {"name": "Leg13", "sha": "aaa"},
            {"name": "Leg19", "sha": "bbb"},
        ]),
        err=None,
    )

    # Risposta per /git/trees/{sha}?recursive=1
    client.responses[f"{REPO_API}/git/trees/bbb?recursive=1"] = HttpResult(
        response=fake_response(200, json_data={"tree": tree_items}),
        err=None,
    )

    # Risposta per /git/trees/aaa?recursive=1 (Leg13, per test multi-legislatura)
    client.responses[f"{REPO_API}/git/trees/aaa?recursive=1"] = HttpResult(
        response=fake_response(200, json_data={"tree": [
            {"path": "Atto00123456/ddlpres/old.akn.xml", "type": "blob"},
        ]}),
        err=None,
    )

    # Risposta per il download raw di un file XML
    # I path nel tree sono relativi alla directory Leg19
    fixture_xml = FIXTURE_DIR / "sample.akn.xml"
    client.responses["https://raw.githubusercontent.com/SenatoDellaRepubblica/AkomaNtosoBulkData/master/Leg19/Atto00055177/ddlpres/01360967-ft.akn.xml"] = HttpResult(
        response=fake_response(200, text=fixture_xml.read_text()),
        err=None,
    )

    return client


# ---------------------------------------------------------------------------
# Test funzioni pure
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_all_tipologie(self) -> None:
        tipi = _all_tipologie()
        assert "ddlpres" in tipi
        assert "emend" in tipi
        assert "resaula" in tipi
        assert len(tipi) == 7

    def test_raw_root_default(self) -> None:
        assert raw_root() == (
            "https://raw.githubusercontent.com/SenatoDellaRepubblica/"
            "AkomaNtosoBulkData/master/Leg19"
        )

    def test_raw_root_custom(self) -> None:
        assert "Leg18" in raw_root("Leg18")

    def test_extract_tipologia_ddlpres(self) -> None:
        assert _extract_tipologia("Atto00055177/ddlpres/file.xml") == "ddlpres"

    def test_extract_tipologia_emend(self) -> None:
        assert _extract_tipologia("Atto00055177/emend/file.xml") == "emend"

    def test_extract_tipologia_unknown(self) -> None:
        assert _extract_tipologia("Atto00055177/unknown/file.xml") == ""

    def test_default_out_path_ddlpres(self) -> None:
        assert _default_out_path("Leg19", ["ddlpres"]) == "leg19_ddlpres_v0.parquet"

    def test_default_out_path_multiple(self) -> None:
        assert _default_out_path("Leg19", ["ddlmess", "ddlcomm"]) == "leg19_ddlcomm_ddlmess_v0.parquet"

    def test_default_out_path_all(self) -> None:
        assert _default_out_path("Leg19", _all_tipologie()) == "leg19_all_v0.parquet"

    def test_default_out_path_other_legislatura(self) -> None:
        assert _default_out_path("Leg18", ["ddlpres"]) == "leg18_ddlpres_v0.parquet"


class TestDiscoverFiles:
    def test_returns_sorted_paths(self) -> None:
        # Path API sono relativi al tree SHA (directory Leg19)
        tree_items = [
            {"path": "Atto00055177/ddlpres/01360967-ft.akn.xml", "type": "blob"},
            {"path": "Atto00055178/ddlpres/01361136-ft.akn.xml", "type": "blob"},
            {"path": "Atto00055178/emend/xyz.xml", "type": "blob"},  # non ddlpres
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client)
        assert files == [
            "Atto00055177/ddlpres/01360967-ft.akn.xml",
            "Atto00055178/ddlpres/01361136-ft.akn.xml",
        ]

    def test_excludes_non_ddlpres(self) -> None:
        tree_items = [
            {"path": "Atto00055177/emend/xyz.akn.xml", "type": "blob"},
            {"path": "Atto00055177/sommcomm/abc.akn.xml", "type": "blob"},
            {"path": "Atto00055177/ddlpres/test.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client)
        assert files == ["Atto00055177/ddlpres/test.akn.xml"]

    def test_empty_when_no_match(self) -> None:
        tree_items = [
            {"path": "Atto00055177/emend/xyz.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client)
        assert files == []

    def test_multiple_tipologie(self) -> None:
        tree_items = [
            {"path": "Atto00055177/ddlpres/a.akn.xml", "type": "blob"},
            {"path": "Atto00055177/emend/b.akn.xml", "type": "blob"},
            {"path": "Atto00055177/resaula/c.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client, tipologie=["ddlpres", "emend"])
        assert files == [
            "Atto00055177/ddlpres/a.akn.xml",
            "Atto00055177/emend/b.akn.xml",
        ]
        assert "resaula" not in " ".join(files)

    def test_all_tipologie(self) -> None:
        tree_items = [
            {"path": "Atto00055177/ddlpres/a.akn.xml", "type": "blob"},
            {"path": "Atto00055177/emend/b.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client, tipologie=["all"])
        assert len(files) == 2
        assert all(f.endswith(".akn.xml") for f in files)

    def test_altra_legislatura(self) -> None:
        tree_items = [
            {"path": "Atto00123456/ddlpres/old.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        files = discover_files(client, legislatura="Leg13")
        # Il mock per Leg13 è configurato in _make_fake_client
        assert len(files) == 1
        assert "old.akn.xml" in files[0]


class TestFetchAndParse:
    def test_parses_fixture(self) -> None:
        tree_items = [
            {"path": "Atto00055177/ddlpres/01360967-ft.akn.xml", "type": "blob"},
        ]
        client = _make_fake_client(tree_items)
        result = fetch_and_parse(
            client,
            "Atto00055177/ddlpres/01360967-ft.akn.xml",
        )
        assert result["document_id"] == "01360967-ft.akn"
        assert result["legislatura"] == "Leg19"  # valore di default in parse_xml
        assert result["text_len"] > 0


class TestFetchContentCache:
    PATH = "Atto00055177/ddlpres/01360967-ft.akn.xml"
    def test_scarica_e_scrive_cache(self, tmp_path: Path) -> None:
        client = _make_fake_client([{"path": self.PATH, "type": "blob"}])
        cache_dir = tmp_path / "cache"
        content = fetch_content(client, self.PATH, cache_dir=cache_dir)
        assert b"akomaNtoso" in content
        cached = cache_dir / "Leg19" / self.PATH
        assert cached.exists()
        assert cached.read_bytes() == content

    def test_cache_hit_non_riusa_la_rete(self, tmp_path: Path) -> None:
        client = _make_fake_client([{"path": self.PATH, "type": "blob"}])
        cache_dir = tmp_path / "cache"
        cached = cache_dir / "Leg19" / self.PATH
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(b"<cached/>")

        content = fetch_content(client, self.PATH, cache_dir=cache_dir)
        assert content == b"<cached/>"

        # Rimuove la risposta fake: un cache-hit non deve fare nessuna richiesta
        client.responses.pop(
            "https://raw.githubusercontent.com/SenatoDellaRepubblica/"
            "AkomaNtosoBulkData/master/Leg19/Atto00055177/ddlpres/01360967-ft.akn.xml"
        )
        again = fetch_content(client, self.PATH, cache_dir=cache_dir)
        assert again == b"<cached/>"

    def test_senza_cache_scarica_sempre(self, tmp_path: Path) -> None:
        client = _make_fake_client([{"path": self.PATH, "type": "blob"}])
        content = fetch_content(client, self.PATH)  # cache_dir=None
        assert b"akomaNtoso" in content


class TestFamiglie:
    def test_classifica_da_doc_title(self) -> None:
        row = {"doc_title": "Conversione in legge del decreto-legge 4 agosto 2022, n. 115"}
        assert "decreto_like" in _document_famiglie(row)

    def test_fallback_su_short_title(self) -> None:
        row = {"doc_title": "", "short_title": "Ratifica ed esecuzione del trattato"}
        assert "ratifica" in _document_famiglie(row)

    def test_multi_famiglia_separate_da_punto_virgola(self) -> None:
        row = {"doc_title": "Delega al governo in materia di lavoro"}
        famiglie = _document_famiglie(row)
        assert ";" in famiglie
        assert "delega" in famiglie.split(";")

    def test_senza_titolo_vuoto(self) -> None:
        assert _document_famiglie({"doc_title": "", "short_title": ""}) == ""


class TestWriteOutput:
    def test_parquet_roundtrip(self, tmp_path: Path) -> None:
        out = tmp_path / "corpus.parquet"
        rows = [
            {
                "atto_dir": "Atto00055177",
                "doc_title": "Conversione in legge del decreto-legge 115",
                "famiglia": "decreto_like",
                "text_len": 1500,
                "articles_count": 3,
            }
        ]
        written = write_output(rows, out)
        assert Path(written).exists()
        table = pq.read_table(written)
        assert table.num_rows == 1
        assert table.column_names == ["atto_dir", "doc_title", "famiglia", "text_len", "articles_count"]
        assert table.to_pylist()[0]["famiglia"] == "decreto_like"

    def test_parquet_vuoto(self, tmp_path: Path) -> None:
        out = tmp_path / "empty.parquet"
        written = write_output([], out)
        assert pq.read_table(written).num_rows == 0

    def test_csv_backward_compat(self, tmp_path: Path) -> None:
        out = tmp_path / "corpus.csv"
        rows = [{"doc_title": "x", "famiglia": "decreto_like", "text_len": 1}]
        written = write_output(rows, out)
        assert written.read_text().startswith("doc_title,famiglia,text_len")
        assert "decreto_like" in written.read_text()


class TestManifest:
    def test_manifest_roundtrip(self, tmp_path: Path) -> None:
        p = tmp_path / "m.manifest.json"
        save_manifest(p, {"a": "sha1", "b": "sha2"})
        assert load_manifest(p) == {"a": "sha1", "b": "sha2"}

    def test_manifest_assente_vuoto(self, tmp_path: Path) -> None:
        assert load_manifest(tmp_path / "missing.json") == {}

    def test_diff_identifica_cambiati(self) -> None:
        entries = [
            {"path": "A", "sha": "s1"},
            {"path": "B", "sha": "s2"},   # cambiato (era s1)
            {"path": "C", "sha": "s3"},   # nuovo
        ]
        manifest = {"A": "s1", "B": "s1"}
        changed = diff_manifest(entries, manifest)
        assert [e["path"] for e in changed] == ["B", "C"]

    def test_diff_nessun_cambiamento(self) -> None:
        entries = [{"path": "A", "sha": "s1"}]
        assert diff_manifest(entries, {"A": "s1"}) == []


class TestRunExtractDelta:
    """run_extract in modalità delta: manifest + snapshot → solo i file cambiati."""

    A_PATH = "Atto00055177/ddlpres/01360967-ft.akn.xml"
    B_PATH = "Atto00055178/ddlpres/01361136-ft.akn.xml"
    RAW_ROOT = "https://raw.githubusercontent.com/SenatoDellaRepubblica/AkomaNtosoBulkData/master/Leg19"

    def _client(self, b_sha: str, b_xml: str, *, include_a: bool = True) -> FakeHttpClient:
        client = FakeHttpClient()
        client.responses[f"{REPO_API}/contents?ref=master"] = HttpResult(
            response=fake_response(200, json_data=[
                {"name": "Leg19", "sha": "bbb"},
            ]),
            err=None,
        )
        tree = [{"path": self.A_PATH, "type": "blob", "sha": "sha_a"}, {"path": self.B_PATH, "type": "blob", "sha": b_sha}]
        client.responses[f"{REPO_API}/git/trees/bbb?recursive=1"] = HttpResult(
            response=fake_response(200, json_data={"tree": tree}),
            err=None,
        )
        if include_a:
            client.responses[f"{self.RAW_ROOT}/{self.A_PATH}"] = HttpResult(
                response=fake_response(200, text=(FIXTURE_DIR / "sample.akn.xml").read_text()),
                err=None,
            )
        client.responses[f"{self.RAW_ROOT}/{self.B_PATH}"] = HttpResult(
            response=fake_response(200, text=b_xml),
            err=None,
        )
        return client

    def test_full_poi_delta_merge(self, tmp_path: Path) -> None:
        out = tmp_path / "corpus.parquet"
        manifest = tmp_path / "corpus.manifest.json"

        # ── Run 1: full (nessun snapshot/manifest) → scarica A e B ──
        b_orig = (FIXTURE_DIR / "sample.akn.xml").read_text()
        client = self._client("sha_b1", b_orig)
        run_extract(client, out=out, manifest_path=manifest, cache_dir=tmp_path / "cache")
        assert pq.read_table(out).num_rows == 2
        assert load_manifest(manifest) == {self.A_PATH: "sha_a", self.B_PATH: "sha_b1"}

        # ── Run 2: delta — B è cambiato (sha_b2 + contenuto diverso) ──
        b_new = b_orig.replace(
            "Disposizioni per l'adeguamento",
            "NUOVO TITOLO DI PROVA",
        )
        client2 = self._client("sha_b2", b_new, include_a=False)  # A non disponibile
        raw_requests_before = len(client2.requests)
        run_extract(
            client2,
            out=out,
            manifest_path=manifest,
            existing_parquet=out,
            cache_dir=tmp_path / "cache",
        )
        # Solo B è stato scaricato (A non è nemmeno stato richiesto)
        raw_reqs = [u for _, u, _ in client2.requests if u.startswith(self.RAW_ROOT)]
        assert len(raw_reqs) == 1
        assert self.B_PATH in raw_reqs[0]

        # Il parquet risultante ha 2 righe e B con il nuovo titolo
        rows = pq.read_table(out).to_pylist()
        assert len(rows) == 2
        b_row = next(r for r in rows if r["path"] == self.B_PATH)
        assert "NUOVO TITOLO DI PROVA" in b_row["doc_title"]
        a_row = next(r for r in rows if r["path"] == self.A_PATH)
        assert "Disposizioni per l'adeguamento" in a_row["doc_title"]

        # Manifest aggiornato solo per B
        assert load_manifest(manifest) == {self.A_PATH: "sha_a", self.B_PATH: "sha_b2"}

    def test_senza_snapshot_fa_full_rebuild(self, tmp_path: Path) -> None:
        """Senza existing_parquet, run_extract processa tutti i file."""
        client = self._client("sha_b1", (FIXTURE_DIR / "sample.akn.xml").read_text())
        out = tmp_path / "corpus.parquet"
        manifest = tmp_path / "corpus.manifest.json"
        run_extract(client, out=out, manifest_path=manifest, cache_dir=tmp_path / "cache")
        raw_reqs = [u for _, u, _ in client.requests if u.startswith(self.RAW_ROOT)]
        assert len(raw_reqs) == 2
        assert pq.read_table(out).num_rows == 2

"""Test per senato_akn.fingerprint — probe path-scoped e stato del probe."""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path

import pytest

from senato_akn import fingerprint


class _Response:
    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _fake_urlopen(monkeypatch: pytest.MonkeyPatch, payload: object) -> list[str]:
    """Sostituisce urlopen e cattura le URL richieste."""
    seen: list[str] = []

    def fake(request: object, timeout: float = 0) -> _Response:
        seen.append(getattr(request, "full_url", str(request)))
        return _Response(payload)

    monkeypatch.setattr(fingerprint.urllib.request, "urlopen", fake)
    return seen


class TestRemoteFingerprint:
    def test_legge_sha_e_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _fake_urlopen(
            monkeypatch,
            [{"sha": "abc123", "commit": {"author": {"date": "2026-11-22T14:09:00Z"}}}],
        )

        info = fingerprint.remote_fingerprint("Leg19")

        assert info == {"sha": "abc123", "date": "2026-11-22T14:09:00Z"}

    def test_il_fingerprint_e_path_scoped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Regressione: lo sha del branch cambia ogni ora per i README.

        Se il filtro `path=` sparisse dalla richiesta, il probe tornerebbe a
        guardare i commit dei README e ogni run risulterebbe "cambiato".
        """
        seen = _fake_urlopen(monkeypatch, [{"sha": "s", "commit": {"author": {"date": "d"}}}])

        fingerprint.remote_fingerprint("Leg19")

        assert len(seen) == 1
        assert "path=Leg19" in seen[0]
        assert "/commits?" in seen[0]

    def test_legislatura_senza_commit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _fake_urlopen(monkeypatch, [])

        assert fingerprint.remote_fingerprint("Leg99") == {"sha": "", "date": ""}

    def test_token_passato_come_header(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def fake(request: object, timeout: float = 0) -> _Response:
            captured["headers"] = dict(getattr(request, "headers", {}))
            return _Response([{"sha": "s", "commit": {"author": {"date": "d"}}}])

        monkeypatch.setattr(fingerprint.urllib.request, "urlopen", fake)

        fingerprint.remote_fingerprint("Leg19", token="tok")

        headers = {k.lower(): v for k, v in captured["headers"].items()}
        assert headers.get("authorization") == "Bearer tok"

    def test_http_error_diventa_probe_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake(request: object, timeout: float = 0) -> _Response:
            raise urllib.error.HTTPError(
                url="u", code=403, msg="Forbidden", hdrs=None, fp=io.BytesIO(b'{"message":"rate"}')
            )

        monkeypatch.setattr(fingerprint.urllib.request, "urlopen", fake)

        with pytest.raises(fingerprint.ProbeError, match="403"):
            fingerprint.remote_fingerprint("Leg19")


class TestStato:
    def test_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "state" / "fp.json"

        fingerprint.save_state({"Leg19": "abc"}, path)

        assert fingerprint.load_state(path) == {"Leg19": "abc"}

    def test_file_assente_vuoto(self, tmp_path: Path) -> None:
        assert fingerprint.load_state(tmp_path / "nope.json") == {}

    def test_file_corrotto_vuoto(self, tmp_path: Path) -> None:
        """Uno stato corrotto non deve far fallire il probe: si ricostruisce."""
        path = tmp_path / "fp.json"
        path.write_text("{non json")

        assert fingerprint.load_state(path) == {}


class TestChanged:
    def test_primo_run_tutte_cambiate(self) -> None:
        total = {"Leg18": {"sha": "a"}, "Leg19": {"sha": "b"}}

        assert fingerprint.changed(total, {}) == ["Leg18", "Leg19"]

    def test_sha_uguale_non_cambia(self) -> None:
        total = {"Leg19": {"sha": "b"}}

        assert fingerprint.changed(total, {"Leg19": "b"}) == []

    def test_sha_diverso_cambia(self) -> None:
        total = {"Leg19": {"sha": "c"}}

        assert fingerprint.changed(total, {"Leg19": "b"}) == ["Leg19"]

    def test_sha_vuoto_non_cambia(self) -> None:
        """Legislatura non presente upstream: non si costruisce a vuoto."""
        total = {"Leg99": {"sha": ""}}

        assert fingerprint.changed(total, {}) == []

    def test_ordine_preservato(self) -> None:
        total = {"Leg19": {"sha": "b"}, "Leg14": {"sha": "a"}}

        assert fingerprint.changed(total, {}) == ["Leg19", "Leg14"]

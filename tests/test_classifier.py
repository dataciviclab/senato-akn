"""Test per senato_akn.classifier."""
from senato_akn.classifier import classify


class TestClassify:
    def test_decreto_law_keyword(self) -> None:
        """'decreto-legge' in title."""
        assert classify("Decreto-legge 123") == ["decreto_like"]

    def test_conversione(self) -> None:
        """'conversione in legge'."""
        assert classify("Conversione in legge del decreto-legge 456") == ["decreto_like"]

    def test_bilancio_previsione(self) -> None:
        assert classify("Bilancio di previsione dello Stato") == ["bilancio"]

    def test_bilancio_rendiconto(self) -> None:
        assert classify("Rendiconto generale") == ["bilancio"]

    def test_ratifica(self) -> None:
        assert classify("Ratifica del trattato") == ["ratifica"]

    def test_delega(self) -> None:
        assert classify("Delega al Governo in materia") == ["delega"]

    def test_istituzione(self) -> None:
        assert classify("Istituzione della Commissione") == ["istituzione"]

    def test_lavoro(self) -> None:
        assert classify("Delega al Governo in materia di lavoro") == ["delega", "lavoro"]

    def test_multiple_families(self) -> None:
        """Titolo che matcha più keyword."""
        assert classify("Delega al Governo in materia di lavoro") == ["delega", "lavoro"]

    def test_no_match(self) -> None:
        """Titolo che non matcha nessuna regola."""
        assert classify("Disposizioni in materia di istruzione") == []

    def test_empty_title(self) -> None:
        assert classify("") == []

    def test_none_title(self) -> None:
        assert classify("") == []  # titolo vuoto

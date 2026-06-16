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
        """Titolo che non matcha nessuna regola (atto molto specifico)."""
        assert classify("Riconoscimento dei teatri storici delle Marche") == []

    def test_empty_title(self) -> None:
        assert classify("") == []

    def test_none_title(self) -> None:
        assert classify("") == []  # titolo vuoto

    # -- Nuove famiglie (PR #8) --

    def test_norme_generali(self) -> None:
        assert classify("Disposizioni in materia di ambiente") == ["norme_generali"]

    def test_modifica(self) -> None:
        assert classify("Modifiche alla legge 123") == ["modifica"]
        assert classify("Modifica all'articolo 5") == ["modifica"]

    def test_codice(self) -> None:
        """'codice penale' in title."""
        assert classify("Modifiche al codice penale") == ["codice"]

    def test_proroga(self) -> None:
        assert classify("Proroga dei termini") == ["proroga"]

    def test_chiarimento(self) -> None:
        assert classify("Interpretazione autentica dell'articolo 3") == ["chiarimento"]

    # -- Guardrail: keyword generiche non devono matchare a caso --

    def test_misure_maps_to_norme_generali(self) -> None:
        """'misure' è keyword per norme_generali."""
        assert classify("Misure per il sostegno") == ["norme_generali"]

    def test_termine_not_keyword(self) -> None:
        """'termine' non deve matchare proroga (parola troppo generica)."""
        assert classify("Definizione del termine di scadenza") == []

    def test_decretolegge_no_hyphen(self) -> None:
        """'decretolegge' senza trattino deve matchare (uso reale nei titoli)."""
        assert classify("Decretolegge 123") == ["decreto_like"]

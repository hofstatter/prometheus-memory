"""Testes do i18n: dicionario completo nos 4 idiomas."""
import re
from pathlib import Path

I18N = Path(__file__).resolve().parent.parent / "web" / "static" / "i18n.js"


def test_i18n_dict_complete():
    src = I18N.read_text()
    entries = re.findall(r"'((?:[^'\\]|\\.)+)': \{en:'((?:[^'\\]|\\.)*)', es:'((?:[^'\\]|\\.)*)', zh:'((?:[^'\\]|\\.)*)'\}", src)
    assert len(entries) >= 40, f"dicionario pequeno: {len(entries)} entradas"
    for pt, en, es, zh in entries:
        assert pt and en and es and zh, f"entrada incompleta: {pt[:30]}"


def test_i18n_has_selector_and_detect():
    src = I18N.read_text()
    assert "lang-select" in src
    assert "navigator.language" in src
    assert "prometheus_lang" in src
    assert "MutationObserver" in src

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_duelo_perfil_has_green_and_blue_lines_for_four_metrics():
    """Verify that perfil.html renders green and blue progress lines for Gols, Nota Média, and Vitórias."""
    perfil_html = (ROOT / "templates" / "perfil.html").read_text(encoding="utf-8")

    assert "GOLS" in perfil_html
    assert "NOTA MÉDIA" in perfil_html
    assert "VITÓRIAS" in perfil_html

    # Check for green (#22c55e) and blue (#3b82f6)
    assert "#22c55e" in perfil_html
    assert "#3b82f6" in perfil_html

    # Check global window exposure
    assert "window.carregarDueloPerfil = carregarDueloPerfil;" in perfil_html


def test_duelo_comparar_page_has_green_and_blue_lines_for_four_metrics():
    """Verify that comparar.html renders green and blue progress lines for Gols, Nota Média, and Vitórias."""
    comparar_html = (ROOT / "templates" / "comparar.html").read_text(encoding="utf-8")

    assert "GOLS" in comparar_html
    assert "NOTA MÉDIA" in comparar_html
    assert "VITÓRIAS" in comparar_html

    assert "#22c55e" in comparar_html
    assert "#3b82f6" in comparar_html


def test_app_shell_delegates_duelo_select_change_event():
    """Verify that static/app-shell.js delegates change events for #dueloOponenteSelect."""
    app_shell_js = (ROOT / "static" / "app-shell.js").read_text(encoding="utf-8")
    assert "event.target.closest('#dueloOponenteSelect')" in app_shell_js
    assert "window.carregarDueloPerfil(oponenteId, jogadorId)" in app_shell_js

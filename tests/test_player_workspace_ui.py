from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_common_player_pages_use_player_workspace_theme():
    templates = (
        "templates/index.html",
        "templates/perfil.html",
        "templates/perfil_jogador.html",
        "templates/votacao_usuario.html",
        "templates/ranking.html",
        "templates/historico.html",
        "templates/sorteio_detalhe.html",
    )

    for template in templates:
        assert "player-workspace-page" in _read(template), template


def test_player_workspace_reuses_official_judge_palette():
    stylesheet = _read("static/style.css")

    assert ".player-workspace-page {" in stylesheet
    assert "--player-green: #22c55e;" in stylesheet
    assert "--player-purple: #8b5cf6;" in stylesheet
    assert "--player-pink: #ec4899;" in stylesheet
    assert "width: min(100%, 1180px);" in stylesheet


def test_current_stylesheet_version_is_used_by_main_shell():
    base = _read("templates/base.html")
    service_worker = _read("static/service-worker.js")

    assert "style.css', v='20260615-2'" in base
    assert "service-worker.js?v=20260615-2" in base
    assert "const SW_VERSION = '20260615-2';" in service_worker


def test_own_player_card_opens_private_profile():
    template = _read("templates/index.html")
    auth_routes = _read("routes/auth_routes.py")

    assert "jogador.owner_user_id == auth_user.id" in template
    assert "url_for('auth.perfil_page')" in template
    assert "Meu perfil" in template
    assert "jogador.owner_user_id == session.get('user_id')" in auth_routes


def test_private_profile_uses_same_dossier_as_public_profiles():
    private_profile = _read("templates/perfil.html")
    public_profile = _read("templates/perfil_jogador.html")

    for class_name in (
        "profile-page--public",
        "public-profile-dossier",
        "public-profile-hero",
        "public-profile-kpi-strip",
        "public-profile-recent-section",
    ):
        assert class_name in private_profile
        assert class_name in public_profile


def test_private_profile_security_dialog_is_accessible_and_responsive():
    template = _read("templates/perfil.html")
    stylesheet = _read("static/style.css")

    assert "profile-account-access" in template
    assert 'id="passwordDialog"' in template
    assert 'aria-haspopup="dialog"' in template
    assert 'autocomplete="current-password"' in template
    assert template.count('autocomplete="new-password"') == 2
    assert template.count("data-password-toggle") >= 3
    assert 'aria-pressed="false"' in template
    assert "dialog.showModal()" in template
    assert "data-required" in template
    assert ".profile-security-dialog::backdrop" in stylesheet
    assert "@media (max-width: 700px)" in stylesheet


def test_header_profile_shortcut_has_visible_emphasis():
    header = _read("templates/_brand_header.html")
    stylesheet = _read("static/style.css")

    assert header.count("brand-profile-shortcut") == 2
    assert ".auth-links .brand-profile-shortcut {" in stylesheet

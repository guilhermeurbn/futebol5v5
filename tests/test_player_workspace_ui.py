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

    assert "style.css', v='20260616-06'" in base
    assert "service-worker.js?v=20260616-06" in base
    assert "const SW_VERSION = '20260616-06';" in service_worker


def test_player_workspace_navigation_fits_without_mobile_horizontal_scroll():
    stylesheet = _read("static/style.css")
    rules = stylesheet.split("@media (max-width: 700px)", 1)[1]

    assert ".player-workspace-page .nav-tabs {" in rules
    assert "display: grid;" in rules
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in rules
    assert "overflow-x: visible;" in rules
    assert ".player-workspace-page .nav-tab {" in rules
    assert "min-width: 0;" in rules
    assert "overflow-wrap: anywhere;" in rules


def test_player_vote_notification_is_global_and_actionable():
    base = _read("templates/base.html")
    app_py = _read("app.py")
    stylesheet = _read("static/style.css")

    assert "votacao_service.obter_pendencia_usuario(session.get('user_id'))" in app_py
    assert "votacao_pendente_url = url_for('votacao.votacao_page')" in app_py
    assert "player-vote-notification" in base
    assert "data-vote-notification-dismiss" in base
    assert "}, 7000);" in base
    assert "pointermove" in base
    assert "sessionStorage" not in base
    assert "Votação aberta" in base
    assert "Minha votação" in base
    assert ".player-vote-notification {" in stylesheet
    assert "bottom: 1rem;" in stylesheet
    assert ".player-vote-notification__dismiss" in stylesheet
    assert "@media (max-width: 520px)" in stylesheet


def test_user_vote_page_is_compact_for_mobile_touch_flow():
    template = _read("templates/votacao_usuario.html")
    stylesheet = _read("static/style.css")

    assert "vote-mobile-hero" in template
    assert "vote-mobile-chips" in template
    assert "partida.aberta_em|dt_pt_hm" in template
    assert "partida.fecha_em|dt_pt_hm if partida.fecha_em else 'Sem prazo'" not in template
    assert "Avalie 5+" in template
    assert ">Salvar</button>" in template
    assert "O juiz abriu esta votação" not in template
    assert ".player-workspace-page .vote-mobile-submit" in stylesheet
    assert "position: sticky;" in stylesheet
    assert ".player-workspace-page .votacao-slider::-webkit-slider-thumb" in stylesheet


def test_player_listing_is_alphabetical_and_omits_private_profile_card_action():
    template = _read("templates/index.html")
    jogador_routes = _read("routes/jogador_crud_routes.py")

    assert "_preparar_jogadores_para_lista(jogador_service.listar_para_dict())" in jogador_routes
    assert "_nome_para_ordenacao(jogador.get('nome', ''))" in jogador_routes
    assert "role == 'usuario'" in jogador_routes
    assert "jogador.get('owner_user_id') == usuario_id" in jogador_routes
    assert "Meu perfil" not in template
    assert "url_for('auth.perfil_page')" not in template
    assert "url_for('jogador.perfil_jogador_publico', jogador_id=jogador.id)" in template


def test_player_listing_filter_tabs_match_card_metadata():
    template = _read("templates/index.html")
    app_shell = _read("static/app-shell.js")

    for filter_name in ("all", "fixo", "avulso", "goleiro", "linha"):
        assert f'data-filter="{filter_name}"' in template

    assert 'data-tipo="{{ jogador.tipo }}"' in template
    assert 'data-posicao="{{ jogador.posicao }}"' in template

    for expected_branch in (
        "filterValue === 'all'",
        "filterValue === 'fixo' && tipo === 'fixo'",
        "filterValue === 'avulso' && tipo === 'avulso'",
        "filterValue === 'goleiro' && posicao === 'goleiro'",
        "filterValue === 'linha' && posicao === 'linha'",
    ):
        assert expected_branch in template
        assert expected_branch in app_shell

    assert "card.style.setProperty('display', 'none', 'important');" in template
    assert "card.style.setProperty('display', 'none', 'important');" in app_shell
    assert "card.style.removeProperty('display');" in app_shell


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


def test_unified_public_profile_route_resolution():
    """Testa que rotas como /perfil_alex ou /perfil/alex resolvem o perfil do jogador usando o template unificado"""
    from app import app
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'user-admin-1'
            sess['role'] = 'admin'

        res = client.get('/perfil_alex', follow_redirects=True)
        assert res.status_code == 200
        assert b'perfil' in res.data.lower()


def test_private_profile_lightbulb_guide_modal():
    template = _read("templates/perfil.html")
    stylesheet = _read("static/style.css")

    assert "profile-guide-trigger" in template
    assert 'id="openProfileGuideBtn"' in template
    assert ".profile-guide-trigger {" in stylesheet




from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_judge_home_only_starts_the_creation_flow():
    template = (ROOT / 'templates' / 'juiz_home.html').read_text(encoding='utf-8')
    base_template = (ROOT / 'templates' / 'base.html').read_text(encoding='utf-8')

    assert "url_for('juiz.juiz_criar_partida')" in template
    assert 'Selecionar jogadores' in template
    assert 'class="jogador-checkbox"' not in template
    assert "session.get('role') == 'juiz'" in base_template
    assert 'target="_blank"' not in template


def test_judge_creation_uses_compact_selection_controls():
    template = (ROOT / 'templates' / 'juiz_criar_partida.html').read_text(encoding='utf-8')

    assert template.count('class="qty-btn judge-format-option"') == 3
    assert 'class="judge-player-option"' in template
    assert 'class="judge-player-option__bg"' in template
    assert 'class="judge-player-option__level"' in template
    assert template.count('judge-player-option__tag') >= 2
    assert 'id="progressoSelecao"' in template
    assert template.index('class="players-grid judge-players-grid"') < template.index(
        'id="acoesSorteio"'
    )


def test_judge_format_color_overrides_generic_quantity_button():
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    assert '.qty-btn.judge-format-option {' in stylesheet
    assert '--judge-ink: #d8d4e3;' in stylesheet
    assert '.judge-selection-progress.is-complete span {' in stylesheet


def test_judge_navigation_is_present_in_workflow_pages():
    base_template = (ROOT / 'templates' / 'base.html').read_text(encoding='utf-8')
    navigation = (ROOT / 'templates' / '_judge_nav.html').read_text(encoding='utf-8')

    assert "session.get('role') == 'juiz'" in base_template
    assert "url_for('juiz.jogar_page')" in base_template
    assert "url_for('juiz.juiz_times_page')" in base_template
    assert "url_for('votacao.votacao_admin_page')" in base_template
    assert "url_for('juiz.juiz_historico')" in base_template
    assert "url_for('juiz.juiz_cronometro')" in base_template
    assert "current_section in ['home', 'criar']" in navigation
    assert 'class="judge-nav-shell"' in navigation
    assert "url_for('juiz.juiz_times_page', sorteio_id=nav_sorteio_id)" in navigation
    assert "url_for('juiz.juiz_historico')" in navigation


def test_judge_result_only_offers_share_and_voting():
    template = (ROOT / 'templates' / 'juiz_times.html').read_text(encoding='utf-8')

    assert 'Compartilhar' in template
    assert 'Substituir Jogador' in template
    assert 'juiz.juiz_substituir_jogador' in template
    assert 'Registrar resultado' not in template


def test_judge_team_editing_supports_touch_swap():
    template = (ROOT / 'templates' / 'juiz_times.html').read_text(encoding='utf-8')
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    assert "const touchEditMode = window.matchMedia" in template
    assert "function selectPlayerForSwap(player)" in template
    assert "Toque em um jogador e depois em outro" in template
    assert "player.addEventListener('click'" in template
    assert "player.addEventListener('keydown'" in template
    assert "swapPlayers(source, player);" in template
    assert ".judge-times-touch-edit-mode .judge-team-player.is-touch-swappable" in stylesheet
    assert ".judge-team-player.is-swap-selected" in stylesheet


def test_judge_team_editing_save_replaces_edit_without_cancel():
    template = (ROOT / 'templates' / 'juiz_times.html').read_text(encoding='utf-8')

    assert 'id="btnEditarTimes"' in template
    assert 'id="btnSalvarTrocas"' in template
    assert 'id="btnCancelarTrocas"' not in template
    assert "btnSalvar.disabled = false;" in template
    assert "Nenhuma troca feita. Edição encerrada." in template


def test_judge_navigation_has_a_dedicated_times_tab():
    navigation = (ROOT / 'templates' / '_judge_nav.html').read_text(encoding='utf-8')
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    assert '<span class="judge-nav__label">Times</span>' in navigation
    assert "current_section == 'times'" in navigation
    assert '<span class="judge-nav__label">Histórico</span>' in navigation
    assert "url_for('juiz.juiz_historico')" in navigation
    assert 'grid-template-columns: repeat(5, 1fr);' in stylesheet


def test_history_only_lives_on_the_dedicated_judge_page():
    times = (ROOT / 'templates' / 'juiz_times.html').read_text(encoding='utf-8')
    voting = (ROOT / 'templates' / 'votacao_admin.html').read_text(encoding='utf-8')
    history = (ROOT / 'templates' / 'juiz_historico.html').read_text(encoding='utf-8')

    assert 'judge-draw-history' not in times
    assert 'Resultados anteriores' not in voting
    assert 'Histórico de sorteios' in history
    assert 'judge-draw-history__item' in history


def test_share_page_only_exposes_txt_and_pdf():
    template = (ROOT / 'templates' / 'juiz_compartilhar.html').read_text(encoding='utf-8')

    assert "url_for(\"stats.api_export_sorteio_txt\")" in template
    assert 'navigator.clipboard.writeText' in template
    assert '>Copiar<' in template
    assert "url_for('stats.export_sorteio_pdf')" in template
    assert 'CSV' not in template
    assert 'QR Code' not in template


def test_judge_voting_is_presented_as_two_sequential_steps():
    template = (ROOT / 'templates' / 'votacao_admin.html').read_text(encoding='utf-8')
    routes = (ROOT / 'routes' / 'votacao_routes.py').read_text(encoding='utf-8')

    assert 'Resultado dos times' in template
    assert 'Abrir votação por 20 horas' in template
    assert 'Registre o resultado dos times para continuar' in template
    assert 'name="vitorias_{{ time.numero }}"' in template
    assert 'duracao_horas=20' in routes


def test_judge_result_values_are_only_changed_with_stepper_buttons():
    template = (ROOT / 'templates' / 'votacao_admin.html').read_text(encoding='utf-8')

    assert 'type="number" name="vitorias_{{ time.numero }}"' not in template
    assert 'type="hidden" name="vitorias_{{ time.numero }}"' in template
    assert template.count('class="judge-result-value"') == 4
    assert template.count('judge-result-dec judge-result-stepper__btn') == 4
    assert template.count('judge-result-inc judge-result-stepper__btn') == 4
    assert 'class="judge-result-team__summary"' in template
    assert 'class="judge-result-team__arrow"' in template
    assert 'class="judge-result-submit"' in template
    assert 'input.focus()' not in template


def test_judge_result_card_is_touch_friendly_on_mobile():
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')
    phone_rules = stylesheet.split('@media (max-width: 720px)', 1)[1]

    assert '.judge-result-fields {' in phone_rules
    assert 'grid-template-columns: 1fr;' in phone_rules
    assert '.judge-result-stepper {' in phone_rules
    assert 'max-width: 240px;' in phone_rules
    assert 'margin: 0 auto;' in phone_rules
    assert 'min-height: 42px;' in phone_rules
    assert '.judge-result-submit {' in phone_rules
    assert 'position: sticky;' in phone_rules


def test_judge_navigation_stays_below_header_in_document_flow():
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    judge_nav_rule = stylesheet.split('.judge-nav {', 1)[1].split('}', 1)[0]
    assert 'position: static;' in judge_nav_rule
    assert 'position: fixed;' not in judge_nav_rule


def test_judge_workspace_has_phone_first_layout():
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    assert '/* Judge workspace: phone-first refinements */' in stylesheet
    assert 'grid-template-columns: repeat(5, minmax(0, 1fr));' in stylesheet
    assert 'font-size: clamp(0.5rem, 2.45vw, 0.66rem);' in stylesheet
    assert 'padding-bottom' not in stylesheet.split(
        '/* Judge workspace: phone-first refinements */', 1
    )[1].split('@media (max-width: 370px)', 1)[0]
    assert 'calc(1.25rem + env(safe-area-inset-bottom))' in stylesheet
    assert '.players-grid.judge-players-grid {' in stylesheet
    assert 'grid-template-columns: repeat(2, minmax(0, 1fr));' in stylesheet
    assert '@media (max-width: 370px)' in stylesheet
    assert 'min-height: 48px;' in stylesheet
    assert '/* Judge creation: thumb-friendly floating draw action on phones */' in stylesheet
    assert '.judge-create-page .judge-create-action {' in stylesheet
    assert 'position: fixed;' in stylesheet
    assert 'bottom: calc(var(--site-footer-height-mobile) + 0.55rem + env(safe-area-inset-bottom));' in stylesheet
    assert 'opacity: 0.92;' in stylesheet
    assert '.judge-create-page .judge-create-action.is-ready {' in stylesheet
    assert 'opacity: 1;' in stylesheet


def test_judge_phone_titles_use_compact_hierarchy():
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    assert '/* Judge headings: compact, readable hierarchy on phones */' in stylesheet
    assert '.judge-workspace-page .judge-flow-card h1,' in stylesheet
    assert 'font-size: clamp(1.35rem, 7vw, 1.65rem);' in stylesheet
    assert '.judge-workspace-page .judge-voting-step__header {' in stylesheet
    assert 'grid-template-columns: 2.2rem minmax(0, 1fr);' in stylesheet


def test_judge_last_match_clickable_card_and_deep_links():
    home_template = (ROOT / 'templates' / 'juiz_home.html').read_text(encoding='utf-8')
    assert "url_for('juiz.juiz_historico', sorteio_id=ultima_partida.sorteio_id)" in home_template
    assert "class=\"judge-flow-card judge-last-match-card\"" in home_template
    assert "class=\"judge-flow-card judge-start-card\"" in home_template
    assert "judge-start-card__header" in home_template
    assert "judge-start-card__badge" in home_template

    history_template = (ROOT / 'templates' / 'juiz_historico.html').read_text(encoding='utf-8')
    assert "sorteio_destaque_id" in history_template
    assert "id=\"sorteio-{{ item.id }}\"" in history_template

    base_template = (ROOT / 'templates' / 'base.html').read_text(encoding='utf-8')
    assert "session.get('role') == 'juiz'" in base_template
    assert "is-referee-layout" in base_template
    assert "url_for('juiz.juiz_cronometro')" in base_template
    assert "url_for('jogador.logout')" in base_template

    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')
    assert ".judge-last-match-card" in stylesheet
    assert ".judge-draw-history__item:target" in stylesheet
    assert ".judge-start-card" in stylesheet
    assert ".judge-start-card__header" in stylesheet
    assert "body.is-referee-layout" in stylesheet
    assert "body.is-referee-layout .site-topbar" in stylesheet
    assert "body.is-referee-layout .site-footer" in stylesheet
    assert "body.is-referee-layout .site-footer__link" in stylesheet
    assert ".judge-teams-page .judge-team-card" in stylesheet
    assert ".judge-teams-page .judge-teams-toolbar" in stylesheet

    times_template = (ROOT / 'templates' / 'juiz_times.html').read_text(encoding='utf-8')
    assert "judge-card-edit-btn" in times_template
    assert "copiarSorteio" in times_template
    assert "stats.export_sorteio_pdf" in times_template


def test_judge_history_matches_admin_except_delete():
    history_template = (ROOT / 'templates' / 'juiz_historico.html').read_text(encoding='utf-8')
    assert "abrirModalTrocarFoto" in history_template
    assert "Trocar Foto" in history_template
    assert "Adicionar Foto" in history_template
    assert "current_user.role in ['admin', 'juiz']" in history_template
    assert "{% if current_user.role == 'admin' %}" in history_template
    assert "Excluir Sorteio" in history_template


from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_judge_home_only_starts_the_creation_flow():
    template = (ROOT / 'templates' / 'juiz_home.html').read_text(encoding='utf-8')

    assert "url_for('juiz.juiz_criar_partida')" in template
    assert 'Selecionar jogadores' in template
    assert 'class="jogador-checkbox"' not in template
    assert "{% include '_judge_nav.html' %}" in template
    assert 'target="_blank"' not in template


def test_judge_creation_uses_compact_selection_controls():
    template = (ROOT / 'templates' / 'juiz_criar_partida.html').read_text(encoding='utf-8')

    assert template.count('class="qty-btn judge-format-option"') == 3
    assert 'class="judge-player-option"' in template
    assert 'class="judge-player-option__bg"' in template
    assert 'class="judge-player-option__level"' in template
    assert template.count('judge-player-option__tag') >= 2
    assert 'id="orientacaoSelecao"' in template
    assert 'id="progressoSelecao"' in template


def test_judge_format_color_overrides_generic_quantity_button():
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    assert '.qty-btn.judge-format-option {' in stylesheet
    assert '--judge-ink: #d8d4e3;' in stylesheet
    assert '.judge-selection-progress.is-complete span {' in stylesheet


def test_judge_navigation_is_present_in_workflow_pages():
    judge_times = (ROOT / 'templates' / 'juiz_times.html').read_text(encoding='utf-8')
    voting = (ROOT / 'templates' / 'votacao_admin.html').read_text(encoding='utf-8')
    navigation = (ROOT / 'templates' / '_judge_nav.html').read_text(encoding='utf-8')

    assert "{% include '_judge_nav.html' %}" in judge_times
    assert "{% set current_section = 'times' %}" in judge_times
    assert "{% include '_judge_nav.html' %}" in voting
    assert "current_section in ['home', 'criar']" in navigation
    assert 'class="judge-nav-shell"' in navigation
    assert "url_for('partida.ver_sorteio'" in navigation
    assert "url_for('partida.compartilhar_sorteio'" in navigation


def test_judge_result_only_offers_share_and_voting():
    template = (ROOT / 'templates' / 'juiz_times.html').read_text(encoding='utf-8')

    assert 'Compartilhar' in template
    assert 'Ir para votações' in template
    assert 'Registrar resultado' not in template


def test_judge_navigation_has_a_dedicated_times_tab():
    navigation = (ROOT / 'templates' / '_judge_nav.html').read_text(encoding='utf-8')
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    assert '<span class="judge-nav__label">Times</span>' in navigation
    assert "current_section == 'compartilhar'" in navigation
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
    assert 'Abrir votação por 12 horas' in template
    assert 'Registre o resultado dos times para continuar' in template
    assert 'name="vitorias_{{ time.numero }}"' in template
    assert 'duracao_horas=12' in routes


def test_judge_navigation_stays_below_header_in_document_flow():
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    judge_nav_rule = stylesheet.split('.judge-nav {', 1)[1].split('}', 1)[0]
    assert 'position: static;' in judge_nav_rule
    assert 'position: fixed;' not in judge_nav_rule


def test_judge_workspace_has_phone_first_layout():
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    assert '/* Judge workspace: phone-first refinements */' in stylesheet
    assert 'scroll-snap-type: x proximity;' in stylesheet
    assert 'padding-bottom' not in stylesheet.split(
        '/* Judge workspace: phone-first refinements */', 1
    )[1].split('@media (max-width: 370px)', 1)[0]
    assert 'calc(1.25rem + env(safe-area-inset-bottom))' in stylesheet
    assert '.players-grid.judge-players-grid {' in stylesheet
    assert 'grid-template-columns: repeat(2, minmax(0, 1fr));' in stylesheet
    assert '@media (max-width: 370px)' in stylesheet
    assert 'min-height: 48px;' in stylesheet

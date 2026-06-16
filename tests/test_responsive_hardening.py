from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_global_layout_prevents_horizontal_page_overflow():
    stylesheet = _read("static/style.css")

    assert "Responsive hardening: shared across every page and workflow" in stylesheet
    assert "overflow-x: clip;" in stylesheet
    assert ".table-shell," in stylesheet
    assert "overflow-x: auto;" in stylesheet
    assert "overscroll-behavior-inline: contain;" in stylesheet


def test_shared_media_and_form_controls_are_fluid():
    stylesheet = _read("static/style.css")

    assert "img,\nsvg,\nvideo,\ncanvas,\niframe {" in stylesheet
    assert "button,\ninput,\nselect,\ntextarea {" in stylesheet
    assert "@media (hover: none) and (pointer: coarse)" in stylesheet
    assert "min-height: 44px;" in stylesheet


def test_phone_breakpoints_cover_actions_navigation_and_dialogs():
    stylesheet = _read("static/style.css")

    phone_rules = stylesheet.split("@media (max-width: 480px)", 1)[1]
    assert ".section-header-actions {" in phone_rules
    assert "grid-template-columns: 1fr;" in phone_rules
    assert ".nav-tabs {" in phone_rules
    assert ".judge-next-actions__buttons {" in phone_rules
    assert ".admin-delete-modal__actions," in phone_rules


def test_all_standalone_shells_use_current_stylesheet_version():
    templates = (
        "templates/base.html",
        "templates/_auth_layout.html",
        "templates/estatisticas.html",
        "templates/selecionar.html",
        "templates/sorteio_detalhe.html",
        "templates/stats_combos.html",
        "templates/stats_players.html",
        "templates/stats_times.html",
        "templates/times.html",
    )

    for template in templates:
        assert "style.css', v='20260616-06'" in _read(template), template


def test_all_shells_load_local_datetime_formatter():
    templates = (
        "templates/base.html",
        "templates/_auth_layout.html",
        "templates/estatisticas.html",
        "templates/selecionar.html",
        "templates/sorteio_detalhe.html",
        "templates/stats_combos.html",
        "templates/stats_players.html",
        "templates/stats_times.html",
        "templates/times.html",
    )
    script = _read("static/local-datetime.js")
    app_py = _read("app.py")

    for template in templates:
        assert "local-datetime.js', v='20260616-06'" in _read(template), template

    assert "hour12: false" in script
    assert "hourCycle: 'h23'" in script
    assert "data-local-datetime" in app_py
    assert "data-local-date" in app_py


def test_judge_navigation_titles_fit_phone_width_inside_bordered_cards():
    stylesheet = _read("static/style.css")
    rules = stylesheet.split(
        "/* Judge navigation: bordered titles that always fit on phones */",
        1,
    )[1]

    assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in rules
    assert "overflow: visible;" in rules
    assert "border: 1px solid rgba(167, 139, 250, 0.16);" in rules
    assert "white-space: normal;" in rules
    assert "overflow-wrap: anywhere;" in rules


def test_judge_timer_starts_at_ten_with_only_five_and_eight_minute_presets():
    template = _read("templates/juiz_cronometro.html")
    stylesheet = _read("static/style.css")
    rules = stylesheet.split(
        "/* Judge timer: focused controls for phones, desktop layout stays unchanged */",
        1,
    )[1]

    assert "judge-timer-adjust--minus" in template
    assert "judge-timer-adjust--plus" in template
    assert 'id="judgeTimerDisplay" aria-live="polite">10:00<' in template
    assert "const DEFAULT_SECONDS = 10 * 60;" in template
    assert template.count('class="judge-timer-preset"') == 2
    assert 'data-seconds="480">8 min</button>' in template
    assert 'data-seconds="300">5 min</button>' in template
    assert 'type="number"' not in template
    assert "CUSTOM_PRESET_KEY" not in template
    assert ".judge-timer-page .judge-timer-presets {" in rules
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in rules
    assert '"toggle toggle"' in rules
    assert '"minus plus"' in rules
    assert '"reset reset"' in rules
    assert "gap: 0.8rem 1.15rem;" in rules

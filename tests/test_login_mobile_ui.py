from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_mobile_login_does_not_force_focus_or_scroll_on_refresh():
    template = (ROOT / 'templates' / 'login.html').read_text(encoding='utf-8')
    layout = (ROOT / 'templates' / '_auth_layout.html').read_text(encoding='utf-8')

    assert 'autofocus' not in template
    assert 'history.scrollRestoration = ' in layout
    assert "navegacao?.type === 'reload'" in layout
    assert 'window.scrollTo(0, 0)' in layout


def test_mobile_login_shows_more_content_hint():
    template = (ROOT / 'templates' / 'login.html').read_text(encoding='utf-8')
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    assert 'Continue para entrar' not in template
    assert 'href="#loginFormPanel"' in template
    assert 'aria-label="Ir para o formulário de login"' in template
    assert '.auth-scroll-hint {' in stylesheet
    assert '.auth-scroll-hint.is-hidden {' in stylesheet
    assert 'env(safe-area-inset-bottom)' in stylesheet
    assert 'position: fixed;' in stylesheet.rsplit(
        '.auth-scroll-hint {', 1
    )[1].split('}', 1)[0]
    assert 'backdrop-filter: blur(20px) saturate(145%);' in stylesheet


def test_mobile_login_intro_centers_brand_and_uses_vertical_cards():
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    assert '.auth-page--login .auth-panel--intro-hero {' in stylesheet
    assert '.auth-page--login .auth-panel__brand--hero {' in stylesheet
    assert 'justify-items: center;' in stylesheet
    assert '.auth-page--login .auth-title--hero-lockup {' in stylesheet
    assert '.auth-page--login .auth-preview-grid {' in stylesheet
    assert 'grid-template-columns: 1fr;' in stylesheet
    assert '.auth-page--login .auth-preview-card {' in stylesheet
    assert 'min-height: 112px;' in stylesheet

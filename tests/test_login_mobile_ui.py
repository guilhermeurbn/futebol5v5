from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_mobile_login_does_not_force_focus_or_scroll_on_refresh():
    template = (ROOT / 'templates' / 'login.html').read_text(encoding='utf-8')
    layout = (ROOT / 'templates' / '_auth_layout.html').read_text(encoding='utf-8')

    assert 'autofocus' not in template
    assert 'history.scrollRestoration = ' in layout
    assert "window.location.hash === '#loginFormPanel'" in layout
    assert 'window.scrollTo(0, 0)' in layout


def test_mobile_login_shows_more_content_hint():
    template = (ROOT / 'templates' / 'login.html').read_text(encoding='utf-8')
    stylesheet = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')

    assert 'Continue para entrar' not in template
    assert 'id="loginScrollHint"' in template
    assert 'href="#loginFormPanel"' not in template
    layout = (ROOT / 'templates' / '_auth_layout.html').read_text(encoding='utf-8')
    assert 'formulario.scrollIntoView({' in layout
    assert 'window.setTimeout(function () {' in layout
    assert '}, 1500);' in layout
    assert 'aria-label="Ir para o formulário de login"' in template
    assert '.auth-scroll-hint {' in stylesheet
    assert '.auth-scroll-hint.is-hidden {' in stylesheet
    assert 'env(safe-area-inset-bottom)' in stylesheet
    assert 'position: fixed;' in stylesheet.rsplit(
        '.auth-scroll-hint {', 1
    )[1].split('}', 1)[0]
    assert 'top: 72%;' in stylesheet
    assert 'left: 50%;' in stylesheet
    assert 'transform: translate(-50%, -50%);' in stylesheet
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
    assert 'min-height: 92px;' in stylesheet


def test_login_assumes_single_app_position_and_onboarding_persistence():
    layout = (ROOT / 'templates' / '_auth_layout.html').read_text(encoding='utf-8')
    app_onboarding = (ROOT / 'static' / 'app-onboarding.js').read_text(encoding='utf-8')
    auth_routes = (ROOT / 'routes' / 'auth_routes.py').read_text(encoding='utf-8')

    assert '<body class="auth-page is-capacitor-app' in layout
    assert "document.body.classList.add('is-capacitor-app');" in app_onboarding
    assert "const onboardingKey = 'natrave_app_onboarding_completed_v1';" in app_onboarding
    assert "show_onboarding = not bool(erro or sucesso)" in auth_routes
    assert "dots.forEach((dot, index) => {" in app_onboarding
    assert "slidesContainer.addEventListener('touchstart'" in app_onboarding


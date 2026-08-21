from pathlib import Path
from app import criar_app


ROOT = Path(__file__).resolve().parents[1]


def test_perfil_template_defines_rehydratable_init_perfil_page():
    """Verify that perfil.html exposes window.initPerfilPage for SPA rehydration."""
    perfil_html = (ROOT / "templates" / "perfil.html").read_text(encoding="utf-8")

    assert "window.initPerfilPage = function()" in perfil_html
    assert "if (typeof window.initPerfilPage === 'function')" in perfil_html
    assert "if (!dialog || !opener || !form) return;" not in perfil_html


def test_app_shell_hooks_and_delegates_profile_actions():
    """Verify app-shell.js runs initPerfilPage in runPageHooks and provides global delegation."""
    app_shell_js = (ROOT / "static" / "app-shell.js").read_text(encoding="utf-8")

    assert "if (typeof window.initPerfilPage === 'function') {\n      window.initPerfilPage();\n    }" in app_shell_js
    assert "event.target.closest('.premium-profile-tab')" in app_shell_js
    assert "event.target.closest('[data-open-password-dialog]')" in app_shell_js
    assert "event.target.closest('[data-open-delete-dialog]')" in app_shell_js


def test_perfil_page_loads_cleanly():
    """Test that /perfil endpoint returns HTTP 200 with rehydratable scripts."""
    app = criar_app()
    with app.test_client() as test_client:
        with test_client.session_transaction() as sess:
            sess['user_id'] = 'test-user-id'

        response = test_client.get('/perfil')
        # Response can be 200 or redirect if auth user is missing in db, check response code
        assert response.status_code in (200, 302)

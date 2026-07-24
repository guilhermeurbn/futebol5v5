from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import routes.auth_routes as auth_routes
from app import criar_app


def _fake_user():
    return {
        'id': 'user-remember',
        'username': 'remember',
        'nome': 'Remember User',
        'role': 'usuario',
        'senha_temporaria_ativa': False,
    }


def test_login_with_remember_me_sets_permanent_session(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    monkeypatch.setattr(auth_routes.auth_service, 'autenticar', lambda username, password: _fake_user())

    with app.test_client() as client:
        response = client.post('/login', data={
            'username': 'remember',
            'password': 'secret',
            'remember_me': '1',
        })

        with client.session_transaction() as sess:
            assert sess.permanent is True
            assert sess['user_id'] == 'user-remember'
            assert sess.get('remember_me') is True

    assert response.status_code == 302
    
    # Verify the Set-Cookie header has an Expires attribute (signaling a permanent cookie)
    cookie_headers = response.headers.getlist('Set-Cookie')
    has_expires = any('Expires=' in h or 'expires=' in h or 'Max-Age=' in h for h in cookie_headers)
    assert has_expires, "Permanent session must set cookie Expires/Max-Age header"


def test_login_without_remember_me_uses_browser_session(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    monkeypatch.setattr(auth_routes.auth_service, 'autenticar', lambda username, password: _fake_user())

    with app.test_client() as client:
        response = client.post('/login', data={
            'username': 'remember',
            'password': 'secret',
        })

        with client.session_transaction() as sess:
            assert sess.permanent is False
            assert sess['user_id'] == 'user-remember'

    assert response.status_code == 302

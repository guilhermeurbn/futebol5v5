from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import criar_app


def _auth_session(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 'test-user'
        sess['username'] = 'tester'
        sess['nome'] = 'Tester'
        sess['role'] = 'usuario'
        sess['senha_temporaria_ativa'] = False


def test_site_shell_uses_regular_layout():
    app = criar_app('testing')

    with app.test_client() as client:
        _auth_session(client)
        response = client.get('/ranking')

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'class="app-shell' in body


def test_site_shell_stays_unwrapped():
    app = criar_app('testing')

    with app.test_client() as client:
        _auth_session(client)
        response = client.get('/ranking')

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'class="app-shell' in body

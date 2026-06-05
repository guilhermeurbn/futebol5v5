from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import criar_app


def _auth_session(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 'test-user'
        sess['username'] = 'tester'
        sess['nome'] = 'Tester'
        sess['role'] = 'admin'
        sess['senha_temporaria_ativa'] = False


def test_home_uses_regular_page_shell():
    app = criar_app('testing')

    with app.test_client() as client:
        _auth_session(client)
        response = client.get('/')

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'page-index' in body


def test_home_keeps_player_grid_in_regular_shell():
    app = criar_app('testing')

    with app.test_client() as client:
        _auth_session(client)
        response = client.get('/')

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'playersGrid' in body

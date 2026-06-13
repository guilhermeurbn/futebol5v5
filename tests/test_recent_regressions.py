import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import criar_app


ROOT = Path(__file__).resolve().parent.parent


def test_suggestion_apis_require_login():
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        for endpoint in ('/api/sugestoes/duplas', '/api/sugestoes/combinadas'):
            response = client.post(endpoint, json={'selecionados': []})
            assert response.status_code == 401


def test_temporary_password_profile_still_shows_password_form():
    app = criar_app('testing')

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'test-user'
            sess['username'] = 'tester'
            sess['nome'] = 'Tester'
            sess['role'] = 'usuario'
            sess['senha_temporaria_ativa'] = True

        response = client.get('/perfil')

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'senha temporária' in body
    assert 'name="nova_senha"' in body
    assert 'name="confirmar_senha"' in body
    assert 'name="senha_atual"' not in body


def test_seed_users_have_unique_usernames_and_no_pending_local_reset():
    users = json.loads((ROOT / 'data' / 'users.json').read_text(encoding='utf-8'))
    usernames = [(user.get('username') or '').strip().lower() for user in users]

    assert len(usernames) == len(set(usernames))

    guigui = next(user for user in users if user.get('username') == 'guiguiurbano')
    assert guigui.get('senha_temporaria_ativa') is False
    assert 'senha_resetada_em' not in guigui
    assert 'senha_resetada_por' not in guigui


def test_votacao_admin_post_without_csrf_redirects_to_recovery_page():
    app = criar_app('testing')

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'test-juiz'
            sess['username'] = 'juiz'
            sess['nome'] = 'Juiz Teste'
            sess['role'] = 'juiz'

        response = client.post('/admin/votacao/criar', data={'sorteio_id': '1', 'titulo': 'Teste'})

    assert response.status_code == 302
    location = response.headers.get('Location', '')
    assert '/admin/votacao' in location
    assert 'erro=' in location

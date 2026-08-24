from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import criar_app
import routes.auth_routes as auth_routes
import routes.admin_routes as admin_routes
import routes.jogador_crud_routes as jogador_crud_routes


def test_cadastro_nome_sobrenome_required():
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        # 1. Single word name should fail
        response = client.post('/cadastro', data={
            'nome': 'Guilherme',
            'email': 'gui@test.com',
            'username': 'guigui',
            'password': 'password123',
            'confirmar_password': 'password123',
        })
        assert response.status_code == 400
        assert 'Por favor, digite seu nome e sobrenome.' in response.get_data(as_text=True)


def test_cadastro_username_ja_existe(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    def mock_criar_usuario(*args, **kwargs):
        raise ValueError("Username ja existe")

    monkeypatch.setattr(auth_routes.auth_service, 'criar_usuario', mock_criar_usuario)

    with app.test_client() as client:
        response = client.post('/cadastro', data={
            'nome': 'Guilherme Urbano',
            'email': 'gui@test.com',
            'username': 'guigui',
            'password': 'password123',
            'confirmar_password': 'password123',
        })
        assert response.status_code == 400
        assert 'Este nome de usuário já está em uso. Por favor, escolha outro.' in response.get_data(as_text=True)


def test_admin_criar_usuario_nome_sobrenome_required(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    # Mock login as admin
    monkeypatch.setattr(admin_routes, '_usuario_logado', lambda: {'id': 'admin', 'role': 'admin', 'autenticado': True})
    # Mock session
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'admin'
            sess['role'] = 'admin'

        response = client.post('/admin/usuarios', data={
            'nome': 'Guilherme',
            'email': 'gui@test.com',
            'username': 'guigui',
            'password': 'password123',
            'role': 'usuario',
        })
        assert response.status_code == 400
        assert 'Por favor, insira o nome e sobrenome.' in response.get_data(as_text=True)


def test_admin_criar_usuario_posicao_goleiro(monkeypatch):
    import uuid
    uniq = str(uuid.uuid4())[:8]
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    monkeypatch.setattr(admin_routes, '_usuario_logado', lambda: {'id': 'admin', 'role': 'admin', 'autenticado': True})
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'admin'
            sess['role'] = 'admin'

        response = client.post('/admin/usuarios', data={
            'nome': f'Guilherme Goleiro {uniq}',
            'email': f'gui_goleiro_{uniq}@test.com',
            'username': f'guigoleiro{uniq}',
            'password': 'password123',
            'role': 'usuario',
            'posicao': 'goleiro',
        })
        assert response.status_code == 302 # Redirects to admin page
        
        from services.db import load_json_data
        jogadores = load_json_data('jogadores', [])
        player = [j for j in jogadores if j.get('nome') == f'Guilherme Goleiro {uniq}']
        assert len(player) >= 1
        assert player[-1].get('posicao') == 'goleiro'


def test_jogador_api_nome_sobrenome_required(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'juiz1'
            sess['role'] = 'juiz'

        response = client.post('/api/jogadores', json={
            'nome': 'Guilherme',
            'nivel': 5.0,
            'tipo': 'avulso',
            'posicao': 'linha',
        })
        assert response.status_code == 400
        assert 'Por favor, insira o nome e sobrenome do jogador.' in response.get_json().get('erro')


def test_api_check_email_availability(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    def mock_listar_usuarios():
        return [{'email': 'taken@example.com', 'username': 'taken'}]

    monkeypatch.setattr(auth_routes.auth_service, 'listar_usuarios', mock_listar_usuarios)

    with app.test_client() as client:
        # Email taken
        res1 = client.get('/api/auth/check-email?email=taken@example.com')
        assert res1.status_code == 200
        assert res1.get_json()['exists'] is True

        # Email available
        res2 = client.get('/api/auth/check-email?email=free@example.com')
        assert res2.status_code == 200
        assert res2.get_json()['exists'] is False


def test_api_check_username_availability(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    def mock_listar_usuarios():
        return [{'email': 'taken@example.com', 'username': 'taken'}]

    monkeypatch.setattr(auth_routes.auth_service, 'listar_usuarios', mock_listar_usuarios)

    with app.test_client() as client:
        # Username taken
        res1 = client.get('/api/auth/check-username?username=taken')
        assert res1.status_code == 200
        assert res1.get_json()['exists'] is True

        # Username free
        res2 = client.get('/api/auth/check-username?username=free')
        assert res2.status_code == 200
        assert res2.get_json()['exists'] is False


def test_formatar_nome_perfil_abbreviation_rule():
    from services.jogador_service import formatar_nome_perfil

    assert len(formatar_nome_perfil("Guilherme Urbano")) <= 10
    assert formatar_nome_perfil("Gui Urbano") == "Gui Urb."
    assert formatar_nome_perfil("guilherme urbano") == "guilherme."
    assert formatar_nome_perfil("João Pedro") == "João Ped."
    assert formatar_nome_perfil("Ana Silva") == "Ana Sil."
    assert formatar_nome_perfil("Bartholomew") == "Bartholom."
    assert formatar_nome_perfil("Guilherme") == "Guilherme"
    assert formatar_nome_perfil("") == ""
    assert formatar_nome_perfil(None) == ""



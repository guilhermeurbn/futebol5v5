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

    assert formatar_nome_perfil("Guilherme Urbano") == "Guilherme Ur."
    assert formatar_nome_perfil("guilherme urbano") == "guilherme ur."
    assert formatar_nome_perfil("João Pedro") == "João Pedro"
    assert formatar_nome_perfil("Gui Urbano") == "Gui Urbano"
    assert formatar_nome_perfil("Bartholomew Urbano") == "Bartholome Ur."
    assert formatar_nome_perfil("Bartholomew") == "Bartholome"
    assert formatar_nome_perfil("Guilherme") == "Guilherme"
    assert formatar_nome_perfil("") == ""

def test_editar_jogador_legacy_single_name(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    class MockJogador:
        def __init__(self, id, nome, nivel=6.5, tipo='avulso', posicao='linha'):
            self.id = id
            self.nome = nome
            self.nivel = nivel
            self.tipo = tipo
            self.posicao = posicao

    # Player 1 is legacy single name "Alex"
    # Player 2 has 2 names "Guilherme Urbano"
    players_db = {
        'p1': MockJogador('p1', 'Alex'),
        'p2': MockJogador('p2', 'Guilherme Urbano'),
    }

    def mock_obter_por_id(id):
        return players_db.get(id)

    def mock_atualizar(id, nome=None, nivel=None, tipo=None, posicao=None):
        if id in players_db and nome:
            players_db[id].nome = nome
        return players_db.get(id)

    monkeypatch.setattr(jogador_crud_routes.jogador_service, 'obter_por_id', mock_obter_por_id)
    monkeypatch.setattr(jogador_crud_routes.jogador_service, 'atualizar', mock_atualizar)
    monkeypatch.setattr(jogador_crud_routes, '_usuario_logado', lambda: {'id': 'admin', 'role': 'admin', 'autenticado': True})

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'admin'
            sess['role'] = 'admin'

        # 1. Updating legacy single-name player "Alex" to "Alex" or "Alexandre" (still 1 name) should SUCCEED
        res1 = client.post('/jogadores/p1/editar', data={'nome': 'Alexandre', 'nivel': '6.5', 'tipo': 'avulso', 'posicao': 'linha'})
        assert res1.status_code == 302
        assert players_db['p1'].nome == 'Alexandre'

        # 2. Updating 2-name player "Guilherme Urbano" to 1 single name "Guilherme" should FAIL
        res2 = client.post('/jogadores/p2/editar', data={'nome': 'Guilherme', 'nivel': '6.5', 'tipo': 'avulso', 'posicao': 'linha'})
        assert res2.status_code == 400
        assert 'Por favor, insira o nome e sobrenome do jogador.' in res2.get_data(as_text=True)





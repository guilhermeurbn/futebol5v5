import json
from pathlib import Path
import sys
from types import SimpleNamespace

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
    users = json.loads((ROOT / 'data' / 'seeds' / 'users.json').read_text(encoding='utf-8'))
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


def test_juiz_times_template_compiles():
    app = criar_app('testing')

    with app.app_context():
        app.jinja_env.get_template('juiz_times.html')


def test_admin_reset_user_without_email(monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    fake_reset_data = {
        "id": "target-user-id",
        "email": None,
        "username": "no_email_user",
        "nome": "Sem Email",
        "role": "usuario",
        "senha_temporaria": "TEMP_PWD_ABC",
    }

    import routes.admin_routes as admin_routes
    class FakeJogador:
        nome = "Sem Email"
        nivel = 5.5
        def nivel_formatado(self):
            return "5.50"
            
    monkeypatch.setattr(admin_routes, '_garantir_e_obter_jogador_vinculado', lambda u, js: FakeJogador())
    monkeypatch.setattr(admin_routes.auth_service, 'resetar_senha_por_admin', lambda user_id, executor_id: fake_reset_data)
    monkeypatch.setattr(admin_routes.auth_service, 'listar_usuarios', lambda: [fake_reset_data])
    monkeypatch.setattr(admin_routes.notificacao_service, 'listar_notificacoes', lambda **kw: [])
    monkeypatch.setattr(admin_routes.notificacao_service, 'contar_nao_lidas', lambda: 0)

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'admin-user'
            sess['username'] = 'admin'
            sess['nome'] = 'Admin'
            sess['role'] = 'admin'

        response = client.post('/admin/usuarios/target-user-id/resetar-senha')
        assert response.status_code == 302
        
        response_page = client.get('/admin/ajustes')
        assert response_page.status_code == 200
        
        body = response_page.get_data(as_text=True)
        assert 'tempPasswordModal' in body
        assert 'Senha Temporária Gerada' in body
        assert 'Sem Email' in body
        assert 'TEMP_PWD_ABC' in body
        assert 'copyTempPasswordBtn' in body
        assert 'Jogador:' in body
        assert '5.50' in body


def test_cadastro_rolls_back_user_when_player_creation_fails(tmp_path, monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    from services.auth_service import AuthService
    import routes.auth_routes as auth_routes

    users_file = tmp_path / 'users.json'
    auth_service = AuthService(arquivo=str(users_file))
    monkeypatch.setattr(auth_routes, 'auth_service', auth_service)
    monkeypatch.setattr(auth_routes, 'email_service', SimpleNamespace(send_welcome_email=lambda **kwargs: SimpleNamespace(ok=True, message_id='email_1')))
    monkeypatch.setattr(auth_routes.jogador_service, 'criar', lambda **kwargs: (_ for _ in ()).throw(RuntimeError('falha ao criar jogador')))

    with app.test_client() as client:
        response = client.post(
            '/cadastro',
            data={
                'nome': 'Novo Usuario',
                'email': 'novo@example.com',
                'username': 'novo_usuario',
                'password': 'senha123',
                'confirmar_password': 'senha123',
                'nivel': '5.5',
                'tipo': 'avulso',
                'posicao': 'linha',
            },
        )

    assert response.status_code == 500
    assert auth_service.obter_por_username('novo_usuario') is None


def test_admin_cadastro_rolls_back_user_when_player_creation_fails(tmp_path, monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    from services.auth_service import AuthService
    import routes.admin_routes as admin_routes

    users_file = tmp_path / 'users.json'
    auth_service = AuthService(arquivo=str(users_file))
    monkeypatch.setattr(admin_routes, 'auth_service', auth_service)
    monkeypatch.setattr(admin_routes, 'email_service', SimpleNamespace(send_temporary_password_email=lambda **kwargs: SimpleNamespace(ok=True, message_id='email_1')))
    monkeypatch.setattr(admin_routes.jogador_service, 'criar', lambda **kwargs: (_ for _ in ()).throw(RuntimeError('falha ao criar jogador')))

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'admin-id'
            sess['username'] = 'admin'
            sess['nome'] = 'Admin'
            sess['role'] = 'admin'

        response = client.post(
            '/admin/usuarios',
            data={
                'email': 'adminnovo@example.com',
                'username': 'adminnovo',
                'nome': 'Admin Novo',
                'password': 'senha123',
                'role': 'usuario',
            },
        )

    assert response.status_code == 500
    assert auth_service.obter_por_username('adminnovo') is None


def test_test_email_route_does_not_reset_password(tmp_path, monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    from services.auth_service import AuthService
    import routes.auth_routes as auth_routes

    users_file = tmp_path / 'users.json'
    auth_service = AuthService(arquivo=str(users_file))
    usuario = auth_service.criar_usuario(
        email='tester@example.com',
        username='tester',
        nome='Tester',
        password='senha123',
        role='usuario',
    )

    captured = {}

    def fake_send_temporary_password_email(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(ok=True, message_id='email_1')

    monkeypatch.setattr(auth_routes, 'auth_service', auth_service)
    monkeypatch.setattr(auth_routes, 'email_service', SimpleNamespace(send_temporary_password_email=fake_send_temporary_password_email))
    monkeypatch.setattr(auth_routes.auth_service, 'resetar_senha_por_admin', lambda **kwargs: (_ for _ in ()).throw(AssertionError('nao deve resetar senha')))

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = 'admin-id'
            sess['username'] = 'admin'
            sess['nome'] = 'Admin'
            sess['role'] = 'admin'

        response = client.get('/teste-email?username=tester')

    assert response.status_code == 200
    assert auth_service.autenticar('tester', 'senha123') is not None
    assert captured['to_email'] == usuario['email']
    assert captured['username'] == 'tester'
    assert captured['senha_temporaria'] != 'senha123'


def test_user_player_deletion_sync_both_ways(tmp_path, monkeypatch):
    from services.db import clear_db_cache
    clear_db_cache()
    users_file = str(tmp_path / 'users.json')
    players_file = str(tmp_path / 'jogadores.json')
    
    import services.auth_service
    import services.jogador_service
    import services.db
    import json
    
    monkeypatch.setattr(services.auth_service.AuthService, '__init__', lambda self, arquivo=users_file: setattr(self, 'arquivo', arquivo) or self._garantir_arquivo())
    monkeypatch.setattr(services.jogador_service.JogadorService, '__init__', lambda self, arquivo=players_file: setattr(self, 'arquivo', arquivo) or setattr(self, 'namespace', 'jogadores') or self._garantir_arquivo())
    
    def fake_load_json_data(namespace, default):
        if namespace == "users":
            try:
                with open(users_file, "r") as f:
                    return json.load(f)
            except:
                return []
        elif namespace == "jogadores":
            try:
                with open(players_file, "r") as f:
                    return json.load(f)
            except:
                return []
        elif namespace == "migration_user_player_link_done":
            return None
        return default
        
    def fake_save_json_data(namespace, payload):
        if namespace == "users":
            with open(users_file, "w") as f:
                json.dump(payload, f)
        elif namespace == "jogadores":
            with open(players_file, "w") as f:
                json.dump(payload, f)

    for module in [services.db, services.jogador_service, services.auth_service]:
        monkeypatch.setattr(module, 'load_json_data', fake_load_json_data)
        monkeypatch.setattr(module, 'save_json_data', fake_save_json_data)
    
    auth_service = services.auth_service.AuthService()
    jogador_service = services.jogador_service.JogadorService()
    
    user = auth_service.criar_usuario(
        email='sync@example.com',
        username='sync_user',
        nome='Sync User',
        password='password123',
        role='usuario'
    )
    
    player = jogador_service.criar(
        nome='Sync User',
        nivel=5.5,
        tipo='avulso',
        posicao='linha',
        owner_user_id=user['id']
    )
    
    assert auth_service.obter_por_id(user['id']) is not None
    assert jogador_service.obter_por_id(player.id) is not None
    
    auth_service.deletar_usuario(user['id'])
    
    assert auth_service.obter_por_id(user['id']) is None
    assert jogador_service.obter_por_id(player.id) is None
    
    user2 = auth_service.criar_usuario(
        email='sync2@example.com',
        username='sync_user2',
        nome='Sync User 2',
        password='password123',
        role='usuario'
    )
    player2 = jogador_service.criar(
        nome='Sync User 2',
        nivel=5.5,
        tipo='avulso',
        posicao='linha',
        owner_user_id=user2['id']
    )
    
    assert auth_service.obter_por_id(user2['id']) is not None
    assert jogador_service.obter_por_id(player2.id) is not None
    
    jogador_service.deletar(player2.id)
    
    assert auth_service.obter_por_id(user2['id']) is None
    assert jogador_service.obter_por_id(player2.id) is None


def test_user_player_link_and_cleanup_migration(tmp_path, monkeypatch):
    from services.db import clear_db_cache
    clear_db_cache()
    users_file = str(tmp_path / 'users.json')
    players_file = str(tmp_path / 'jogadores.json')
    
    import services.auth_service
    import services.jogador_service
    import services.db
    import json
    
    monkeypatch.setattr(services.auth_service.AuthService, '__init__', lambda self, arquivo=users_file: setattr(self, 'arquivo', arquivo) or self._garantir_arquivo())
    monkeypatch.setattr(services.jogador_service.JogadorService, '__init__', lambda self, arquivo=players_file: setattr(self, 'arquivo', arquivo) or setattr(self, 'namespace', 'jogadores') or self._garantir_arquivo())
    
    def fake_load_json_data(namespace, default):
        if namespace == "users":
            try:
                with open(users_file, "r") as f:
                    return json.load(f)
            except:
                return []
        elif namespace == "jogadores":
            try:
                with open(players_file, "r") as f:
                    return json.load(f)
            except:
                return []
        elif namespace == "migration_user_player_link_done":
            return None
        return default
        
    def fake_save_json_data(namespace, payload):
        if namespace == "users":
            with open(users_file, "w") as f:
                json.dump(payload, f)
        elif namespace == "jogadores":
            with open(players_file, "w") as f:
                json.dump(payload, f)

    for module in [services.db, services.jogador_service, services.auth_service]:
        monkeypatch.setattr(module, 'load_json_data', fake_load_json_data)
        monkeypatch.setattr(module, 'save_json_data', fake_save_json_data)
    
    auth_service = services.auth_service.AuthService()
    jogador_service = services.jogador_service.JogadorService()
    
    user_match = auth_service.criar_usuario(email='m1@ex.com', username='match1', nome='Match One', password='password123', role='usuario')
    player_match = jogador_service.criar(nome='Match One', nivel=7.0, tipo='avulso', posicao='linha')
    
    user_unmatched = auth_service.criar_usuario(email='um@ex.com', username='unmatched', nome='Unmatched User', password='password123', role='usuario')
    player_unmatched = jogador_service.criar(nome='Unmatched Player', nivel=6.0, tipo='avulso', posicao='linha')
    
    admin_user = auth_service.criar_usuario(email='adm@ex.com', username='admin_user', nome='Admin User', password='password123', role='admin')
    
    services.db.executar_migracao_link_usuarios_jogadores()
    
    linked_players = jogador_service.listar()
    linked_users = auth_service.listar_usuarios()
    
    p_match = next((p for p in linked_players if p.nome == 'Match One'), None)
    assert p_match is not None
    assert p_match.owner_user_id == user_match['id']
    
    assert not any(p.nome == 'Unmatched Player' for p in linked_players)
    assert not any(u['username'] == 'unmatched' for u in linked_users)
    assert any(u['username'] == 'admin_user' for u in linked_users)



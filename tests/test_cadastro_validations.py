from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import routes.auth_routes as auth_routes
from app import criar_app
from services.auth_service import AuthService


class FakeJogadorService:
    def __init__(self):
        self.criados = []

    def criar(self, **kwargs):
        self.criados.append(kwargs)
        return {'id': 'jogador-1', **kwargs}


class FakeEmailService:
    def __init__(self):
        self.enviados = []

    def send_welcome_email(self, **kwargs):
        self.enviados.append(kwargs)


class FakeNotificacaoService:
    def __init__(self):
        self.notificacoes = []

    def criar_notificacao(self, **kwargs):
        self.notificacoes.append(kwargs)


def _signup_payload(**overrides):
    payload = {
        'email': 'novo@example.com',
        'nome': 'Novo Jogador',
        'username': 'novojogador',
        'password': 'senha123',
        'confirmar_password': 'senha123',
        'nivel': '5',
        'tipo': 'avulso',
        'posicao': 'linha',
    }
    payload.update(overrides)
    return payload


def _signup_app(tmp_path, monkeypatch):
    app = criar_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    auth_service = AuthService(arquivo=str(tmp_path / 'users.json'))
    jogador_service = FakeJogadorService()
    email_service = FakeEmailService()
    notificacao_service = FakeNotificacaoService()

    monkeypatch.setattr(auth_routes, 'auth_service', auth_service)
    monkeypatch.setattr(auth_routes, 'jogador_service', jogador_service)
    monkeypatch.setattr(auth_routes, 'email_service', email_service)
    monkeypatch.setattr(auth_routes, 'notificacao_service', notificacao_service)

    return app, auth_service, jogador_service, email_service, notificacao_service


def test_auth_service_rejects_duplicate_email(tmp_path):
    service = AuthService(arquivo=str(tmp_path / 'users.json'))
    service.criar_usuario(email='dupe@example.com', username='primeiro', nome='Primeiro', password='senha123')

    with pytest.raises(ValueError, match='Email ja existe'):
        service.criar_usuario(email='DUPE@example.com', username='segundo', nome='Segundo', password='senha123')


def test_auth_service_rejects_duplicate_username(tmp_path):
    service = AuthService(arquivo=str(tmp_path / 'users.json'))
    service.criar_usuario(email='um@example.com', username='mesmo', nome='Primeiro', password='senha123')

    with pytest.raises(ValueError, match='Username ja existe'):
        service.criar_usuario(email='dois@example.com', username='MESMO', nome='Segundo', password='senha123')


def test_auth_service_rejects_weak_password(tmp_path):
    service = AuthService(arquivo=str(tmp_path / 'users.json'))

    with pytest.raises(ValueError, match='Senha deve ter ao menos 6 caracteres'):
        service.criar_usuario(email='fraca@example.com', username='fraca', nome='Senha Fraca', password='123')


@pytest.mark.parametrize(
    ('field', 'value', 'expected'),
    [
        ('email', 'email-invalido', 'Informe um email valido'),
        ('username', 'ab', 'Username deve ter ao menos 3 caracteres'),
        ('nome', 'A', 'Nome deve ter ao menos 2 caracteres'),
        ('password', '123', 'Senha deve ter ao menos 6 caracteres'),
        ('confirmar_password', 'outra123', 'A confirmacao de senha nao confere'),
    ],
)
def test_cadastro_route_rejects_invalid_payloads(tmp_path, monkeypatch, field, value, expected):
    app, *_ = _signup_app(tmp_path, monkeypatch)
    payload = _signup_payload(**{field: value})
    if field == 'password':
        payload['confirmar_password'] = value

    with app.test_client() as client:
        response = client.post('/cadastro', data=payload)

    body = response.get_data(as_text=True)
    assert response.status_code == 400
    assert expected in body


def test_cadastro_route_rejects_repeated_email(tmp_path, monkeypatch):
    app, auth_service, *_ = _signup_app(tmp_path, monkeypatch)
    auth_service.criar_usuario(email='novo@example.com', username='existente', nome='Existente', password='senha123')

    with app.test_client() as client:
        response = client.post('/cadastro', data=_signup_payload(username='outro'))

    body = response.get_data(as_text=True)
    assert response.status_code == 400
    assert 'Este e-mail já está em uso.' in body


def test_cadastro_route_rejects_repeated_username(tmp_path, monkeypatch):
    app, auth_service, *_ = _signup_app(tmp_path, monkeypatch)
    auth_service.criar_usuario(email='existente@example.com', username='novojogador', nome='Existente', password='senha123')

    with app.test_client() as client:
        response = client.post('/cadastro', data=_signup_payload(email='outro@example.com'))

    body = response.get_data(as_text=True)
    assert response.status_code == 400
    assert 'Este nome de usuário já está em uso.' in body


def test_cadastro_route_success_creates_user_player_email_and_notification(tmp_path, monkeypatch):
    app, auth_service, jogador_service, email_service, notificacao_service = _signup_app(tmp_path, monkeypatch)

    with app.test_client() as client:
        response = client.post('/cadastro', data=_signup_payload())

    body = response.get_data(as_text=True)
    usuario = auth_service.obter_por_username('novojogador')

    assert response.status_code == 200
    assert 'Cadastro realizado com sucesso' in body
    assert usuario['email'] == 'novo@example.com'
    assert jogador_service.criados[0]['owner_user_id'] == usuario['id']
    assert jogador_service.criados[0]['tipo'] == 'avulso'
    assert jogador_service.criados[0]['posicao'] == 'linha'
    assert email_service.enviados[0]['to_email'] == 'novo@example.com'
    assert notificacao_service.notificacoes[0]['tipo'] == 'cadastro'


def test_prevent_duplicate_user_and_player_names(tmp_path):
    from services.jogador_service import JogadorService
    auth_service = AuthService(arquivo=str(tmp_path / "users.json"))
    jog_service = JogadorService(arquivo=str(tmp_path / "jogadores.json"))

    auth_service.criar_usuario(email="u1@example.com", username="user1", nome="Carlos Silva", password="password123")
    with pytest.raises(ValueError, match="Ja existe um usuario cadastrado com este nome"):
        auth_service.criar_usuario(email="u2@example.com", username="user2", nome="carlos silva", password="password123")

    import uuid
    p_name = f"Jogador Dup {uuid.uuid4().hex[:6]}"
    jog_service.criar(nome=p_name, nivel=7.0, tipo="avulso", posicao="linha")
    with pytest.raises(ValueError, match="Já existe um jogador cadastrado com o nome"):
        jog_service.criar(nome=p_name.lower(), nivel=8.0, tipo="fixo", posicao="goleiro")


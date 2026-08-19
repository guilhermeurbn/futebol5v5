import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.auth_service import AuthService
from services.email_service import EmailService


class FakeResponse:
    status_code = 200
    text = '{"id": "email_123"}'

    def raise_for_status(self):
        return None

    def json(self):
        return {'id': 'email_123'}


def test_auth_service_email_and_reset_token_roundtrip(tmp_path):
    users_file = tmp_path / 'users.json'
    service = AuthService(arquivo=str(users_file))

    usuario = service.criar_usuario(
        email='joao@example.com',
        username='joao',
        nome='Joao',
        password='senha123',
    )

    assert usuario['email'] == 'joao@example.com'

    token = service.gerar_token_reset(usuario['id'])
    assert service.validar_token_reset(token)['id'] == usuario['id']

    service.definir_nova_senha(usuario['id'], 'novaSenha123')
    assert service.validar_token_reset(token) is None
    assert service.autenticar('joao', 'novaSenha123')['email'] == 'joao@example.com'


def test_email_service_send_welcome_email(monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY', 're_test_key')
    monkeypatch.setenv('RESEND_FROM_EMAIL', 'NaTrave <no-reply@natrave.pt>')

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=0):
        captured['url'] = url
        captured['headers'] = headers or {}
        captured['body'] = json or {}
        captured['timeout'] = timeout
        return FakeResponse()

    monkeypatch.setattr('services.email_service.requests.post', fake_post)

    service = EmailService()
    result = service.send_welcome_email('user@example.com', 'User', 'user123')

    assert result.ok is True
    assert result.message_id == 'email_123'
    assert captured['url'] == 'https://api.resend.com/emails'
    assert captured['body']['to'] == ['user@example.com']
    assert 'Authorization' in captured['headers']
    assert captured['timeout'] == 15


def test_email_service_send_temporary_password_email_layout(monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY', 're_test_key')
    monkeypatch.setenv('RESEND_FROM_EMAIL', 'NaTrave <no-reply@natrave.pt>')

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=0):
        captured['body'] = json or {}
        return FakeResponse()

    monkeypatch.setattr('services.email_service.requests.post', fake_post)

    service = EmailService()
    result = service.send_temporary_password_email(
        to_email='alex@example.com',
        nome='Alex Silva',
        username='alex',
        senha_temporaria='TEMP-9982'
    )

    assert result.ok is True
    html = captured['body']['html']

    # 1. Container 600px e Dark theme
    assert 'max-width: 600px' in html
    assert '#09090b' in html
    assert '#121217' in html
    assert '#10b981' in html

    # 2. Card de senha temporária em monospace
    assert 'TEMP-9982' in html
    assert 'font-family: \'SFMono-Regular\', Consolas' in html or 'monospace' in html

    # 3. Seção com 3 passos
    assert '3 passos para utilizar sua senha' in html
    assert 'Acesse a plataforma' in html
    assert 'Faça login com a senha temporária' in html
    assert 'Cadastre uma nova senha definitiva' in html

    # 4. Aviso de segurança
    assert 'Aviso de Segurança' in html
    assert 'esta senha temporária é de uso provisório' in html

    # 5. Botão CTA
    assert 'Acessar NaTrave' in html

    # 6. Rodapé profissional
    assert 'NaTrave 5v5 &bull; Gestão Inteligente de Futebol' in html or 'NaTrave 5v5' in html
    assert 'alex@example.com' in html


def test_completar_email_obrigatorio_flow():
    from app import criar_app
    app = criar_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    from services.auth_service import AuthService
    auth_svc = AuthService()

    import uuid
    uname = f"sememailuser_{uuid.uuid4().hex[:6]}"

    usuario = auth_svc.criar_usuario(
        email="",
        username=uname,
        nome=f"Sem Email {uname}",
        password="password123",
        role="usuario"
    )

    dados = auth_svc._carregar()
    for u in dados:
        if u.get("id") == usuario["id"]:
            u["email"] = ""
    auth_svc._salvar(dados)

    resp_login = client.post('/login', data={'username': uname, 'password': 'password123'}, follow_redirects=False)
    assert resp_login.status_code == 302
    assert '/completar-email' in resp_login.headers['Location']

    with client.session_transaction() as sess:
        sess['user_id'] = usuario['id']
        sess['pending_email_user_id'] = usuario['id']
        sess['username'] = uname
        sess['nome'] = 'Sem Email Teste'
        sess['role'] = 'usuario'

    resp_perfil = client.get('/perfil', follow_redirects=False)
    assert resp_perfil.status_code == 302
    assert '/completar-email' in resp_perfil.headers['Location']

    res_email = f"sememail.resolvido.{uuid.uuid4().hex[:6]}@exemplo.com"
    resp_submit = client.post('/completar-email', data={'email': res_email}, follow_redirects=True)
    assert resp_submit.status_code == 200

    u_atualizado = auth_svc.obter_por_id(usuario['id'])
    assert u_atualizado['email'] == res_email

    # Cleanup
    auth_svc.deletar_usuario(usuario['id'])


def test_privacidade_public_access():
    from app import criar_app
    app = criar_app()
    app.config['TESTING'] = True
    client = app.test_client()

    response = client.get('/privacidade')
    assert response.status_code == 200
    assert 'Política de Privacidade' in response.data.decode('utf-8')




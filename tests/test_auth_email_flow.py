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
    monkeypatch.setenv('RESEND_FROM_EMAIL', 'NaTrave <no-reply@natrave.com>')

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

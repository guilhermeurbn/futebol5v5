"""
Security Battery Tests - SQL Injection, XSS, and Input Hardening on Auth Endpoints
"""
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import criar_app
from routes import auth_routes
from services.auth_service import AuthService


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Create test Flask app with isolated DB"""
    app = criar_app('testing')

    auth_svc = AuthService(arquivo=str(tmp_path / 'users.json'))
    # Create legitimate test user
    auth_svc.criar_usuario(
        email='victor@example.com',
        username='victor_real',
        nome='Victor Santos',
        password='Password123!',
        role='usuario'
    )

    monkeypatch.setattr(auth_routes, 'auth_service', auth_svc)
    monkeypatch.setattr(auth_routes, 'jogador_service', Mock())
    monkeypatch.setattr(auth_routes, 'email_service', Mock())
    monkeypatch.setattr(auth_routes, 'notificacao_service', Mock())

    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestSQLInjectionLoginProtection:
    """Test SQL injection payloads on /login endpoint"""

    @pytest.mark.parametrize('sqli_payload', [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "admin'--",
        "admin' #",
        "' OR 1=1 --",
        "'; DROP TABLE users; --",
        "1' UNION SELECT NULL, NULL, NULL--",
        "admin' AND 1=0 UNION ALL SELECT 'admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918'--",
        "' OR pg_sleep(5)--"
    ])
    def test_login_rejects_sql_injection_username(self, client, sqli_payload):
        """Verify SQL injection payloads in username fail safely without auth bypass or server error"""
        response = client.post('/login', data={
            'username': sqli_payload,
            'password': 'password123'
        })
        # Must return status 401 or 400 (not 500 server crash, nor 302 login success)
        assert response.status_code in [401, 400]
        body = response.get_data(as_text=True)
        assert 'invalid' in body.lower() or 'erro' in body.lower() or 'não confere' in body.lower() or '401' in body or '400' in body

    @pytest.mark.parametrize('sqli_payload', [
        "' OR '1'='1",
        "password' OR 'a'='a",
        "'; DELETE FROM users WHERE 1=1; --"
    ])
    def test_login_rejects_sql_injection_password(self, client, sqli_payload):
        """Verify SQL injection payloads in password fail safely"""
        response = client.post('/login', data={
            'username': 'victor_real',
            'password': sqli_payload
        })
        assert response.status_code in [401, 400]


class TestSQLInjectionCadastroProtection:
    """Test SQL injection payloads on /cadastro endpoint"""

    @pytest.mark.parametrize('sqli_payload', [
        "User'; DROP TABLE users; --",
        "User' OR '1'='1",
        "User<script>alert(1)</script>"
    ])
    def test_cadastro_handles_malicious_name_safely(self, client, sqli_payload):
        """Verify malicious injection in name does not bypass validation or crash server"""
        response = client.post('/cadastro', data={
            'nome': sqli_payload,
            'email': 'valid_test@example.com',
            'username': 'unique_user_99',
            'password': 'Password123!',
            'confirmar_password': 'Password123!'
        })
        # Should either reject with 400 or succeed with sanitized data (no 500 error)
        assert response.status_code in [200, 302, 400]

    @pytest.mark.parametrize('sqli_username', [
        "user'; DROP TABLE users; --",
        "admin' OR 1=1 --",
        "user@name' UNION SELECT 1--"
    ])
    def test_cadastro_rejects_invalid_username_characters(self, client, sqli_username):
        """Verify usernames containing SQL control chars are rejected by regex check"""
        response = client.get(f'/checar-username?username={sqli_username}')
        assert response.status_code == 400
        data = response.get_json()
        assert data['available'] is False


class TestInputSanitizationAndBoundaries:
    """Test boundary conditions, oversized inputs, and control characters"""

    def test_oversized_login_username_rejected(self, client):
        """Verify extremely long username payload (5000 chars) is handled safely"""
        huge_username = "a" * 5000
        response = client.post('/login', data={
            'username': huge_username,
            'password': 'somepassword'
        })
        assert response.status_code in [401, 400]

    def test_null_byte_injection_handled_safely(self, client):
        """Verify null byte injection (\x00) does not cause unexpected errors"""
        response = client.post('/login', data={
            'username': 'admin\x00user',
            'password': 'password123'
        })
        assert response.status_code in [401, 400]

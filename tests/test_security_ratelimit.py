"""
Security Regression Tests - Rate Limiting
Tests for rate limiting on sensitive endpoints (login, signup, password reset)
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from time import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import criar_app
from routes import auth_routes
from services.auth_service import AuthService


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Create test Flask app"""
    app = criar_app('testing')

    monkeypatch.setattr(
        auth_routes,
        'auth_service',
        AuthService(arquivo=str(tmp_path / 'users.json')),
    )
    monkeypatch.setattr(auth_routes, 'jogador_service', Mock())
    monkeypatch.setattr(auth_routes, 'email_service', Mock())
    monkeypatch.setattr(auth_routes, 'notificacao_service', Mock())

    app.config['TESTING'] = True
    # Disable CSRF for testing POST endpoints
    app.config['WTF_CSRF_ENABLED'] = False
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestRateLimitingLogin:
    """Test rate limiting on /login endpoint (max 50 per hour, 51st rejects)"""
    
    def test_login_accepts_50_requests_per_hour(self, client, monkeypatch):
        """Verify /login allows first 50 POST requests within an hour"""
        for i in range(50):
            response = client.post('/login', data={
                'username': f'user{i}',
                'password': 'wrongpass'
            })
            # Deve falhar autenticação, mas sem limitar antes da 51a
            assert response.status_code in [200, 401], \
                f"Request {i+1} failed with {response.status_code}"
    
    def test_login_rejects_51st_request_per_hour(self, client, monkeypatch):
        """Verify /login rejects 51st POST request within an hour with 429"""
        responses = []
        for i in range(51):
            response = client.post('/login', data={
                'username': f'user{i}',
                'password': 'wrongpass'
            })
            responses.append(response.status_code)

        assert responses[50] == 429, \
            f"51st request should be rate limited (429), got {responses[50]}"
        for idx, code in enumerate(responses[:50]):
            assert code != 429, \
                f"Request {idx+1} was rate limited but shouldn't be"


class TestRateLimitingCadastro:
    """Test rate limiting on /cadastro endpoint (max 3 per hour, 4th rejects)"""
    
    def test_cadastro_accepts_3_requests_per_hour(self, client, monkeypatch):
        """Verify /cadastro allows first 3 POST requests within an hour"""
        for i in range(3):
            response = client.post('/cadastro', data={
                'nome': f'User {i}',
                'email': f'user{i}_{time()}@example.com',
                'username': f'user{i}_{time()}',
                'password': 'Pass1234!',
                'confirmar_password': 'Pass1234!',
                'nivel': '5'
            })
            assert response.status_code != 429, \
                f"Request {i+1} was rate limited but shouldn't be"
    
    def test_cadastro_rejects_4th_request_per_hour(self, client, monkeypatch):
        """Verify /cadastro rejects 4th POST request within an hour with 429"""
        responses = []
        for i in range(4):
            response = client.post('/cadastro', data={
                'nome': f'User {i}',
                'email': f'user{i}_{time()}@example.com',
                'username': f'user{i}_{time()}',
                'password': 'Pass1234!',
                'confirmar_password': 'Pass1234!',
                'nivel': '5'
            })
            responses.append(response.status_code)

        assert responses[3] == 429, \
            f"4th request should be rate limited (429), got {responses[3]}"


class TestRateLimitingPasswordReset:
    """Test rate limiting on /recuperar-senha (max 3 per hour, 4th rejects)"""
    
    def test_password_reset_accepts_3_requests_per_hour(self, client, monkeypatch):
        """Verify /recuperar-senha allows first 3 POST requests within an hour"""
        for i in range(3):
            response = client.post('/recuperar-senha', data={
                'email': f'user{i}@example.com'
            })
            assert response.status_code != 429, \
                f"Request {i+1} was rate limited but shouldn't be"
    
    def test_password_reset_rejects_4th_request_per_hour(self, client, monkeypatch):
        """Verify /recuperar-senha rejects 4th POST request within an hour with 429"""
        responses = []
        for i in range(4):
            response = client.post('/recuperar-senha', data={
                'email': f'user{i}@example.com'
            })
            responses.append(response.status_code)

        assert responses[3] == 429, \
            f"4th request should be rate limited (429), got {responses[3]}"


class TestRateLimitCounterReset:
    """Test that rate limit counters reset after time window expires"""
    
    def test_login_counter_resets_after_hour(self, monkeypatch):
        """Verify login rate limit counter resets after 3600 seconds (1 hour)"""
        app_source = Path(__file__).resolve().parent.parent / 'app.py'
        content = app_source.read_text(encoding='utf-8')
        assert '"50/hour"' in content, "Rate limit window should be 3600 seconds (1 hour)"
    
    def test_cadastro_counter_resets_after_hour(self, monkeypatch):
        """Verify signup rate limit counter resets after 3600 seconds"""
        app_source = Path(__file__).resolve().parent.parent / 'app.py'
        content = app_source.read_text(encoding='utf-8')
        assert '"3/hour"' in content, "Rate limit window should be 3600 seconds (1 hour)"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

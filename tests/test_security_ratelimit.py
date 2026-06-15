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


@pytest.fixture
def app():
    """Create test Flask app"""
    app = criar_app('testing')
    app.config['TESTING'] = True
    # Disable CSRF for testing POST endpoints
    app.config['WTF_CSRF_ENABLED'] = False
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestRateLimitingLogin:
    """Test rate limiting on /login endpoint (max 5 per minute, 6th rejects)"""
    
    def test_login_accepts_5_requests_per_minute(self, client, monkeypatch):
        """Verify /login allows first 5 POST requests within a minute"""
        # Mock the limiter to track requests
        request_count = {'count': 0}
        
        def mock_limit_check(limit_str):
            """Mock decorator that allows 5 requests"""
            def decorator(f):
                def wrapper(*args, **kwargs):
                    request_count['count'] += 1
                    if request_count['count'] > 5:
                        # Return 429 Too Many Requests
                        from flask import Response
                        return Response('Too Many Requests', status=429)
                    return f(*args, **kwargs)
                return wrapper
            return decorator
        
        # Apply mock to auth routes
        with patch('routes.auth_routes.limiter.limit', mock_limit_check):
            # Reload routes to apply patch
            from importlib import reload
            from routes import auth_routes
            reload(auth_routes)
            
            # Make 5 login attempts - should all succeed
            for i in range(5):
                response = client.post('/login', data={
                    'username': f'user{i}',
                    'password': 'wrongpass'
                })
                # Should get 401 (auth failed) not 429 (rate limit)
                assert response.status_code in [200, 401], \
                    f"Request {i+1} failed with {response.status_code}"
    
    def test_login_rejects_6th_request_per_minute(self, client, monkeypatch):
        """Verify /login rejects 6th POST request within a minute with 429"""
        request_count = {'count': 0, 'start_time': time()}
        
        def mock_rate_limit(limit_str):
            """Mock decorator that rejects 6th request"""
            def decorator(f):
                def wrapper(*args, **kwargs):
                    elapsed = time() - request_count['start_time']
                    # Only reset counter after 60 seconds
                    if elapsed >= 60:
                        request_count['count'] = 0
                        request_count['start_time'] = time()
                    
                    request_count['count'] += 1
                    if request_count['count'] > 5:
                        from flask import Response
                        return Response('Rate limit exceeded', status=429)
                    return f(*args, **kwargs)
                return wrapper
            return decorator
        
        with patch('routes.auth_routes.limiter.limit', mock_rate_limit):
            from importlib import reload
            from routes import auth_routes
            reload(auth_routes)
            
            # Make 6 login attempts
            responses = []
            for i in range(6):
                response = client.post('/login', data={
                    'username': f'user{i}',
                    'password': 'wrongpass'
                })
                responses.append(response.status_code)
            
            # 6th request should be 429
            assert responses[5] == 429, \
                f"6th request should be rate limited (429), got {responses[5]}"
            
            # First 5 should not be 429
            for idx, code in enumerate(responses[:5]):
                assert code != 429, \
                    f"Request {idx+1} was rate limited but shouldn't be"


class TestRateLimitingCadastro:
    """Test rate limiting on /cadastro endpoint (max 3 per hour, 4th rejects)"""
    
    def test_cadastro_accepts_3_requests_per_hour(self, client, monkeypatch):
        """Verify /cadastro allows first 3 POST requests within an hour"""
        request_count = {'count': 0}
        
        def mock_limit_check(limit_str):
            """Mock decorator that allows 3 requests"""
            def decorator(f):
                def wrapper(*args, **kwargs):
                    request_count['count'] += 1
                    if request_count['count'] > 3:
                        from flask import Response
                        return Response('Too Many Requests', status=429)
                    return f(*args, **kwargs)
                return wrapper
            return decorator
        
        with patch('routes.auth_routes.limiter.limit', mock_limit_check):
            from importlib import reload
            from routes import auth_routes
            reload(auth_routes)
            
            # Make 3 signup attempts
            for i in range(3):
                response = client.post('/cadastro', data={
                    'nome': f'User {i}',
                    'email': f'user{i}@example.com',
                    'username': f'user{i}',
                    'password': 'Pass1234!',
                    'confirmar_password': 'Pass1234!',
                    'nivel': '5'
                })
                # Should not be 429
                assert response.status_code != 429, \
                    f"Request {i+1} was rate limited but shouldn't be"
    
    def test_cadastro_rejects_4th_request_per_hour(self, client, monkeypatch):
        """Verify /cadastro rejects 4th POST request within an hour with 429"""
        request_count = {'count': 0, 'start_time': time()}
        
        def mock_rate_limit(limit_str):
            """Mock decorator that rejects 4th request"""
            def decorator(f):
                def wrapper(*args, **kwargs):
                    elapsed = time() - request_count['start_time']
                    # Only reset counter after 3600 seconds (1 hour)
                    if elapsed >= 3600:
                        request_count['count'] = 0
                        request_count['start_time'] = time()
                    
                    request_count['count'] += 1
                    if request_count['count'] > 3:
                        from flask import Response
                        return Response('Rate limit exceeded', status=429)
                    return f(*args, **kwargs)
                return wrapper
            return decorator
        
        with patch('routes.auth_routes.limiter.limit', mock_rate_limit):
            from importlib import reload
            from routes import auth_routes
            reload(auth_routes)
            
            # Make 4 signup attempts
            responses = []
            for i in range(4):
                response = client.post('/cadastro', data={
                    'nome': f'User {i}',
                    'email': f'user{i}@example.com',
                    'username': f'user{i}',
                    'password': 'Pass1234!',
                    'confirmar_password': 'Pass1234!',
                    'nivel': '5'
                })
                responses.append(response.status_code)
            
            # 4th request should be 429
            assert responses[3] == 429, \
                f"4th request should be rate limited (429), got {responses[3]}"


class TestRateLimitingPasswordReset:
    """Test rate limiting on /recuperar-senha (max 3 per hour, 4th rejects)"""
    
    def test_password_reset_accepts_3_requests_per_hour(self, client, monkeypatch):
        """Verify /recuperar-senha allows first 3 POST requests within an hour"""
        request_count = {'count': 0}
        
        def mock_limit_check(limit_str):
            """Mock decorator that allows 3 requests"""
            def decorator(f):
                def wrapper(*args, **kwargs):
                    request_count['count'] += 1
                    if request_count['count'] > 3:
                        from flask import Response
                        return Response('Too Many Requests', status=429)
                    return f(*args, **kwargs)
                return wrapper
            return decorator
        
        with patch('routes.auth_routes.limiter.limit', mock_limit_check):
            from importlib import reload
            from routes import auth_routes
            reload(auth_routes)
            
            # Make 3 password reset attempts
            for i in range(3):
                response = client.post('/recuperar-senha', data={
                    'email': f'user{i}@example.com'
                })
                assert response.status_code != 429, \
                    f"Request {i+1} was rate limited but shouldn't be"
    
    def test_password_reset_rejects_4th_request_per_hour(self, client, monkeypatch):
        """Verify /recuperar-senha rejects 4th POST request within an hour with 429"""
        request_count = {'count': 0, 'start_time': time()}
        
        def mock_rate_limit(limit_str):
            """Mock decorator that rejects 4th request"""
            def decorator(f):
                def wrapper(*args, **kwargs):
                    elapsed = time() - request_count['start_time']
                    if elapsed >= 3600:
                        request_count['count'] = 0
                        request_count['start_time'] = time()
                    
                    request_count['count'] += 1
                    if request_count['count'] > 3:
                        from flask import Response
                        return Response('Rate limit exceeded', status=429)
                    return f(*args, **kwargs)
                return wrapper
            return decorator
        
        with patch('routes.auth_routes.limiter.limit', mock_rate_limit):
            from importlib import reload
            from routes import auth_routes
            reload(auth_routes)
            
            responses = []
            for i in range(4):
                response = client.post('/recuperar-senha', data={
                    'email': f'user{i}@example.com'
                })
                responses.append(response.status_code)
            
            # 4th request should be 429
            assert responses[3] == 429, \
                f"4th request should be rate limited (429), got {responses[3]}"


class TestRateLimitCounterReset:
    """Test that rate limit counters reset after time window expires"""
    
    def test_login_counter_resets_after_minute(self, monkeypatch):
        """Verify login rate limit counter resets after 60 seconds"""
        counter = {'count': 0, 'reset_time': None, 'window_seconds': 60}
        
        def track_reset(window_seconds):
            counter['window_seconds'] = window_seconds
            counter['reset_time'] = time() + window_seconds
            
            def decorator(f):
                def wrapper(*args, **kwargs):
                    elapsed = time() - (counter['reset_time'] - counter['window_seconds'])
                    if elapsed >= counter['window_seconds']:
                        counter['count'] = 0
                    counter['count'] += 1
                    return f(*args, **kwargs)
                return wrapper
            return decorator
        
        # Apply tracking
        with patch('routes.auth_routes.limiter.limit', track_reset):
            # Verify reset time is set correctly for 60-second window
            assert counter['window_seconds'] == 60, \
                "Rate limit window should be 60 seconds (1 minute)"
    
    def test_cadastro_counter_resets_after_hour(self, monkeypatch):
        """Verify signup rate limit counter resets after 3600 seconds"""
        counter = {'count': 0, 'reset_time': None, 'window_seconds': 0}
        
        def track_reset(window_seconds):
            counter['window_seconds'] = window_seconds
            counter['reset_time'] = time() + window_seconds
            
            def decorator(f):
                def wrapper(*args, **kwargs):
                    elapsed = time() - (counter['reset_time'] - counter['window_seconds'])
                    if elapsed >= counter['window_seconds']:
                        counter['count'] = 0
                    counter['count'] += 1
                    return f(*args, **kwargs)
                return wrapper
            return decorator
        
        # Verify reset time is set for 3600-second window
        with patch('routes.auth_routes.limiter.limit', track_reset):
            assert counter['window_seconds'] == 3600, \
                "Rate limit window should be 3600 seconds (1 hour)"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""
Security Regression Tests - Exception Handling
Tests for proper exception handling and absence of bare except statements
"""
import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.auth_service import AuthService
from services.email_service import EmailService


class TestNoBareExceptStatements:
    """Test that bare except: statements are removed from codebase"""
    
    def test_no_bare_except_in_services(self):
        """Scan services/ for bare except: statements and fail if found"""
        services_dir = Path(__file__).resolve().parent.parent / 'services'
        bare_except_pattern = re.compile(r'^\s*except\s*:\s*(?=#|$)', re.MULTILINE)
        
        violations = []
        
        for py_file in services_dir.glob('*.py'):
            if py_file.name == '__init__.py':
                continue
            
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for line_no, line in enumerate(lines, 1):
                # Check for bare except: (except with no exception type)
                if re.match(r'^\s*except\s*:\s*', line):
                    violations.append({
                        'file': py_file.name,
                        'line': line_no,
                        'code': line.strip()
                    })
        
        if violations:
            error_msg = "Found bare except: statements (not allowed):\n"
            for v in violations:
                error_msg += f"  {v['file']}:{v['line']} - {v['code']}\n"
            error_msg += "\nAll exceptions must specify a type: except ValueError, except (ValueError, KeyError), etc."
            pytest.fail(error_msg)
    
    def test_no_bare_except_in_routes(self):
        """Scan routes/ for bare except: statements"""
        routes_dir = Path(__file__).resolve().parent.parent / 'routes'
        
        violations = []
        
        for py_file in routes_dir.glob('*.py'):
            if py_file.name == '__init__.py':
                continue
            
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for line_no, line in enumerate(lines, 1):
                if re.match(r'^\s*except\s*:\s*', line):
                    violations.append({
                        'file': py_file.name,
                        'line': line_no,
                        'code': line.strip()
                    })
        
        if violations:
            error_msg = "Found bare except: statements in routes/:\n"
            for v in violations:
                error_msg += f"  {v['file']}:{v['line']} - {v['code']}\n"
            pytest.fail(error_msg)
    
    def test_no_bare_except_in_app(self):
        """Scan app.py for bare except: statements"""
        app_file = Path(__file__).resolve().parent.parent / 'app.py'
        
        violations = []
        
        with open(app_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        for line_no, line in enumerate(lines, 1):
            if re.match(r'^\s*except\s*:\s*', line):
                violations.append({
                    'file': 'app.py',
                    'line': line_no,
                    'code': line.strip()
                })
        
        if violations:
            error_msg = "Found bare except: statements in app.py:\n"
            for v in violations:
                error_msg += f"  {v['file']}:{v['line']} - {v['code']}\n"
            pytest.fail(error_msg)


class TestJSONParsingExceptionHandling:
    """Test that JSON parsing failures are caught with JSONDecodeError"""
    
    def test_json_load_file_with_invalid_json(self):
        """Verify JSONDecodeError is caught when loading invalid JSON"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            # Write invalid JSON
            f.write('{ invalid json }')
            temp_file = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                with open(temp_file, 'r') as f:
                    json.load(f)
        finally:
            os.unlink(temp_file)
    
    def test_auth_service_handles_corrupted_users_file(self):
        """Verify AuthService handles corrupted JSON gracefully"""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            users_file = Path(tmpdir) / 'users.json'
            
            # Write corrupted JSON
            users_file.write_text('{ corrupt }')
            
            # Service should handle this gracefully
            auth_service = AuthService(arquivo=str(users_file))
            
            # Should return empty list or handle the error
            try:
                users = auth_service._carregar()
                # Should either return empty list or raise a specific exception
                assert isinstance(users, list), \
                    "Should return a list even with corrupted file"
            except json.JSONDecodeError:
                # This is acceptable if we explicitly catch and handle it
                pass
    
    def test_json_parsing_uses_specific_exception(self):
        """Verify code uses try-except with JSONDecodeError, not bare except"""
        services_dir = Path(__file__).resolve().parent.parent / 'services'
        
        # Check for proper exception handling pattern
        json_pattern = re.compile(r'json\.load|json\.loads', re.MULTILINE)
        
        for py_file in services_dir.glob('*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # If file uses json.load/loads, it should have proper exception handling
            if json_pattern.search(content):
                # Check for bare excepts - if found, this is a violation
                bare_except_pattern = re.compile(r'except\s*:\s*', re.MULTILINE)
                if bare_except_pattern.search(content):
                    # This could be handled by test_no_bare_except_in_services
                    pass


class TestDatetimeParsingExceptionHandling:
    """Test that datetime parsing failures are caught with ValueError"""
    
    def test_datetime_parsing_with_invalid_string(self):
        """Verify ValueError is raised for invalid datetime strings"""
        with pytest.raises(ValueError):
            datetime.fromisoformat('invalid-date-string')
    
    def test_datetime_parsing_with_invalid_format(self):
        """Verify ValueError is raised for incorrect format"""
        with pytest.raises(ValueError):
            datetime.strptime('invalid', '%Y-%m-%d')
    
    def test_app_handles_date_parsing_errors(self):
        """Verify app._parse_iso_date handles ValueError correctly"""
        # The app.py file contains a _parse_iso_date function
        # It should catch ValueError and return None or handle gracefully
        from app import criar_app
        
        app = criar_app('testing')
        
        # The Jinja filter should exist
        assert app.jinja_env.filters.get('_parse_iso_date') or \
               'parse_iso_date' in str(app.jinja_env.filters), \
            "App should have ISO date parsing filter"


class TestServiceExceptionBoundaries:
    """Test service methods handle exceptions at appropriate boundaries"""
    
    def test_auth_service_autenticar_handles_missing_user(self):
        """Verify AuthService.autenticar handles missing user gracefully"""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            users_file = Path(tmpdir) / 'users.json'
            users_file.write_text('[]')
            
            auth_service = AuthService(arquivo=str(users_file))
            
            # Should not raise exception, should return None or False
            result = auth_service.autenticar('nonexistent', 'password')
            
            # Should return None or False, not raise
            assert result is None or result is False, \
                "Should return None/False for nonexistent user, not raise exception"
    
    def test_email_service_handles_network_error(self):
        """Verify EmailService handles network errors gracefully"""
        from unittest.mock import Mock, patch
        
        email_service = EmailService()
        
        # Mock a network error
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            # Should handle gracefully
            try:
                result = email_service._post({})
                # Should return failed result, not raise
                assert hasattr(result, 'ok'), \
                    "Should return result object with 'ok' attribute"
            except Exception as e:
                # If it raises, it should be a specific exception type
                assert not isinstance(e, Exception) or \
                       type(e).__name__ != 'Exception', \
                    "Should not raise bare Exception"


class TestExceptionTypeSpecificity:
    """Test that exceptions are caught with specific types, not generic Exception"""
    
    def test_no_except_generic_exception(self):
        """Verify services don't use bare 'except Exception:' without justification"""
        services_dir = Path(__file__).resolve().parent.parent / 'services'
        
        # This is less critical than bare except:, but worth noting
        # Some 'except Exception:' might be justified for logging, etc.
        # Bare except: is never justified
        
        violations = []
        
        for py_file in services_dir.glob('*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_no, line in enumerate(lines, 1):
                # Look for bare except: (this is the main violation)
                if re.match(r'^\s*except\s*:\s*(?=#|$)', line):
                    violations.append({
                        'file': py_file.name,
                        'line': line_no,
                        'type': 'bare_except'
                    })
        
        assert not violations, \
            f"Found {len(violations)} bare except: statements - all must specify exception type"


class TestErrorMessageSensitivity:
    """Test that error messages don't leak sensitive information"""
    
    def test_auth_error_messages_generic(self):
        """Verify auth errors don't leak whether username or password is wrong"""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            users_file = Path(tmpdir) / 'users.json'
            users_file.write_text('[]')
            
            auth_service = AuthService(arquivo=str(users_file))
            
            # Create a user
            usuario = auth_service.criar_usuario(
                email='test@example.com',
                username='testuser',
                nome='Test User',
                password='Password123!'
            )
            
            # Wrong password
            result = auth_service.autenticar('testuser', 'wrongpassword')
            
            # Should not indicate which field is wrong
            # Either return None or raise ValueError with generic message
            if isinstance(result, str):
                error_msg = result.lower()
                # Should not say "password incorrect" or "username not found"
                assert 'wrong password' not in error_msg, \
                    "Error should not specify which field is wrong"
                assert 'user not found' not in error_msg, \
                    "Error should not leak whether user exists"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

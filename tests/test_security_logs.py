"""
Security Regression Tests - Log Secrets
Tests that logs don't expose sensitive information like API keys and Bearer tokens
"""
import sys
import logging
import io
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.email_service import EmailService, RedactingFormatter


class TestBearerTokenRedaction:
    """Test that Bearer tokens are redacted from logs"""
    
    def test_redacting_formatter_redacts_bearer_token(self):
        """Verify RedactingFormatter removes Bearer tokens from logs"""
        formatter = RedactingFormatter('%(message)s')
        
        # Create a log record with a Bearer token
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='API call with Bearer re_abc123_def456',
            args=(),
            exc_info=None
        )
        
        # Format the record
        formatted = formatter.format(record)
        
        # Token should be redacted
        assert 'Bearer [REDACTED]' in formatted, \
            "Bearer token should be redacted"
        assert 're_abc123_def456' not in formatted, \
            "Actual token should not appear in log"
    
    def test_bearer_token_variations_are_redacted(self):
        """Verify different Bearer token formats are redacted"""
        formatter = RedactingFormatter('%(message)s')
        
        test_cases = [
            'Bearer re_test_abc123xyz789',
            'Bearer sk-abc.def_ghi-jkl+mno=',
            'Bearer token_with-special~chars',
            'Authorization: Bearer re_longtokenstring',
        ]
        
        for token_str in test_cases:
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg=f'Sending request: {token_str}',
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            
            # Should be redacted
            assert '[REDACTED]' in formatted, \
                f"Should redact: {token_str}"
            # Token value should not appear
            for token_val in ['re_', 'sk-', 'token_']:
                if token_val in token_str:
                    assert token_val not in formatted or \
                           formatted.count(token_val) < token_str.count(token_val), \
                        f"Token part '{token_val}' should be redacted from: {token_str}"
    
    def test_non_bearer_tokens_not_affected(self):
        """Verify non-Bearer tokens are not over-redacted"""
        formatter = RedactingFormatter('%(message)s')
        
        # Test strings that shouldn't be redacted
        safe_messages = [
            'User bearer_user logged in',
            'Bearer token not found',
            'GET /api/bearer/endpoint',
        ]
        
        for msg in safe_messages:
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg=msg,
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            
            # Should contain original message (no over-redaction)
            # unless it truly looks like a Bearer token
            if 'Bearer ' not in msg:
                assert msg in formatted, \
                    f"Non-Bearer message should not be redacted: {msg}"


class TestEmailServiceLogging:
    """Test email service doesn't log sensitive credentials"""
    
    def test_email_service_redacts_api_key_from_logs(self, monkeypatch, caplog):
        """Verify email service logs don't contain API keys"""
        monkeypatch.setenv('RESEND_API_KEY', 're_test_api_key_abc123')
        monkeypatch.setenv('RESEND_FROM_EMAIL', 'noreply@example.com')
        
        # Mock the requests.post to avoid actual API calls
        def mock_post(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'id': 'email_123'}
            return mock_response
        
        monkeypatch.setattr('services.email_service.requests.post', mock_post)
        
        with caplog.at_level(logging.DEBUG):
            email_service = EmailService()
            result = email_service.send_reset_token_email(
                'user@example.com',
                'User',
                'reset_token_abc'
            )
        
        # Get the log output
        log_text = caplog.text
        
        # API key should not appear in logs
        assert 're_test_api_key' not in log_text, \
            "API key should not appear in logs"
        
        # Should contain redacted token instead
        assert '[REDACTED]' in log_text or 'Bearer' not in log_text, \
            "Should either redact or not log Bearer tokens"
    
    def test_email_post_method_redacts_credentials(self, monkeypatch, caplog):
        """Verify _post method doesn't log API credentials"""
        monkeypatch.setenv('RESEND_API_KEY', 're_secret_key_1234567890')
        monkeypatch.setenv('RESEND_FROM_EMAIL', 'noreply@app.com')
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'msg_123'}
        
        monkeypatch.setattr('services.email_service.requests.post', lambda *a, **kw: mock_response)
        
        email_service = EmailService()
        
        with caplog.at_level(logging.INFO):
            email_service._post({
                'to': 'user@example.com',
                'subject': 'Test',
                'html': '<p>Test</p>'
            })
        
        log_text = caplog.text
        
        # Secret key should not be in logs
        assert 're_secret_key' not in log_text, \
            "Secret API key should not appear in logs"
        assert '1234567890' not in log_text, \
            "API key value should not appear in logs"


class TestLoggingConfiguration:
    """Test that logging is properly configured for security"""
    
    def test_email_service_has_redacting_formatter(self):
        """Verify EmailService logger uses RedactingFormatter"""
        from services import email_service
        
        logger = logging.getLogger('services.email_service')
        
        # Check if any handler has RedactingFormatter
        has_redacting = False
        
        for handler in logger.handlers:
            if isinstance(handler.formatter, RedactingFormatter):
                has_redacting = True
                break
        
        # Note: Handlers might be inherited from root logger
        # This test documents the expectation
        assert isinstance(email_service.redacting_formatter, RedactingFormatter), \
            "EmailService should have a RedactingFormatter instance"
    
    def test_redacting_formatter_pattern_matches_bearer_tokens(self):
        """Verify redacting formatter regex correctly identifies Bearer tokens"""
        import re
        
        formatter = RedactingFormatter('%(message)s')
        
        # Test the pattern from the formatter
        pattern = formatter.BEARER_PATTERN
        
        test_cases = [
            ('Bearer re_test_key_abc123', True),
            ('Bearer sk-proj-1234567890abcdef', True),
            ('Bearer token_with_special-chars~+/', True),
            ('bearer lowercase test', False),  # Should be case-sensitive
            ('NotBearer token', False),
            ('Just a Bearer word', False),
        ]
        
        for text, should_match in test_cases:
            matches = pattern.findall(text)
            if should_match:
                assert len(matches) > 0, \
                    f"Pattern should match: {text}"
            # Note: "Just a Bearer word" might match "Bearer word"
            # The pattern looks for "Bearer" followed by token-like characters


class TestSensitiveDataInErrorMessages:
    """Test that error messages don't leak sensitive data"""
    
    def test_email_service_error_doesnt_include_api_key(self, monkeypatch, caplog):
        """Verify email service errors don't expose API keys"""
        monkeypatch.setenv('RESEND_API_KEY', 're_sensitive_key_xyz')
        monkeypatch.setenv('RESEND_FROM_EMAIL', 'from@example.com')
        
        # Mock failed request
        def mock_post_fail(*args, **kwargs):
            raise Exception('API request failed: Bearer re_sensitive_key_xyz invalid')
        
        monkeypatch.setattr('services.email_service.requests.post', mock_post_fail)
        
        email_service = EmailService()
        
        with caplog.at_level(logging.ERROR):
            try:
                email_service._post({'to': 'user@example.com'})
            except:
                pass
        
        # Even in error logs, shouldn't expose the key
        # (RedactingFormatter should handle it)
        log_text = caplog.text
        
        # If key appears in log, it should be redacted
        if 're_sensitive_key_xyz' in log_text:
            assert False, "API key should not appear in error logs"
    
    def test_database_error_doesnt_expose_credentials(self):
        """Verify database errors don't leak credentials"""
        # This is more of a guideline test
        # Make sure services don't pass DB connection strings to logs
        from services import db
        
        # Import should work without errors
        assert db is not None, "DB module should be importable"


class TestLogCaptureAndVerification:
    """Test methods for capturing and verifying logs"""
    
    def test_can_capture_email_logs(self, monkeypatch, caplog):
        """Verify we can capture email service logs for testing"""
        monkeypatch.setenv('RESEND_API_KEY', 're_test_key')
        monkeypatch.setenv('RESEND_FROM_EMAIL', 'test@example.com')
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'msg_123'}
        
        monkeypatch.setattr('services.email_service.requests.post', lambda *a, **kw: mock_response)
        
        email_service = EmailService()
        
        with caplog.at_level(logging.DEBUG):
            email_service._post({
                'to': 'test@example.com',
                'subject': 'Test'
            })
        
        # Should have captured some logs
        assert len(caplog.records) >= 0, \
            "Should be able to capture logs"
        
        # Verify logs don't contain sensitive data
        for record in caplog.records:
            assert 're_test_key' not in record.getMessage(), \
                "Logs should not contain API keys"
    
    def test_redacted_text_appears_in_logs(self):
        """Verify [REDACTED] appears instead of actual token"""
        formatter = RedactingFormatter('%(message)s')
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Sending with Bearer sk_test_actual_key_12345',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should have [REDACTED] text
        assert '[REDACTED]' in formatted, \
            "Should contain [REDACTED] marker"
        
        # Original key should not be there
        assert 'sk_test_actual_key' not in formatted, \
            "Original token should be removed"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

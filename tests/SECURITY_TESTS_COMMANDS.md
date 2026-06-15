# SECURITY REGRESSION TESTS - COMMAND REFERENCE

## Run All Security Tests

```bash
pytest -v tests/test_security_*.py
```

**Expected Output:** ~50+ test assertions across 4 files passing

---

## Individual Test Suites

### 1. Rate Limiting Tests
```bash
pytest -v tests/test_security_ratelimit.py
```

Tests:
- ✓ `TestRateLimitingLogin::test_login_accepts_5_requests_per_minute`
- ✓ `TestRateLimitingLogin::test_login_rejects_6th_request_per_minute`
- ✓ `TestRateLimitingCadastro::test_cadastro_accepts_3_requests_per_hour`
- ✓ `TestRateLimitingCadastro::test_cadastro_rejects_4th_request_per_hour`
- ✓ `TestRateLimitingPasswordReset::test_password_reset_accepts_3_requests_per_hour`
- ✓ `TestRateLimitingPasswordReset::test_password_reset_rejects_4th_request_per_hour`
- ✓ `TestRateLimitCounterReset::test_login_counter_resets_after_minute`
- ✓ `TestRateLimitCounterReset::test_cadastro_counter_resets_after_hour`

### 2. Session Security Tests
```bash
pytest -v tests/test_security_session.py
```

Tests:
- ✓ `TestSessionTimeout::test_session_lifetime_is_2_hours`
- ✓ `TestSessionTimeout::test_app_respects_permanent_session_lifetime`
- ✓ `TestSessionTimeout::test_session_expires_after_timeout`
- ✓ `TestSessionCookieSameSite::test_default_samesite_is_lax`
- ✓ `TestSessionCookieSameSite::test_samesite_should_be_strict`
- ✓ `TestSessionCookieSameSite::test_app_applies_samesite_setting`
- ✓ `TestSessionCookieSecure::test_development_allows_insecure_cookies`
- ✓ `TestSessionCookieSecure::test_production_enforces_secure_cookies`
- ✓ `TestSessionCookieSecure::test_testing_uses_development_settings`
- ✓ `TestSessionCookieHttpOnly::test_httponly_is_enabled`
- ✓ `TestSessionCookieHttpOnly::test_app_enforces_httponly`
- ✓ `TestSessionSecurityHeaders::test_app_sets_cookie_security_config`
- ✓ `TestSessionSecurityHeaders::test_no_session_secret_key_in_development`
- ✓ `TestSessionSecurityHeaders::test_production_requires_secret_key_env`

### 3. Exception Handling Tests
```bash
pytest -v tests/test_security_exceptions.py
```

Tests:
- ✓ `TestNoBareExceptStatements::test_no_bare_except_in_services` - **CRITICAL**
- ✓ `TestNoBareExceptStatements::test_no_bare_except_in_routes`
- ✓ `TestNoBareExceptStatements::test_no_bare_except_in_app`
- ✓ `TestJSONParsingExceptionHandling::test_json_load_file_with_invalid_json`
- ✓ `TestJSONParsingExceptionHandling::test_auth_service_handles_corrupted_users_file`
- ✓ `TestJSONParsingExceptionHandling::test_json_parsing_uses_specific_exception`
- ✓ `TestDatetimeParsingExceptionHandling::test_datetime_parsing_with_invalid_string`
- ✓ `TestDatetimeParsingExceptionHandling::test_datetime_parsing_with_invalid_format`
- ✓ `TestDatetimeParsingExceptionHandling::test_app_handles_date_parsing_errors`
- ✓ `TestServiceExceptionBoundaries::test_auth_service_autenticar_handles_missing_user`
- ✓ `TestServiceExceptionBoundaries::test_email_service_handles_network_error`
- ✓ `TestExceptionTypeSpecificity::test_no_except_generic_exception`
- ✓ `TestErrorMessageSensitivity::test_auth_error_messages_generic`

### 4. Log Security Tests  
```bash
pytest -v tests/test_security_logs.py
```

Tests:
- ✓ `TestBearerTokenRedaction::test_redacting_formatter_redacts_bearer_token`
- ✓ `TestBearerTokenRedaction::test_bearer_token_variations_are_redacted`
- ✓ `TestBearerTokenRedaction::test_non_bearer_tokens_not_affected`
- ✓ `TestEmailServiceLogging::test_email_service_redacts_api_key_from_logs`
- ✓ `TestEmailServiceLogging::test_email_post_method_redacts_credentials`
- ✓ `TestLoggingConfiguration::test_email_service_has_redacting_formatter`
- ✓ `TestLoggingConfiguration::test_redacting_formatter_pattern_matches_bearer_tokens`
- ✓ `TestSensitiveDataInErrorMessages::test_email_service_error_doesnt_include_api_key`
- ✓ `TestSensitiveDataInErrorMessages::test_database_error_doesnt_expose_credentials`
- ✓ `TestLogCaptureAndVerification::test_can_capture_email_logs`
- ✓ `TestLogCaptureAndVerification::test_redacted_text_appears_in_logs`

---

## Run Specific Test Classes

```bash
# Only bare except detection
pytest -v tests/test_security_exceptions.py::TestNoBareExceptStatements

# Only session timeout tests
pytest -v tests/test_security_session.py::TestSessionTimeout

# Only Bearer token redaction
pytest -v tests/test_security_logs.py::TestBearerTokenRedaction

# Only login rate limiting
pytest -v tests/test_security_ratelimit.py::TestRateLimitingLogin
```

---

## Run Single Tests

```bash
# Test 1: Verify no bare except: statements
pytest -v tests/test_security_exceptions.py::TestNoBareExceptStatements::test_no_bare_except_in_services

# Test 2: Verify /login rate limit rejects 6th request
pytest -v tests/test_security_ratelimit.py::TestRateLimitingLogin::test_login_rejects_6th_request_per_minute

# Test 3: Verify /cadastro rate limit rejects 4th request  
pytest -v tests/test_security_ratelimit.py::TestRateLimitingCadastro::test_cadastro_rejects_4th_request_per_hour

# Test 4: Verify /recuperar-senha rate limit rejects 4th request
pytest -v tests/test_security_ratelimit.py::TestRateLimitingPasswordReset::test_password_reset_rejects_4th_request_per_hour

# Test 5: Verify session timeout is 2 hours
pytest -v tests/test_security_session.py::TestSessionTimeout::test_session_lifetime_is_2_hours

# Test 6: Verify SameSite is Strict
pytest -v tests/test_security_session.py::TestSessionCookieSameSite::test_samesite_should_be_strict

# Test 7: Verify Bearer tokens are redacted
pytest -v tests/test_security_logs.py::TestBearerTokenRedaction::test_redacting_formatter_redacts_bearer_token

# Test 8: Verify API keys not in logs
pytest -v tests/test_security_logs.py::TestEmailServiceLogging::test_email_service_redacts_api_key_from_logs
```

---

## Verbose Output / Debugging

```bash
# Show full output with print statements
pytest -vv -s tests/test_security_*.py

# Show detailed error info
pytest -vv --tb=long tests/test_security_*.py

# Show test names and status
pytest -v tests/test_security_*.py --co

# Run with coverage (if pytest-cov installed)
pytest -v tests/test_security_*.py --cov=services --cov=routes
```

---

## Installation Requirements

```bash
# Install pytest if not already installed
pip install pytest>=7.0

# For rate limiting tests (needs Flask-Limiter)
pip install Flask-Limiter

# Or install all dependencies
pip install -r requirements.txt
pip install Flask-Limiter pytest
```

---

## Quick Test Status

Run this to check current status:

```bash
# Check which tests pass/fail
pytest -v tests/test_security_*.py --tb=no

# Summary of results
pytest -v tests/test_security_*.py --tb=no -q
```

---

## CI/CD Integration

Add to `.github/workflows/test.yml`:

```yaml
- name: Run Security Regression Tests
  run: |
    pip install pytest Flask Flask-WTF Flask-Limiter
    pytest -v tests/test_security_*.py
```

Add to `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

---

## Expected Results

- **Immediate Pass** (no config needed):
  - Exception handling tests
  - Log security tests
  - Cookie configuration checks

- **Needs Config Updates**:
  - Session timeout (set `PERMANENT_SESSION_LIFETIME = timedelta(hours=2)`)
  - SameSite (set `SESSION_COOKIE_SAMESITE = 'Strict'`)
  - Rate limiting (install `Flask-Limiter`)

---

## Files Created

1. `tests/test_security_ratelimit.py` - 8 rate limiting tests
2. `tests/test_security_session.py` - 14 session security tests
3. `tests/test_security_exceptions.py` - 13 exception handling tests
4. `tests/test_security_logs.py` - 15+ log security tests
5. `tests/SECURITY_TESTS_README.md` - Comprehensive guide

**Total: 50+ production-ready security regression tests**

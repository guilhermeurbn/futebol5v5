"""
Servico de email baseado na API do Resend.
"""
import json
import logging
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import requests


class RedactingFormatter(logging.Formatter):
    """Redacts sensitive credentials from log records."""
    
    BEARER_PATTERN = re.compile(r'Bearer\s+[\w\-._~+/]+=*')
    
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        return self.BEARER_PATTERN.sub('Bearer [REDACTED]', msg)


logger = logging.getLogger(__name__)
redacting_formatter = RedactingFormatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
for handler in logger.handlers:
    handler.setFormatter(redacting_formatter)


@dataclass
class EmailResult:
    ok: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class EmailService:
    """Envia emails transacionais usando Resend."""

    _DEFAULT_SECRETS_PATH = Path(__file__).resolve().parent.parent / '.secrets' / 'resend.json'

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self._api_key = (api_key or "").strip() if api_key is not None else ""
        self._from_email = (from_email or "").strip() if from_email is not None else ""
        self.base_url = (base_url if base_url is not None else os.getenv("APP_BASE_URL", "http://localhost:5051")).rstrip("/")

    def _load_secrets_file(self) -> tuple[str, str]:
        secrets_path = os.getenv('RESEND_SECRETS_FILE', str(self._DEFAULT_SECRETS_PATH)).strip()
        if not secrets_path:
            return '', ''

        path = Path(secrets_path).expanduser()
        if not path.exists():
            return '', ''

        try:
            with path.open('r', encoding='utf-8') as file:
                data = json.load(file) or {}
            api_key = (data.get('RESEND_API_KEY') or data.get('api_key') or '').strip()
            from_email = (data.get('RESEND_FROM_EMAIL') or data.get('from_email') or '').strip()
            return api_key, from_email
        except Exception as exc:
            logger.warning('Falha ao ler arquivo secreto de email %s: %s', path, exc)
            return '', ''

    def _resolve_credentials(self, api_key: Optional[str] = None, from_email: Optional[str] = None) -> tuple[str, str]:
        resolved_api_key = (api_key if api_key is not None else self._api_key).strip()
        resolved_from_email = (from_email if from_email is not None else self._from_email).strip()

        if not resolved_api_key:
            resolved_api_key = os.getenv('RESEND_API_KEY', '').strip()
        if not resolved_from_email:
            resolved_from_email = os.getenv('RESEND_FROM_EMAIL', '').strip()

        if not resolved_api_key or not resolved_from_email:
            file_api_key, file_from_email = self._load_secrets_file()
            if not resolved_api_key:
                resolved_api_key = file_api_key
            if not resolved_from_email:
                resolved_from_email = file_from_email

        return resolved_api_key, resolved_from_email

    def _enabled(self, api_key: Optional[str] = None, from_email: Optional[str] = None) -> bool:
        resolved_api_key, resolved_from_email = self._resolve_credentials(api_key=api_key, from_email=from_email)
        return bool(resolved_api_key and resolved_from_email)

    def _post(self, payload: dict, api_key: Optional[str] = None, from_email: Optional[str] = None) -> EmailResult:
        resolved_api_key, resolved_from_email = self._resolve_credentials(api_key=api_key, from_email=from_email)
        if not resolved_api_key or not resolved_from_email:
            logger.warning("Resend desativado: configure RESEND_API_KEY e RESEND_FROM_EMAIL")
            return EmailResult(ok=False, error="Resend nao configurado")

        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {resolved_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "NaTrave/1.0",
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json() if response.text else {}
            message_id = data.get("id")
            return EmailResult(ok=True, message_id=message_id)
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            details = exc.response.text if exc.response is not None else str(exc)
            logger.warning("Erro HTTP do Resend: %s - %s", status_code, self._redact_sensitive(details))
            return EmailResult(ok=False, error=f"HTTP {status_code}")
        except Exception as exc:
            logger.error("Erro ao enviar email via Resend: %s", self._redact_sensitive(str(exc)))
            return EmailResult(ok=False, error=str(exc))

    def _redact_sensitive(self, text: str) -> str:
        if not text:
            return text
        return RedactingFormatter.BEARER_PATTERN.sub('Bearer [REDACTED]', text)

    def send_email(self, to_email: str, subject: str, html: str, text: str = "") -> EmailResult:
        from_email = self._resolve_credentials()[1]
        payload = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text
        return self._post(payload)

    def send_welcome_email(self, to_email: str, nome: str, username: str) -> EmailResult:
        subject = "Bem-vindo ao NaTrave 5v5"
        html = f"""
        <div style="font-family: Arial, sans-serif; background:#0b0b0f; color:#f3f4f6; padding:24px;">
          <div style="max-width:600px;margin:0 auto;background:#111118;border:1px solid rgba(141,255,47,.18);border-radius:18px;padding:28px;">
            <p style="margin:0 0 12px;color:#8DFF2F;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">NaTrave 5v5</p>
            <h1 style="margin:0 0 12px;font-size:28px;line-height:1.1;">Sua conta foi criada com sucesso</h1>
            <p style="margin:0 0 18px;color:#d1d5db;font-size:16px;line-height:1.6;">Olá, {nome}. Agora você já pode entrar com seu usuário <strong>{username}</strong> e começar a organizar seus jogos.</p>
            <p style="margin:0;color:#d1d5db;line-height:1.6;">Se você esquecer a senha, basta usar o fluxo de recuperação por email.</p>
          </div>
        </div>
        """
        text = (
            f"Sua conta foi criada no NaTrave 5v5. "
            f"Olá, {nome}. Faça login com o usuário {username}. "
            f"Se precisar, use a recuperação de senha por email."
        )
        result = self.send_email(to_email, subject, html, text)
        return result

    def send_temporary_password_email(self, to_email: str, nome: str, username: str, senha_temporaria: str) -> EmailResult:
        subject = "Sua senha temporária no NaTrave 5v5"
        html = f"""
        <div style="font-family: Arial, sans-serif; background:#0b0b0f; color:#f3f4f6; padding:24px;">
            <div style="max-width:600px;margin:0 auto;background:#111118;border:1px solid rgba(141,255,47,.18);border-radius:18px;padding:28px;">
                <p style="margin:0 0 12px;color:#8DFF2F;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">NaTrave 5v5</p>
                <h1 style="margin:0 0 12px;font-size:28px;line-height:1.1;">Senha temporária gerada</h1>
                <p style="margin:0 0 18px;color:#d1d5db;font-size:16px;line-height:1.6;">Olá, {nome}. Sua senha temporária para a conta <strong>{username}</strong> é:</p>
                <div style="margin:0 0 22px;padding:16px 18px;border-radius:14px;background:rgba(124,58,237,.12);border:1px solid rgba(124,58,237,.18);font-size:18px;font-weight:700;letter-spacing:.02em;">{senha_temporaria}</div>
                <p style="margin:0;color:#9ca3af;font-size:14px;line-height:1.5;">Entre com essa senha e troque-a imediatamente no seu perfil para continuar usando o sistema.</p>
            </div>
        </div>
        """
        text = (
            f"Olá, {nome}. Sua senha temporária no NaTrave 5v5 para o usuário {username} é: {senha_temporaria}. "
            "Entre com ela e troque-a imediatamente no seu perfil."
        )
        return self.send_email(to_email, subject, html, text)

    def send_password_reset_email(self, to_email: str, nome: str, reset_url: str) -> EmailResult:
        subject = "Redefina sua senha no NaTrave 5v5"
        html = f"""
        <div style="font-family: Arial, sans-serif; background:#0b0b0f; color:#f3f4f6; padding:24px;">
            <div style="max-width:600px;margin:0 auto;background:#111118;border:1px solid rgba(141,255,47,.18);border-radius:18px;padding:28px;">
                <p style="margin:0 0 12px;color:#8DFF2F;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">NaTrave 5v5</p>
                <h1 style="margin:0 0 12px;font-size:28px;line-height:1.1;">Redefinicao de senha</h1>
                <p style="margin:0 0 18px;color:#d1d5db;font-size:16px;line-height:1.6;">Ola, {nome}. Use o link abaixo para criar uma nova senha.</p>
                <p style="margin:0 0 22px;"><a href="{reset_url}" style="display:inline-block;padding:12px 16px;border-radius:10px;background:#8DFF2F;color:#0b0b0f;text-decoration:none;font-weight:700;">Definir nova senha</a></p>
                <p style="margin:0;color:#9ca3af;font-size:14px;line-height:1.5;">Se voce nao pediu essa alteracao, ignore este email.</p>
            </div>
        </div>
        """
        text = (
            f"Ola, {nome}. Use este link para redefinir sua senha no NaTrave 5v5: {reset_url}. "
            "Se voce nao pediu essa alteracao, ignore este email."
        )
        return self.send_email(to_email, subject, html, text)

    def send_reset_token_email(self, to_email: str, nome: str, token: str) -> EmailResult:
        """Compatibilidade com testes legados que passam token ao invés de URL pronta."""
        reset_url = f"{self.base_url}/definir-senha?token={token}"
        return self.send_password_reset_email(to_email=to_email, nome=nome, reset_url=reset_url)

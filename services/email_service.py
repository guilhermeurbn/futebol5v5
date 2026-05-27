"""
Servico de email baseado na API do Resend.
"""
import json
import logging
import os
from dataclasses import dataclass
from typing import Optional
from urllib import error, request


logger = logging.getLogger(__name__)


@dataclass
class EmailResult:
    ok: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class EmailService:
    """Envia emails transacionais usando Resend."""

    def __init__(self) -> None:
        self.api_key = os.getenv("RESEND_API_KEY", "").strip()
        self.from_email = os.getenv("RESEND_FROM_EMAIL", "").strip()
        self.base_url = os.getenv("APP_BASE_URL", "http://localhost:5051").rstrip("/")

    def _enabled(self) -> bool:
        return bool(self.api_key and self.from_email)

    def _post(self, payload: dict) -> EmailResult:
        if not self._enabled():
            logger.warning("Resend desativado: configure RESEND_API_KEY e RESEND_FROM_EMAIL")
            return EmailResult(ok=False, error="Resend nao configurado")

        url = "https://api.resend.com/emails"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        req = request.Request(url, data=body, headers=headers, method="POST")

        try:
            with request.urlopen(req, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8") or "{}")
                message_id = data.get("id")
                return EmailResult(ok=True, message_id=message_id)
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            logger.error("Erro HTTP do Resend: %s - %s", exc.code, details)
            return EmailResult(ok=False, error=f"HTTP {exc.code}")
        except Exception as exc:
            logger.error("Erro ao enviar email via Resend: %s", exc)
            return EmailResult(ok=False, error=str(exc))

    def send_email(self, to_email: str, subject: str, html: str, text: str = "") -> EmailResult:
        payload = {
            "from": self.from_email,
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
        return self.send_email(to_email, subject, html, text)

        def send_temporary_password_email(self, to_email: str, nome: str, username: str, senha_temporaria: str) -> EmailResult:
                subject = "Sua nova senha no NaTrave 5v5"
                html = f"""
                <div style="font-family: Arial, sans-serif; background:#0b0b0f; color:#f3f4f6; padding:24px;">
                    <div style="max-width:600px;margin:0 auto;background:#111118;border:1px solid rgba(141,255,47,.18);border-radius:18px;padding:28px;">
                        <p style="margin:0 0 12px;color:#8DFF2F;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">NaTrave 5v5</p>
                        <h1 style="margin:0 0 12px;font-size:28px;line-height:1.1;">Senha atualizada</h1>
                        <p style="margin:0 0 18px;color:#d1d5db;font-size:16px;line-height:1.6;">Olá, {nome}. O admin redefiniu sua senha para a conta <strong>{username}</strong>.</p>
                        <div style="margin:0 0 22px;padding:16px 18px;border-radius:14px;background:rgba(124,58,237,.12);border:1px solid rgba(124,58,237,.18);font-size:18px;font-weight:700;letter-spacing:.02em;">{senha_temporaria}</div>
                        <p style="margin:0;color:#9ca3af;font-size:14px;line-height:1.5;">Entre no sistema e troque essa senha assim que possível.</p>
                    </div>
                </div>
                """
                text = (
                        f"Olá, {nome}. O admin redefiniu sua senha no NaTrave 5v5. "
                        f"Usuário: {username}. Senha temporária: {senha_temporaria}. "
                        "Troque essa senha assim que possível."
                )
                return self.send_email(to_email, subject, html, text)

    def send_password_reset_email(self, to_email: str, nome: str, reset_url: str) -> EmailResult:
        subject = "Redefina sua senha no NaTrave 5v5"
        html = f"""
        <div style="font-family: Arial, sans-serif; background:#0b0b0f; color:#f3f4f6; padding:24px;">
          <div style="max-width:600px;margin:0 auto;background:#111118;border:1px solid rgba(124,58,237,.18);border-radius:18px;padding:28px;">
            <p style="margin:0 0 12px;color:#8DFF2F;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">NaTrave 5v5</p>
            <h1 style="margin:0 0 12px;font-size:28px;line-height:1.1;">Redefinir senha</h1>
            <p style="margin:0 0 18px;color:#d1d5db;font-size:16px;line-height:1.6;">Olá, {nome}. Recebemos uma solicitação para redefinir sua senha.</p>
            <p style="margin:0 0 22px;line-height:1.6;"><a href="{reset_url}" style="display:inline-block;background:#7c3aed;color:#fff;text-decoration:none;padding:14px 20px;border-radius:12px;font-weight:700;">Criar nova senha</a></p>
            <p style="margin:0;color:#9ca3af;font-size:14px;line-height:1.5;">Se você não solicitou isso, pode ignorar este email.</p>
          </div>
        </div>
        """
        text = (
            f"Olá, {nome}. Para redefinir sua senha no NaTrave 5v5, acesse: {reset_url}. "
            "Se você não solicitou isso, ignore este email."
        )
        return self.send_email(to_email, subject, html, text)

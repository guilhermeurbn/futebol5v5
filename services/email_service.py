"""
Serviço de email baseado na API do Resend com templates totalmente pretos (dark theme premium)
e resolução estrita de URLs de produção (sem links para localhost).
"""
import json
import logging
import os
import re
import threading
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

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


def resolve_public_base_url(custom_base: Optional[str] = None) -> str:
    """
    Garante que nenhuma URL enviada por e-mail contenha 'localhost' ou '127.0.0.1'.
    Retorna a URL base de produção configurada ou o fallback seguro https://natrave.pt.
    """
    url = (custom_base or "").strip()
    if not url or "localhost" in url or "127.0.0.1" in url:
        url = (os.getenv("APP_BASE_URL") or os.getenv("PUBLIC_URL") or os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip()

    if not url or "localhost" in url or "127.0.0.1" in url:
        try:
            from flask import request, has_request_context
            if has_request_context() and request.host:
                host = request.host
                if "localhost" not in host and "127.0.0.1" not in host:
                    scheme = request.scheme or "https"
                    url = f"{scheme}://{host}"
        except Exception:
            pass

    if not url or "localhost" in url or "127.0.0.1" in url:
        url = "https://natrave.pt"

    if not url.startswith("http"):
        url = "https://" + url

    return url.rstrip("/")


def sanitize_email_url(url: str, base_url: str) -> str:
    """Substitui qualquer referência a localhost/127.0.0.1 pela base_url pública de produção."""
    if not url:
        return f"{base_url}/login"
    if "localhost" in url or "127.0.0.1" in url:
        match = re.search(r'https?://[^/]+(.*)', url)
        if match:
            path = match.group(1)
            return f"{base_url}{path}"
        return base_url
    return url


class EmailService:
    """Envia emails transacionais usando Resend com design profissional dark theme."""

    _DEFAULT_SECRETS_PATH = Path(__file__).resolve().parent.parent / '.secrets' / 'resend.json'

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self._api_key = (api_key or "").strip() if api_key is not None else ""
        self._from_email = (from_email or "").strip() if from_email is not None else ""
        self.base_url = resolve_public_base_url(base_url)

    def get_clean_base_url(self, override_url: Optional[str] = None) -> str:
        return resolve_public_base_url(override_url or self.base_url)

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

    def _build_email_html(
        self,
        to_email: str,
        preheader: str,
        badge_text: str,
        title: str,
        subtitle: str,
        highlight_card_html: str = "",
        steps: list = None,
        steps_title: str = "Próximos Passos",
        security_title: str = "Aviso de Segurança",
        security_text: str = "",
        cta_text: str = "Acessar NaTrave",
        cta_url: str = "",
    ) -> str:
        clean_base = self.get_clean_base_url()
        raw_cta = cta_url or f"{clean_base}/login"
        final_cta_url = sanitize_email_url(raw_cta, clean_base)

        # Construct Steps Section
        steps_html = ""
        if steps:
            items_html = ""
            for idx, (step_num, step_title, step_desc) in enumerate(steps, 1):
                margin_bottom = 14 if idx < len(steps) else 0
                items_html += f"""
                <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: {margin_bottom}px;">
                    <tr>
                        <td width="32" valign="top" style="padding-right: 12px;">
                            <div style="width: 26px; height: 26px; border-radius: 50%; background-color: rgba(34, 197, 94, 0.18) !important; border: 1px solid rgba(34, 197, 94, 0.4) !important; color: #4ade80 !important; font-size: 13px; font-weight: 800; text-align: center; line-height: 24px;">{step_num}</div>
                        </td>
                        <td valign="top">
                            <p style="margin: 0; font-size: 14px; font-weight: 700; color: #f4f4f5 !important; line-height: 1.4;">{step_title}</p>
                            <p style="margin: 2px 0 0 0; font-size: 13px; color: #a1a1aa !important; line-height: 1.4;">{step_desc}</p>
                        </td>
                    </tr>
                </table>
                """

            steps_html = f"""
            <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px; background-color: #181824 !important; border: 1px solid #27273a !important; border-radius: 14px; padding: 22px;">
                <tr>
                    <td>
                        <p style="margin: 0 0 16px 0; font-size: 12px; font-weight: 800; color: #ffffff !important; text-transform: uppercase; letter-spacing: 0.06em;">
                            <span style="color: #4ade80 !important; margin-right: 6px;">📋</span> {steps_title}
                        </p>
                        {items_html}
                    </td>
                </tr>
            </table>
            """

        # Construct Security Notice
        security_html = ""
        if security_text:
            security_html = f"""
            <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: rgba(245, 158, 11, 0.05) !important; border: 1px solid rgba(245, 158, 11, 0.25) !important; border-radius: 12px; padding: 18px 20px;">
                <tr>
                    <td valign="top" width="24" style="padding-right: 12px; font-size: 16px; line-height: 1;">
                        🛡️
                    </td>
                    <td valign="top">
                        <p style="margin: 0 0 4px 0; font-size: 13px; font-weight: 700; color: #fbbf24 !important;">
                            {security_title}
                        </p>
                        <p style="margin: 0; font-size: 12px; color: #d4d4d8 !important; line-height: 1.55;">
                            {security_text}
                        </p>
                    </td>
                </tr>
            </table>
            """

        # Construct CTA Button
        cta_html = f"""
        <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
            <tr>
                <td align="center">
                    <!--[if mso]>
                    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{final_cta_url}" style="height:50px;v-text-anchor:middle;width:240px;" arcsize="20%" stroke="f" fillcolor="#22c55e">
                        <w:anchorlock/>
                        <center style="color:#09090b;font-family:sans-serif;font-size:15px;font-weight:bold;">{cta_text}</center>
                    </v:roundrect>
                    <![endif]-->
                    <!--[if !mso]><!-->
                    <a href="{final_cta_url}" target="_blank" style="display: inline-block; padding: 15px 36px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 15px; font-weight: 800; color: #09090b !important; text-decoration: none; border-radius: 12px; background-color: #22c55e !important; border: 1px solid #22c55e !important; text-align: center; box-shadow: 0 6px 20px rgba(34, 197, 94, 0.4);">
                        {cta_text}
                    </a>
                    <!--<![endif]-->
                </td>
            </tr>
        </table>
        """

        return f"""<!DOCTYPE html>
<html lang="pt-BR" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="color-scheme" content="only dark">
    <meta name="supported-color-schemes" content="only dark">
    <title>{title}</title>
    <style>
        :root {{
            color-scheme: only dark !important;
            supported-color-schemes: only dark !important;
        }}
        html, body {{
            background-color: #09090b !important;
            color: #f4f4f5 !important;
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
        }}
        @media (prefers-color-scheme: light) {{
            body, table, td, div, p, span, a {{
                background-color: #09090b !important;
                color: #f4f4f5 !important;
            }}
        }}
        @media (prefers-color-scheme: dark) {{
            body, table, td, div, p, span, a {{
                background-color: #09090b !important;
                color: #f4f4f5 !important;
            }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; width: 100% !important; background-color: #09090b !important; color: #f4f4f5 !important; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <div style="display:none;font-size:1px;color:#09090b;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
        {preheader}
    </div>
    <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #09090b !important; width: 100%;">
        <tr>
            <td align="center" style="padding: 40px 16px; background-color: #09090b !important;">
                <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%; margin: 0 auto;">
                    
                    <!-- NATRAVE OFFICIAL LOGO HEADER -->
                    <tr>
                        <td align="center" style="padding-bottom: 28px;">
                            <table role="presentation" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="background-color: rgba(34, 197, 94, 0.12) !important; border: 1px solid rgba(34, 197, 94, 0.3) !important; border-radius: 9999px; padding: 10px 24px;">
                                        <span style="display: inline-block; width: 9px; height: 9px; background-color: #22c55e !important; border-radius: 50%; vertical-align: middle; margin-right: 10px; box-shadow: 0 0 8px #22c55e;"></span>
                                        <span style="font-size: 14px; font-weight: 900; color: #ffffff !important; letter-spacing: 0.15em; text-transform: uppercase; vertical-align: middle;">NATRAVE <span style="color: #22c55e !important;">5V5</span></span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- MAIN CARD CONTAINER -->
                    <tr>
                        <td style="background-color: #121217 !important; border: 1px solid #27272a !important; border-radius: 20px; padding: 38px 32px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.65);">
                            
                            <!-- BADGE -->
                            <table role="presentation" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 18px;">
                                <tr>
                                    <td style="font-size: 11px; font-weight: 800; color: #10b981 !important; letter-spacing: 0.12em; text-transform: uppercase; background-color: rgba(16, 185, 129, 0.15) !important; border-radius: 6px; padding: 5px 12px; border: 1px solid rgba(16, 185, 129, 0.35) !important;">
                                        {badge_text}
                                    </td>
                                </tr>
                            </table>

                            <!-- TITLE -->
                            <h1 style="margin: 0 0 16px 0; font-size: 25px; font-weight: 800; color: #ffffff !important; line-height: 1.25; letter-spacing: -0.02em;">
                                {title}
                            </h1>

                            <!-- SUBTITLE / INTRO TEXT -->
                            <div style="font-size: 15px; line-height: 1.6; color: #a1a1aa !important; margin-bottom: 28px;">
                                {subtitle}
                            </div>

                            <!-- HIGHLIGHT CARD -->
                            {highlight_card_html}

                            <!-- CTA BUTTON -->
                            {cta_html}

                            <!-- STEPS SECTION -->
                            {steps_html}

                            <!-- SECURITY NOTICE -->
                            {security_html}

                        </td>
                    </tr>

                    <!-- FOOTER -->
                    <tr>
                        <td align="center" style="padding-top: 32px; padding-bottom: 16px; text-align: center;">
                            <p style="margin: 0 0 8px 0; font-size: 13px; font-weight: 700; color: #71717a !important;">
                                NaTrave 5v5 &bull; Gestão Inteligente de Futebol
                            </p>
                            <p style="margin: 0 0 8px 0; font-size: 12px; color: #52525b !important; line-height: 1.5;">
                                Este e-mail transacional foi enviado para <span style="color: #a1a1aa !important;">{to_email}</span>.<br>Por favor, não responda diretamente a esta mensagem.
                            </p>
                            <p style="margin: 0; font-size: 11px; color: #3f3f46 !important;">
                                &copy; 2026 NaTrave 5v5. Todos os direitos reservados.
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    # ==================== SERVIÇOS DE E-MAIL LEGADOS / AUTENTICAÇÃO ====================

    def send_welcome_email(self, to_email: str, nome: str, username: str) -> EmailResult:
        subject = "Bem-vindo ao NaTrave 5v5"
        clean_base = self.get_clean_base_url()

        highlight_card_html = f"""
        <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
            <tr>
                <td style="background-color: #181824; border: 1px solid #27273a; border-radius: 14px; padding: 20px 24px;">
                    <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 800; color: #4ade80; letter-spacing: 0.08em; text-transform: uppercase;">
                        👤 Detalhes da sua Conta
                    </p>
                    <p style="margin: 0; font-size: 15px; color: #ffffff; font-weight: 700;">
                        Nome de usuário: <span style="font-family: 'SFMono-Regular', Consolas, monospace; color: #4ade80; font-size: 16px;">@{username}</span>
                    </p>
                </td>
            </tr>
        </table>
        """

        steps = [
            ("1", "Acesse sua conta", f"Entre com seu usuário <strong>@{username}</strong> e a senha cadastrada."),
            ("2", "Defina sua Posição de Jogo", "Acesse seu perfil para selecionar se atua como Jogador de Linha ou Goleiro."),
            ("3", "Participe dos Jogos", "Acompanhe os sorteios das partidas, estatísticas individuais e votações pós-jogo."),
        ]

        security_text = (
            "Mantenha suas credenciais em segurança. O NaTrave 5v5 nunca solicitará sua senha por e-mail ou WhatsApp."
        )

        html = self._build_email_html(
            to_email=to_email,
            preheader=f"Bem-vindo ao NaTrave 5v5, {nome}! Sua conta de usuário @{username} foi criada.",
            badge_text="CONTA CRIADA",
            title="Seja Bem-vindo ao NaTrave!",
            subtitle=f"Olá, <strong style=\"color:#ffffff;\">{nome}</strong>! Sua conta no NaTrave 5v5 foi criada com sucesso e já está pronta para uso.",
            highlight_card_html=highlight_card_html,
            steps=steps,
            steps_title="Primeiros Passos na Plataforma",
            security_title="Segurança da Conta",
            security_text=security_text,
            cta_text="Acessar NaTrave",
            cta_url=f"{clean_base}/login",
        )

        text = (
            f"Olá, {nome}!\n\n"
            f"Sua conta no NaTrave 5v5 foi criada com sucesso.\n"
            f"Usuário registrado: {username}\n\n"
            f"Acesse agora: {clean_base}/login"
        )
        # Dispara alerta de novo cadastro para natrave.suporte@gmail.com
        self.notify_admin_novo_cadastro(nome=nome, username=username, email=to_email)
        return self.send_email(to_email, subject, html, text)

    def send_temporary_password_email(self, to_email: str, nome: str, username: str, senha_temporaria: str) -> EmailResult:
        subject = "Sua senha temporária no NaTrave 5v5"
        clean_base = self.get_clean_base_url()

        highlight_card_html = f"""
        <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
            <tr>
                <td style="background-color: #061c14; border: 1px solid #22c55e; border-radius: 14px; padding: 22px 24px; text-align: center;">
                    <p style="margin: 0 0 8px 0; font-size: 12px; font-weight: 800; color: #4ade80; letter-spacing: 0.08em; text-transform: uppercase;">
                        🔑 Sua Senha Temporária
                    </p>
                    <div style="font-family: 'SFMono-Regular', Consolas, monospace; font-size: 26px; font-weight: 800; color: #ffffff; letter-spacing: 3px; background-color: #0d281e; border: 1px solid rgba(34, 197, 94, 0.4); border-radius: 10px; padding: 12px 20px; margin: 6px 0 0 0; display: inline-block; word-break: break-all;">
                        {senha_temporaria}
                    </div>
                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #a7f3d0;">
                        Copie a senha acima para realizar o seu login temporário.
                    </p>
                </td>
            </tr>
        </table>
        """

        steps = [
            ("1", "Acesse a plataforma", "Clique no botão verde \"Acessar NaTrave\" abaixo para ir à tela de login."),
            ("2", "Faça login com a senha temporária", f"Insira seu usuário (<strong>{username}</strong>) e a senha em destaque acima."),
            ("3", "Cadastre uma nova senha definitiva", "Ao entrar, você será direcionado para cadastrar sua nova senha pessoal."),
        ]

        security_text = (
            "Por motivos de segurança, esta senha temporária é de uso provisório e único. "
            "Recomendamos efetuar o login e alterar sua senha imediatamente."
        )

        html = self._build_email_html(
            to_email=to_email,
            preheader=f"Olá, {nome}! Sua senha temporária no NaTrave 5v5 é {senha_temporaria}.",
            badge_text="RECUPERAÇÃO DE SENHA",
            title="Sua Senha Temporária",
            subtitle=f"Olá, <strong style=\"color:#ffffff;\">{nome}</strong>. Geramos uma nova senha temporária exclusiva para a sua conta <strong style=\"color:#ffffff;\">@{username}</strong>.",
            highlight_card_html=highlight_card_html,
            steps=steps,
            steps_title="3 passos para utilizar sua senha",
            security_title="Aviso de Segurança",
            security_text=security_text,
            cta_text="Acessar NaTrave",
            cta_url=f"{clean_base}/login",
        )

        text = (
            f"Olá, {nome}.\n\n"
            f"Sua senha temporária no NaTrave 5v5 para a conta {username} é:\n"
            f"{senha_temporaria}\n\n"
            f"Acesse: {clean_base}/login"
        )
        self.notify_admin_solicitacao_senha(nome=nome, username=username, email=to_email, tipo_acao="Senha Temporária Gerada")
        return self.send_email(to_email, subject, html, text)

    def send_password_reset_email(self, to_email: str, nome: str, reset_url: str) -> EmailResult:
        subject = "Redefina sua senha no NaTrave 5v5"
        clean_base = self.get_clean_base_url()
        safe_reset_url = sanitize_email_url(reset_url, clean_base)

        highlight_card_html = f"""
        <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
            <tr>
                <td style="background-color: #181824; border: 1px solid #27273a; border-radius: 14px; padding: 18px 22px;">
                    <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 800; color: #a1a1aa; letter-spacing: 0.05em; text-transform: uppercase;">
                        🔗 Link de Redefinição
                    </p>
                    <p style="margin: 0; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; color: #4ade80; word-break: break-all;">
                        {safe_reset_url}
                    </p>
                </td>
            </tr>
        </table>
        """

        steps = [
            ("1", "Clique no botão de acesso", "Clique em \"Acessar NaTrave\" abaixo para ir à tela de redefinição."),
            ("2", "Cadastre a nova senha", "Escolha uma nova senha forte com combinação de letras e números."),
            ("3", "Faça login com a nova senha", "Após salvar, faça seu login normalmente com as novas credenciais."),
        ]

        security_text = (
            "Este link de redefinição de senha é seguro e temporário. "
            "Se você não solicitou a redefinição de senha, nenhuma alteração foi realizada em sua conta."
        )

        html = self._build_email_html(
            to_email=to_email,
            preheader=f"Olá, {nome}. Clique no link para redefinir sua senha no NaTrave 5v5.",
            badge_text="REDEFINIÇÃO DE SENHA",
            title="Redefina a sua Senha",
            subtitle=f"Olá, <strong style=\"color:#ffffff;\">{nome}</strong>. Recebemos uma solicitação para redefinir a senha da sua conta no NaTrave 5v5.",
            highlight_card_html=highlight_card_html,
            steps=steps,
            steps_title="Como redefinir sua senha",
            security_title="Aviso de Segurança",
            security_text=security_text,
            cta_text="Acessar NaTrave",
            cta_url=safe_reset_url,
        )

        text = (
            f"Olá, {nome}.\n\n"
            f"Use este link para redefinir sua senha no NaTrave 5v5:\n{safe_reset_url}\n\n"
            "Se você não solicitou esta alteração, ignore este e-mail."
        )
        self.notify_admin_solicitacao_senha(nome=nome, username="", email=to_email, tipo_acao="Link de Redefinição de Senha Solicitado")
        return self.send_email(to_email, subject, html, text)

    def send_reset_token_email(self, to_email: str, nome: str, token: str) -> EmailResult:
        clean_base = self.get_clean_base_url()
        reset_url = f"{clean_base}/definir-senha?token={token}"
        return self.send_password_reset_email(to_email=to_email, nome=nome, reset_url=reset_url)

    # ==================== NOVOS SERVIÇOS DE NOTIFICAÇÃO DA PARTIDA ====================

    def send_presenca_aberta_email(self, to_email: str, nome: str, data_rodada: str = "Próxima Terça-Feira") -> EmailResult:
        """Envia e-mail informando que a lista de presença para a rodada de terça está aberta."""
        subject = f"⚽ Rodada Aberta: Confirme sua presença para {data_rodada}!"
        clean_base = self.get_clean_base_url()
        cta_url = f"{clean_base}/login"

        highlight_card_html = f"""
        <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
            <tr>
                <td style="background-color: #061c14; border: 1px solid #22c55e; border-radius: 14px; padding: 22px 24px;">
                    <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 800; color: #4ade80; letter-spacing: 0.08em; text-transform: uppercase;">
                        📅 Rodada de Futebol
                    </p>
                    <p style="margin: 0 0 4px 0; font-size: 18px; color: #ffffff; font-weight: 800;">
                        {data_rodada}
                    </p>
                    <p style="margin: 0; font-size: 13px; color: #a7f3d0; line-height: 1.4;">
                        A lista de confirmação de presença já está aberta! Acesse o app e garanta sua vaga.
                    </p>
                </td>
            </tr>
        </table>
        """

        steps = [
            ("1", "Acesse a lista de presença", "Clique no botão verde \"Confirmar Presença\" abaixo para acessar a plataforma."),
            ("2", "Selecione seu status", "Marque \"Confirmado\", \"Ausente\" ou \"Dúvida\" para informar a organização."),
            ("3", "Acompanhe os sorteios", "Fique atento aos horários de sorteio das equipes para a partida."),
        ]

        html = self._build_email_html(
            to_email=to_email,
            preheader=f"A rodada da {data_rodada} já está aberta para inscrição de presença. Confirme agora no NaTrave 5v5!",
            badge_text="INSCRIÇÃO DE PRESENÇA ABERTA",
            title=f"Rodada Aberta: {data_rodada}",
            subtitle=f"Olá, <strong style=\"color:#ffffff;\">{nome}</strong>! A lista de inscrição para a rodada de futebol da <strong style=\"color:#4ade80;\">{data_rodada}</strong> já está aberta oficialmente.",
            highlight_card_html=highlight_card_html,
            steps=steps,
            steps_title="Como confirmar sua presença",
            security_title="Importante",
            security_text="A confirmação prévia é essencial para que a organização realize o sorteio equilibrado dos times.",
            cta_text="Confirmar Presença",
            cta_url=cta_url,
        )

        text = (
            f"Olá, {nome}!\n\n"
            f"A rodada da {data_rodada} já está aberta para inscrição de presença no NaTrave 5v5!\n\n"
            f"Confirme sua vaga agora: {cta_url}"
        )
        return self.send_email(to_email, subject, html, text)

    def send_votacao_aberta_email(self, to_email: str, nome: str, partida_titulo: str = "Votação da Partida") -> EmailResult:
        """Envia e-mail de votação aberta EXCLUSIVAMENTE para os participantes da partida."""
        subject = "⭐ Votação Aberta: Avalie seus companheiros de partida!"
        clean_base = self.get_clean_base_url()
        cta_url = f"{clean_base}/votacao"

        highlight_card_html = f"""
        <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
            <tr>
                <td style="background-color: #181028; border: 1px solid #a78bfa; border-radius: 14px; padding: 22px 24px;">
                    <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 800; color: #c084fc; letter-spacing: 0.08em; text-transform: uppercase;">
                        ⭐ Avaliação da Partida
                    </p>
                    <p style="margin: 0 0 4px 0; font-size: 18px; color: #ffffff; font-weight: 800;">
                        {partida_titulo}
                    </p>
                    <p style="margin: 0; font-size: 13px; color: #e9d5ff; line-height: 1.4;">
                        Sua partida foi finalizada! A votação para avaliar o desempenho dos atletas já está disponível.
                    </p>
                </td>
            </tr>
        </table>
        """

        steps = [
            ("1", "Acesse a área de votação", "Clique no botão verde \"Votar Agora\" para abrir diretamente a tela de avaliação."),
            ("2", "Avalie seus companheiros", "Atribua notas de 0 a 10 para pelo menos 5 jogadores da rodada."),
            ("3", "Envie seus votos", "Seus votos serão computados no ranking oficial da temporada."),
        ]

        html = self._build_email_html(
            to_email=to_email,
            preheader=f"Olá {nome}! A votação para a partida {partida_titulo} já está aberta. Avalie seus companheiros no NaTrave 5v5!",
            badge_text="VOTAÇÃO DA PARTIDA ABERTA",
            title="Avalie os Jogadores da Rodada",
            subtitle=f"Olá, <strong style=\"color:#ffffff;\">{nome}</strong>! A sua partida <strong style=\"color:#a78bfa;\">{partida_titulo}</strong> foi encerrada e a votação pós-jogo já está liberada exclusivamente para os participantes.",
            highlight_card_html=highlight_card_html,
            steps=steps,
            steps_title="3 passos para registrar suas notas",
            security_title="Regra de Votação",
            security_text="Suas avaliações são confidenciais e contribuem diretamente para a pontuação e estatísticas dos atletas.",
            cta_text="Votar Agora",
            cta_url=cta_url,
        )

        text = (
            f"Olá, {nome}!\n\n"
            f"A votação para a partida '{partida_titulo}' já está aberta no NaTrave 5v5!\n\n"
            f"Avalie seus companheiros agora: {cta_url}"
        )
        return self.send_email(to_email, subject, html, text)

    def send_ranking_disponivel_email(self, to_email: str, nome: str, partida_titulo: str = "Ranking Atualizado") -> EmailResult:
        """Envia e-mail informando que a apuração terminou e o novo ranking está disponível."""
        subject = "🏆 Ranking Atualizado: Confira as novas posições e estatísticas!"
        clean_base = self.get_clean_base_url()
        cta_url = f"{clean_base}/#ranking"

        highlight_card_html = f"""
        <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
            <tr>
                <td style="background-color: #1c190f; border: 1px solid #f59e0b; border-radius: 14px; padding: 22px 24px;">
                    <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 800; color: #fbbf24; letter-spacing: 0.08em; text-transform: uppercase;">
                        🏆 Classificação Geral
                    </p>
                    <p style="margin: 0 0 4px 0; font-size: 18px; color: #ffffff; font-weight: 800;">
                        {partida_titulo}
                    </p>
                    <p style="margin: 0; font-size: 13px; color: #fde68a; line-height: 1.4;">
                        A apuração das notas da rodada foi concluída! Confira seu desempenho e nova colocação na tabela.
                    </p>
                </td>
            </tr>
        </table>
        """

        steps = [
            ("1", "Acesse o Ranking", "Clique no botão \"Ver Ranking\" para visualizar a tabela de classificação atualizada."),
            ("2", "Confira seu Desempenho", "Veja suas notas, gols, vitórias e evolução de nível."),
            ("3", "Acompanhe as estatísticas", "Compare suas estatísticas com os outros atletas da temporada."),
        ]

        html = self._build_email_html(
            to_email=to_email,
            preheader="O ranking do NaTrave 5v5 foi atualizado! Veja sua nova posição na tabela.",
            badge_text="RANKING DA TEMPORADA DISPONÍVEL",
            title="Ranking da Rodada Atualizado",
            subtitle=f"Olá, <strong style=\"color:#ffffff;\">{nome}</strong>! As avaliações da partida <strong style=\"color:#fbbf24;\">{partida_titulo}</strong> foram apuradas e o ranking geral foi atualizado.",
            highlight_card_html=highlight_card_html,
            steps=steps,
            steps_title="O que você pode conferir agora",
            security_title="Estatísticas da Temporada",
            security_text="O ranking é atualizado automaticamente ao final da apuração de cada rodada.",
            cta_text="Ver Ranking Completo",
            cta_url=cta_url,
        )

        text = (
            f"Olá, {nome}!\n\n"
            f"O ranking da temporada no NaTrave 5v5 foi atualizado após a apuração da partida '{partida_titulo}'!\n\n"
            f"Confira a tabela completa agora: {cta_url}"
        )
        return self.send_email(to_email, subject, html, text)

    # ==================== MÉTODOS DE DISPARO EM LOTE / ASSÍNCRONO ====================

    def _normalizar_texto(self, texto: Optional[str]) -> str:
        import unicodedata
        t = unicodedata.normalize("NFKD", (texto or "").strip().lower())
        return "".join(c for c in t if not unicodedata.combining(c))

    def notify_presenca_aberta(self, jogadores: Optional[list] = None, data_rodada: str = "Próxima Terça-Feira") -> None:
        """Dispara e-mail de presença aberta em segundo plano para todos os perfis e usuários com e-mail cadastrado."""
        def _run():
            try:
                from services.jogador_service import JogadorService
                from services.auth_service import AuthService
                js = JogadorService()
                aus = AuthService()
                
                destinatarios = {}  # email.lower() -> nome

                # 1. Carregar jogadores cadastrados
                lista_efetiva = jogadores or js.listar()
                for j in lista_efetiva:
                    email = getattr(j, "email", None) or (j.get("email") if isinstance(j, dict) else None)
                    nome = getattr(j, "nome", None) or (j.get("nome") if isinstance(j, dict) else "Jogador")
                    if email and "@" in str(email):
                        e_clean = str(email).strip().lower()
                        if e_clean not in destinatarios:
                            destinatarios[e_clean] = str(nome)

                # 2. Carregar todos os usuários do sistema de autenticação
                try:
                    todos_usuarios = aus.listar_usuarios()
                    for u in todos_usuarios:
                        email = u.get("email")
                        nome = u.get("nome") or u.get("username") or "Jogador"
                        if email and "@" in str(email):
                            e_clean = str(email).strip().lower()
                            if e_clean not in destinatarios:
                                destinatarios[e_clean] = str(nome)
                except Exception as _exc_u:
                    logger.warning("Aviso ao carregar usuários de auth para presença: %s", _exc_u)

                # 3. Disparar e-mails para todos os perfis encontrados
                for e_mail, n_ome in destinatarios.items():
                    try:
                        self.send_presenca_aberta_email(to_email=e_mail, nome=n_ome, data_rodada=data_rodada)
                    except Exception as exc:
                        logger.warning("Erro ao enviar email de presença para %s: %s", e_mail, exc)
            except Exception as e:
                logger.error("Erro no worker notify_presenca_aberta: %s", e)

        threading.Thread(target=_run, daemon=True).start()

    def notify_votacao_aberta(self, participantes: list, partida_titulo: str = "Votação da Partida") -> None:
        """Dispara e-mail de votação aberta APENAS para os participantes da partida."""
        def _run():
            try:
                from services.jogador_service import JogadorService
                js = JogadorService()
                todos_jogadores = js.listar()
                by_user_id = {str(j.owner_user_id): j for j in todos_jogadores if getattr(j, 'owner_user_id', None)}
                by_nome = {self._normalizar_texto(j.nome): j for j in todos_jogadores if getattr(j, 'nome', None)}

                for p in (participantes or []):
                    email = getattr(p, "email", None) or (p.get("email") if isinstance(p, dict) else None)
                    nome = getattr(p, "jogador_nome", None) or getattr(p, "nome", None) or (p.get("jogador_nome") or p.get("nome") if isinstance(p, dict) else "Jogador")
                    user_id = getattr(p, "user_id", None) or (p.get("user_id") if isinstance(p, dict) else None)

                    if not email:
                        atleta = None
                        if user_id and str(user_id) in by_user_id:
                            atleta = by_user_id[str(user_id)]
                        elif nome:
                            chave = self._normalizar_texto(nome)
                            if chave in by_nome:
                                atleta = by_nome[chave]
                        
                        if atleta and getattr(atleta, "email", None):
                            email = atleta.email

                    if email and "@" in str(email):
                        try:
                            self.send_votacao_aberta_email(to_email=str(email), nome=str(nome), partida_titulo=partida_titulo)
                        except Exception as exc:
                            logger.warning("Erro ao enviar email de votação para %s: %s", email, exc)
            except Exception as e:
                logger.error("Erro no worker notify_votacao_aberta: %s", e)

        threading.Thread(target=_run, daemon=True).start()

    def notify_ranking_disponivel(self, jogadores: Optional[list] = None, partida_titulo: str = "Ranking Atualizado") -> None:
        """Dispara e-mail de ranking disponível em segundo plano para todos os jogadores."""
        def _run():
            try:
                from services.jogador_service import JogadorService
                js = JogadorService()
                lista_efetiva = jogadores or js.listar()
                for j in lista_efetiva:
                    email = getattr(j, "email", None) or (j.get("email") if isinstance(j, dict) else None)
                    nome = getattr(j, "nome", None) or (j.get("nome") if isinstance(j, dict) else "Jogador")
                    if email and "@" in str(email):
                        try:
                            self.send_ranking_disponivel_email(to_email=str(email), nome=str(nome), partida_titulo=partida_titulo)
                        except Exception as exc:
                            logger.warning("Erro ao enviar email de ranking para %s: %s", email, exc)
            except Exception as e:
                logger.error("Erro no worker notify_ranking_disponivel: %s", e)

        threading.Thread(target=_run, daemon=True).start()

    def notify_admin_novo_cadastro(self, nome: str, username: str, email: str) -> None:
        """Envia e-mail de alerta para natrave.suporte@gmail.com quando uma conta é criada ou e-mail é cadastrado."""
        def _run():
            try:
                from datetime import datetime
                data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
                subject = f"🔔 [NaTrave Suporte] Novo Cadastro / E-mail: @{username}"
                
                highlight_card_html = f"""
                <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                    <tr>
                        <td style="background-color: #061c14 !important; border: 1px solid #22c55e !important; border-radius: 14px; padding: 20px 22px;">
                            <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 800; color: #4ade80 !important; letter-spacing: 0.08em; text-transform: uppercase;">
                                👤 Dados do Atleta
                            </p>
                            <p style="margin: 0 0 4px 0; font-size: 16px; color: #ffffff !important; font-weight: 700;">
                                Nome: <strong style="color: #ffffff !important;">{nome}</strong>
                            </p>
                            <p style="margin: 0 0 4px 0; font-size: 15px; color: #a7f3d0 !important;">
                                Usuário: <span style="font-family: monospace; color: #4ade80 !important;">@{username}</span>
                            </p>
                            <p style="margin: 0 0 4px 0; font-size: 15px; color: #a7f3d0 !important;">
                                E-mail Cadastrado: <strong style="color: #ffffff !important;">{email}</strong>
                            </p>
                            <p style="margin: 8px 0 0 0; font-size: 12px; color: #71717a !important;">
                                Registrado em: {data_hora}
                            </p>
                        </td>
                    </tr>
                </table>
                """

                html = self._build_email_html(
                    to_email="natrave.suporte@gmail.com",
                    preheader=f"Novo cadastro realizado por {nome} (@{username})",
                    badge_text="ALERTA DE SISTEMA • NOVO CADASTRO",
                    title="Novo Atleta Cadastrado",
                    subtitle=f"Um novo jogador acabou de registrar/atualizar seu e-mail na plataforma <strong style=\"color:#22c55e;\">NaTrave 5v5</strong>.",
                    highlight_card_html=highlight_card_html,
                    cta_text="Acessar Painel de Controle",
                    cta_url=f"{self.get_clean_base_url()}/admin"
                )

                text = f"Novo cadastro no NaTrave 5v5:\nNome: {nome}\nUsuário: @{username}\nE-mail: {email}\nData: {data_hora}"
                self.send_email("natrave.suporte@gmail.com", subject, html, text)
            except Exception as exc:
                logger.warning("Falha ao enviar e-mail de alerta de cadastro para suporte: %s", exc)

        threading.Thread(target=_run, daemon=True).start()

    def notify_admin_solicitacao_senha(self, nome: str, username: str, email: str, tipo_acao: str = "Solicitação de Senha") -> None:
        """Envia e-mail de alerta para natrave.suporte@gmail.com sobre alteração/solicitação de senha de jogador."""
        def _run():
            try:
                from datetime import datetime
                data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
                subject = f"🚨 [NaTrave Suporte] Alerta de Senha: @{username or email} ({tipo_acao})"
                
                highlight_card_html = f"""
                <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                    <tr>
                        <td style="background-color: #241418 !important; border: 1px solid #f43f5e !important; border-radius: 14px; padding: 20px 22px;">
                            <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 800; color: #fb7185 !important; letter-spacing: 0.08em; text-transform: uppercase;">
                                🔑 Detalhes da Solicitação
                            </p>
                            <p style="margin: 0 0 4px 0; font-size: 16px; color: #ffffff !important; font-weight: 700;">
                                Jogador: <strong style="color: #ffffff !important;">{nome}</strong>
                            </p>
                            <p style="margin: 0 0 4px 0; font-size: 15px; color: #fecdd3 !important;">
                                Usuário: <span style="font-family: monospace; color: #fb7185 !important;">@{username or 'N/A'}</span>
                            </p>
                            <p style="margin: 0 0 4px 0; font-size: 15px; color: #fecdd3 !important;">
                                E-mail: <strong style="color: #ffffff !important;">{email}</strong>
                            </p>
                            <p style="margin: 0 0 4px 0; font-size: 15px; color: #ffffff !important;">
                                Ação Realizada: <strong style="color: #fb7185 !important;">{tipo_acao}</strong>
                            </p>
                            <p style="margin: 8px 0 0 0; font-size: 12px; color: #71717a !important;">
                                Ocorrido em: {data_hora}
                            </p>
                        </td>
                    </tr>
                </table>
                """

                html = self._build_email_html(
                    to_email="natrave.suporte@gmail.com",
                    preheader=f"Alerta de segurança: {tipo_acao} para @{username or email}",
                    badge_text="ALERTA DE SEGURANÇA • SENHA",
                    title="Solicitação/Troca de Senha",
                    subtitle="Um jogador solicitou redefinição ou alterou a senha de acesso na plataforma.",
                    highlight_card_html=highlight_card_html,
                    cta_text="Acessar Painel Admin",
                    cta_url=f"{self.get_clean_base_url()}/admin"
                )

                text = f"Alerta de Senha no NaTrave 5v5:\nJogador: {nome}\nUsuário: @{username}\nE-mail: {email}\nAção: {tipo_acao}\nData: {data_hora}"
                self.send_email("natrave.suporte@gmail.com", subject, html, text)
            except Exception as exc:
                logger.warning("Falha ao enviar e-mail de alerta de senha para suporte: %s", exc)

        threading.Thread(target=_run, daemon=True).start()

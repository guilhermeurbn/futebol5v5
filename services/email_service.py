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
        login_url = cta_url or f"{self.base_url}/login"

        # Construct 3 Steps Section
        steps_html = ""
        if steps:
            items_html = ""
            for idx, (step_num, step_title, step_desc) in enumerate(steps, 1):
                margin_bottom = 14 if idx < len(steps) else 0
                items_html += f"""
                <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: {margin_bottom}px;">
                    <tr>
                        <td width="32" valign="top" style="padding-right: 12px;">
                            <div style="width: 26px; height: 26px; border-radius: 50%; background-color: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #10b981; font-size: 13px; font-weight: 700; text-align: center; line-height: 24px;">{step_num}</div>
                        </td>
                        <td valign="top">
                            <p style="margin: 0; font-size: 14px; font-weight: 600; color: #f4f4f5; line-height: 1.4;">{step_title}</p>
                            <p style="margin: 2px 0 0 0; font-size: 13px; color: #a1a1aa; line-height: 1.4;">{step_desc}</p>
                        </td>
                    </tr>
                </table>
                """

            steps_html = f"""
            <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px; background-color: #16161e; border: 1px solid #27272a; border-radius: 14px; padding: 24px;">
                <tr>
                    <td>
                        <p style="margin: 0 0 16px 0; font-size: 13px; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.05em;">
                            <span style="color: #10b981; margin-right: 6px;">📋</span> {steps_title}
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
            <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: rgba(245, 158, 11, 0.05); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 12px; padding: 18px 20px;">
                <tr>
                    <td valign="top" width="24" style="padding-right: 12px; font-size: 16px; line-height: 1;">
                        🛡️
                    </td>
                    <td valign="top">
                        <p style="margin: 0 0 4px 0; font-size: 13px; font-weight: 700; color: #f59e0b;">
                            {security_title}
                        </p>
                        <p style="margin: 0; font-size: 12px; color: #d4d4d8; line-height: 1.55;">
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
                    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{login_url}" style="height:48px;v-text-anchor:middle;width:240px;" arcsize="20%" stroke="f" fillcolor="#10b981">
                        <w:anchorlock/>
                        <center style="color:#09090b;font-family:sans-serif;font-size:15px;font-weight:bold;">{cta_text}</center>
                    </v:roundrect>
                    <![endif]-->
                    <!--[if !mso]><!-->
                    <a href="{login_url}" target="_blank" style="display: inline-block; padding: 14px 32px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 15px; font-weight: 700; color: #09090b; text-decoration: none; border-radius: 10px; background-color: #10b981; border: 1px solid #10b981; text-align: center; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);">
                        {cta_text}
                    </a>
                    <!--<![endif]-->
                </td>
            </tr>
        </table>
        """

        return f"""<!DOCTYPE html>
<html lang="pt-BR" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="color-scheme" content="dark">
    <meta name="supported-color-schemes" content="dark">
    <title>{title}</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; width: 100% !important; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; background-color: #09090b; color: #f4f4f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <!--[if !mso]><!-->
    <div style="display:none;font-size:1px;color:#09090b;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
        {preheader}
    </div>
    <!--<![endif]-->
    <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #09090b; width: 100%;">
        <tr>
            <td align="center" style="padding: 40px 16px;">
                <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%; margin: 0 auto;">
                    
                    <!-- HEADER LOGO -->
                    <tr>
                        <td align="center" style="padding-bottom: 28px;">
                            <table role="presentation" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 9999px; padding: 8px 18px;">
                                        <span style="display: inline-block; width: 8px; height: 8px; background-color: #10b981; border-radius: 50%; vertical-align: middle; margin-right: 8px;"></span>
                                        <span style="font-size: 13px; font-weight: 700; color: #10b981; letter-spacing: 0.1em; text-transform: uppercase; vertical-align: middle;">NATRAVE 5V5</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- CARD CONTAINER -->
                    <tr>
                        <td style="background-color: #121217; border: 1px solid #27272a; border-radius: 20px; padding: 40px 36px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
                            
                            <!-- BADGE -->
                            <table role="presentation" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 16px;">
                                <tr>
                                    <td style="font-size: 11px; font-weight: 800; color: #10b981; letter-spacing: 0.12em; text-transform: uppercase; background-color: rgba(16, 185, 129, 0.1); border-radius: 6px; padding: 4px 10px; border: 1px solid rgba(16, 185, 129, 0.2);">
                                        {badge_text}
                                    </td>
                                </tr>
                            </table>

                            <!-- TITLE -->
                            <h1 style="margin: 0 0 16px 0; font-size: 26px; font-weight: 700; color: #ffffff; line-height: 1.25; letter-spacing: -0.02em;">
                                {title}
                            </h1>

                            <!-- SUBTITLE / INTRO TEXT -->
                            <div style="font-size: 15px; line-height: 1.6; color: #a1a1aa; margin-bottom: 28px;">
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
                            <p style="margin: 0 0 8px 0; font-size: 13px; font-weight: 600; color: #71717a;">
                                NaTrave 5v5 &bull; Gestão Inteligente de Futebol
                            </p>
                            <p style="margin: 0 0 8px 0; font-size: 12px; color: #52525b; line-height: 1.5;">
                                Este e-mail transacional foi enviado para <span style="color: #a1a1aa;">{to_email}</span>.<br>Por favor, não responda diretamente a esta mensagem.
                            </p>
                            <p style="margin: 0; font-size: 11px; color: #3f3f46;">
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

    def send_welcome_email(self, to_email: str, nome: str, username: str) -> EmailResult:
        subject = "Bem-vindo ao NaTrave 5v5"

        highlight_card_html = f"""
        <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
            <tr>
                <td style="background-color: #16161e; border: 1px solid #27272a; border-radius: 12px; padding: 20px 24px;">
                    <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 700; color: #10b981; letter-spacing: 0.08em; text-transform: uppercase;">
                        👤 Detalhes da sua Conta
                    </p>
                    <p style="margin: 0; font-size: 15px; color: #ffffff; font-weight: 600;">
                        Nome de usuário: <span style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; color: #10b981; font-size: 16px;">@{username}</span>
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
            cta_url=f"{self.base_url}/login",
        )

        text = (
            f"Olá, {nome}!\n\n"
            f"Sua conta no NaTrave 5v5 foi criada com sucesso.\n"
            f"Usuário registrado: {username}\n\n"
            f"Acesse agora: {self.base_url}/login"
        )
        return self.send_email(to_email, subject, html, text)

    def send_temporary_password_email(self, to_email: str, nome: str, username: str, senha_temporaria: str) -> EmailResult:
        subject = "Sua senha temporária no NaTrave 5v5"

        highlight_card_html = f"""
        <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
            <tr>
                <td style="background-color: #061c14; border: 1px solid #10b981; border-radius: 12px; padding: 22px 24px; text-align: center;">
                    <p style="margin: 0 0 8px 0; font-size: 12px; font-weight: 700; color: #34d399; letter-spacing: 0.08em; text-transform: uppercase;">
                        🔑 Sua Senha Temporária
                    </p>
                    <div style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 26px; font-weight: 700; color: #ffffff; letter-spacing: 3px; background-color: #0d281e; border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 12px 18px; margin: 6px 0 0 0; display: inline-block; word-break: break-all;">
                        {senha_temporaria}
                    </div>
                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #6ee7b7;">
                        Copie a senha acima para realizar o seu login temporário.
                    </p>
                </td>
            </tr>
        </table>
        """

        steps = [
            ("1", "Acesse a plataforma", "Clique no botão verde \"Acessar NaTrave\" abaixo para ir à tela de login."),
            ("2", "Faça login com a senha temporária", f"Insira seu usuário (<strong>{username}</strong>) e a senha em destaque no card acima."),
            ("3", "Cadastre uma nova senha definitiva", "Ao entrar, você será direcionado para cadastrar sua nova senha pessoal e segura."),
        ]

        security_text = (
            "Por motivos de segurança, esta senha temporária é de uso provisório e único. "
            "Recomendamos efetuar o login e alterar sua senha imediatamente. "
            "Se você não solicitou esta redefinição, entre em contato imediatamente com os administradores do sistema."
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
            cta_url=f"{self.base_url}/login",
        )

        text = (
            f"Olá, {nome}.\n\n"
            f"Sua senha temporária no NaTrave 5v5 para a conta {username} é:\n"
            f"{senha_temporaria}\n\n"
            "Passos para utilizar:\n"
            f"1. Acesse {self.base_url}/login\n"
            f"2. Faça login com o usuário '{username}' e a senha temporária '{senha_temporaria}'\n"
            "3. Altere para sua nova senha no seu perfil.\n\n"
            "Por motivos de segurança, efetue a troca imediatamente."
        )
        return self.send_email(to_email, subject, html, text)

    def send_password_reset_email(self, to_email: str, nome: str, reset_url: str) -> EmailResult:
        subject = "Redefina sua senha no NaTrave 5v5"

        highlight_card_html = f"""
        <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
            <tr>
                <td style="background-color: #16161e; border: 1px solid #27272a; border-radius: 12px; padding: 18px 22px;">
                    <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 700; color: #a1a1aa; letter-spacing: 0.05em; text-transform: uppercase;">
                        🔗 Link de Redefinição
                    </p>
                    <p style="margin: 0; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 12px; color: #10b981; word-break: break-all;">
                        {reset_url}
                    </p>
                </td>
            </tr>
        </table>
        """

        steps = [
            ("1", "Clique no botão de acesso", "Clique em \"Acessar NaTrave\" abaixo ou acesse o link de redefinição exibido."),
            ("2", "Cadastre a nova senha", "Escolha uma nova senha forte com combinação de letras e números."),
            ("3", "Faça login com a nova senha", "Após salvar a alteração, faça seu login normalmente com as novas credenciais."),
        ]

        security_text = (
            "Este link de redefinição de senha é seguro e temporário. "
            "Se você não solicitou a redefinição de senha, fique tranquilo: nenhuma alteração foi realizada em sua conta."
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
            cta_url=reset_url,
        )

        text = (
            f"Olá, {nome}.\n\n"
            f"Use este link para redefinir sua senha no NaTrave 5v5:\n{reset_url}\n\n"
            "Se você não solicitou esta alteração, ignore este e-mail."
        )
        return self.send_email(to_email, subject, html, text)

    def send_reset_token_email(self, to_email: str, nome: str, token: str) -> EmailResult:
        """Compatibilidade com testes legados que passam token ao invés de URL pronta."""
        reset_url = f"{self.base_url}/definir-senha?token={token}"
        return self.send_password_reset_email(to_email=to_email, nome=nome, reset_url=reset_url)

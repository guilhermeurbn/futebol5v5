"""
Serviço de Mensagens Twilio (SMS e WhatsApp)
Envio de notificações automáticas de convocação, votação e partidas via Twilio API.
"""
import os
import logging
import requests
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class TwilioService:
    def __init__(self):
        self.account_sid = (os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
        self.auth_token = (os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("TWILIO_API_SECRET") or "").strip()
        self.api_key_sid = (os.getenv("TWILIO_API_KEY_SID") or "").strip()
        self.from_phone = (os.getenv("TWILIO_PHONE_NUMBER") or "").strip()
        self.from_whatsapp = (os.getenv("TWILIO_WHATSAPP_NUMBER") or "whatsapp:+14155238886").strip()

        # Define credenciais de autenticação
        if self.api_key_sid and self.auth_token:
            self.auth = (self.api_key_sid, self.auth_token)
        else:
            self.auth = (self.account_sid, self.auth_token)

    @property
    def is_configured(self) -> bool:
        """Retorna True se as credenciais do Twilio estiverem configuradas."""
        return bool(self.account_sid and self.auth_token)

    def _formatar_telefone(self, telefone: str, prefixo_pais: str = "+351") -> str:
        """Formata o número de telefone para o padrão E.164 (ex: +351912345678)."""
        num = "".join(c for c in str(telefone) if c.isdigit() or c == "+")
        if not num:
            return ""
        if not num.startswith("+"):
            num = f"{prefixo_pais}{num.lstrip('0')}"
        return num

    def enviar_sms(self, para_telefone: str, mensagem: str) -> bool:
        """Envia um SMS direto para o número de telefone informado."""
        if not self.is_configured:
            logger.warning("Twilio não configurado. Impossível enviar SMS.")
            return False

        destino = self._formatar_telefone(para_telefone)
        if not destino:
            logger.warning("Número de telefone de destino inválido: %s", para_telefone)
            return False

        if not self.from_phone:
            logger.warning("TWILIO_PHONE_NUMBER não configurado nas variáveis de ambiente.")
            return False

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "From": self.from_phone,
            "To": destino,
            "Body": mensagem
        }

        try:
            resp = requests.post(url, data=data, auth=self.auth, timeout=10)
            if resp.status_code in (200, 201):
                logger.info("SMS Twilio enviado com sucesso para %s", destino)
                return True
            logger.error("Erro Twilio SMS (%s): %s", resp.status_code, resp.text)
            return False
        except Exception as exc:
            logger.error("Exceção ao enviar SMS via Twilio para %s: %s", destino, exc)
            return False

    def enviar_whatsapp(self, para_telefone: str, mensagem: str) -> bool:
        """Envia uma mensagem via WhatsApp Sandbox / API oficial da Twilio."""
        if not self.is_configured:
            logger.warning("Twilio não configurado. Impossível enviar WhatsApp.")
            return False

        destino_num = self._formatar_telefone(para_telefone)
        if not destino_num:
            logger.warning("Número de telefone inválido para WhatsApp: %s", para_telefone)
            return False

        destino_wa = f"whatsapp:{destino_num}" if not destino_num.startswith("whatsapp:") else destino_num
        origem_wa = self.from_whatsapp if self.from_whatsapp.startswith("whatsapp:") else f"whatsapp:{self.from_whatsapp}"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "From": origem_wa,
            "To": destino_wa,
            "Body": mensagem
        }

        try:
            resp = requests.post(url, data=data, auth=self.auth, timeout=10)
            if resp.status_code in (200, 201):
                logger.info("WhatsApp Twilio enviado com sucesso para %s", destino_wa)
                return True
            logger.error("Erro Twilio WhatsApp (%s): %s", resp.status_code, resp.text)
            return False
        except Exception as exc:
            logger.error("Exceção ao enviar WhatsApp via Twilio para %s: %s", destino_wa, exc)
            return False

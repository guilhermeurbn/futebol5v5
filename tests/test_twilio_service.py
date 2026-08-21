"""
Testes unitários para o TwilioService (SMS e WhatsApp)
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from services.twilio_service import TwilioService


def test_twilio_not_configured():
    with patch.dict(os.environ, {}, clear=True):
        ts = TwilioService()
        assert not ts.is_configured
        assert not ts.enviar_sms("+351912345678", "Mensagem de teste")
        assert not ts.enviar_whatsapp("+351912345678", "Mensagem de teste")


def test_twilio_formatar_telefone():
    ts = TwilioService()
    assert ts._formatar_telefone("912345678") == "+351912345678"
    assert ts._formatar_telefone("+351912345678") == "+351912345678"
    assert ts._formatar_telefone("0912345678") == "+351912345678"


def test_twilio_enviar_sms_sucesso():
    env = {
        "TWILIO_ACCOUNT_SID": "DUMMY_TWILIO_ACCOUNT_SID_FOR_TESTING",
        "TWILIO_AUTH_TOKEN": "dummy_token_123456",
        "TWILIO_PHONE_NUMBER": "+12025550123"
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_post.return_value = mock_response

            ts = TwilioService()
            sucesso = ts.enviar_sms("912345678", "Ola do NaTrave!")
            assert sucesso
            assert mock_post.called
            args, kwargs = mock_post.call_args
            assert kwargs["data"]["To"] == "+351912345678"
            assert kwargs["data"]["From"] == "+12025550123"


def test_twilio_enviar_whatsapp_sucesso():
    env = {
        "TWILIO_ACCOUNT_SID": "DUMMY_TWILIO_ACCOUNT_SID_FOR_TESTING",
        "TWILIO_AUTH_TOKEN": "dummy_token_123456",
        "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886"
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_post.return_value = mock_response

            ts = TwilioService()
            sucesso = ts.enviar_whatsapp("912345678", "Votacao aberta no NaTrave!")
            assert sucesso
            assert mock_post.called
            args, kwargs = mock_post.call_args
            assert kwargs["data"]["To"] == "whatsapp:+351912345678"
            assert kwargs["data"]["From"] == "whatsapp:+14155238886"

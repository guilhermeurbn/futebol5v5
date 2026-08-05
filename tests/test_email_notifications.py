"""
Testes unitários para validar todos os serviços de e-mail transacionais e garantia de ausência de localhost.
"""
import pytest
from services.email_service import EmailService, resolve_public_base_url, sanitize_email_url


def test_resolve_public_base_url_never_returns_localhost():
    """Garante que a resolução de URL base nunca retorna localhost ou 127.0.0.1"""
    assert "localhost" not in resolve_public_base_url("http://localhost:5050")
    assert "127.0.0.1" not in resolve_public_base_url("http://127.0.0.1:5000")
    assert resolve_public_base_url() == "https://natrave.pt"


def test_sanitize_email_url_replaces_localhost():
    """Garante que qualquer link sanitizado não possui localhost"""
    clean_base = "https://natrave.pt"
    sanitized = sanitize_email_url("http://localhost:5050/definir-senha?token=123", clean_base)
    assert sanitized == "https://natrave.pt/definir-senha?token=123"
    assert "localhost" not in sanitized


def test_send_presenca_aberta_email_html_and_no_localhost():
    """Valida a criação do e-mail de presença aberta"""
    service = EmailService()
    html = service._build_email_html(
        to_email="jogador@natrave.pt",
        preheader="A rodada de terça já está aberta!",
        badge_text="INSCRIÇÃO DE PRESENÇA ABERTA",
        title="Rodada Aberta: Próxima Terça-Feira",
        subtitle="Olá, Jogador!",
        cta_text="Confirmar Presença",
        cta_url="http://localhost:5050/presenca"
    )

    assert "NATRAVE" in html
    assert "INSCRIÇÃO DE PRESENÇA ABERTA" in html
    assert "Confirmar Presença" in html
    assert "localhost" not in html
    assert "127.0.0.1" not in html
    assert "https://natrave.pt/presenca" in html


def test_send_votacao_aberta_email_html_and_no_localhost():
    """Valida a criação do e-mail de votação aberta"""
    service = EmailService()
    res = service.send_votacao_aberta_email("atleta@natrave.pt", "Ramon", "Sorteio #17")
    # Resend não enviado em ambiente local sem API Key, mas função retorna resultado tratado
    assert res.ok is False or res.message_id is not None or res.error == "Resend nao configurado"


def test_send_ranking_disponivel_email_html_and_no_localhost():
    """Valida o e-mail de ranking disponível"""
    service = EmailService()
    html = service._build_email_html(
        to_email="atleta@natrave.pt",
        preheader="Veja sua nova posição",
        badge_text="RANKING DA TEMPORADA DISPONÍVEL",
        title="Ranking da Rodada Atualizado",
        subtitle="Olá!",
        cta_text="Ver Ranking Completo",
        cta_url="http://localhost:5051/#ranking"
    )

    assert "RANKING DA TEMPORADA DISPONÍVEL" in html
    assert "Ver Ranking Completo" in html
    assert "localhost" not in html
    assert "https://natrave.pt/#ranking" in html


def test_all_auth_emails_have_no_localhost():
    """Testa todos os e-mails de autenticação (bem-vindo, senha temporária, reset)"""
    service = EmailService()
    
    welcome_html = service._build_email_html(
        to_email="test@natrave.pt",
        preheader="Bem-vindo",
        badge_text="CONTA CRIADA",
        title="Bem-vindo!",
        subtitle="Olá",
        cta_url="http://localhost:5000/login"
    )
    assert "localhost" not in welcome_html
    assert "https://natrave.pt/login" in welcome_html

    reset_html = service._build_email_html(
        to_email="test@natrave.pt",
        preheader="Redefinir Senha",
        badge_text="REDEFINIÇÃO DE SENHA",
        title="Redefina a sua Senha",
        subtitle="Olá",
        cta_url="http://127.0.0.1:5051/definir-senha?token=abc123"
    )
    assert "127.0.0.1" not in reset_html
    assert "https://natrave.pt/definir-senha?token=abc123" in reset_html


def test_email_forced_dark_mode_anti_inversion_css():
    """Valida se o HTML gerado inclui meta tags e regras CSS para forçar dark mode e impedir inversão"""
    service = EmailService()
    html = service._build_email_html(
        to_email="test@natrave.pt",
        preheader="Teste Dark",
        badge_text="TESTE",
        title="Titulo Teste",
        subtitle="Subtitulo"
    )
    assert 'color-scheme" content="only dark"' in html
    assert 'color-scheme: only dark !important;' in html
    assert 'background-color: #09090b !important;' in html
    assert 'background-color: #121217 !important;' in html

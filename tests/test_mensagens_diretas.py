"""
Testes automatizados para mensagens diretas estilo chat/WhatsApp entre jogadores.
"""
import pytest
from services.mensagem_service import MensagemService


def test_mensagem_service_enviar_e_listar():
    svc = MensagemService(arquivo="data/test_mensagens_temp.json")
    try:
        # Enviar mensagem Guilherme -> Lucas
        msg1 = svc.enviar_mensagem(
            remetente_id="1",
            remetente_nome="Guilherme",
            destinatario_id="2",
            destinatario_nome="Lucas",
            conteudo="Bora pro jogo terça-feira!"
        )

        assert msg1["id"] is not None
        assert msg1["remetente_nome"] == "Guilherme"

        # Verificar sinalizador de mensagens nao lidas para Lucas (ID 2)
        assert svc.tem_mensagens_nao_lidas("2") is True
        assert svc.tem_mensagens_nao_lidas("1") is False

        # Resposta Lucas -> Guilherme
        msg2 = svc.enviar_mensagem(
            remetente_id="2",
            remetente_nome="Lucas",
            destinatario_id="1",
            destinatario_nome="Guilherme",
            conteudo="Com certeza! Tamo junto!"
        )

        # Conversa cronológica (estilo chat WhatsApp)
        conversa = svc.obter_conversa_cronologica("1", "2")
        assert len(conversa) == 2
        assert conversa[0]["conteudo"] == "Bora pro jogo terça-feira!"
        assert conversa[1]["conteudo"] == "Com certeza! Tamo junto!"

        # Marcar mensagens de Lucas como lidas
        svc.marcar_como_lidas("2")
        assert svc.tem_mensagens_nao_lidas("2") is False

    finally:
        import os
        if os.path.exists("data/test_mensagens_temp.json"):
            os.remove("data/test_mensagens_temp.json")

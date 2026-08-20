"""
Teste de verificação para preservação do histórico de partidas e pontos
após alteração de nome, sobrenome ou username de um jogador.
"""
import pytest
import uuid
from services.auth_service import AuthService
from services.jogador_service import JogadorService, sincronizar_dados_e_partidas
from services.jogador_stats_service import JogadorStatsService
from services.partida_service import PartidaService
from services.db import load_json_data, save_json_data


def test_historico_preservado_apos_edicao_nome_username():
    auth_svc = AuthService()
    jog_svc = JogadorService()
    stats_svc = JogadorStatsService()
    partida_svc = PartidaService()

    # 1. Criar usuário e jogador inicial
    uniq = uuid.uuid4().hex[:6]
    email = f"atleta.{uniq}@teste.com"
    username_orig = f"atleta_orig_{uniq}"
    nome_orig = f"Atleta Orig{uniq} Sobrenome"

    u_data = auth_svc.criar_usuario(
        email=email,
        username=username_orig,
        nome=nome_orig,
        password="password123"
    )
    user_id = u_data["id"]

    # Obter ou criar o jogador vinculado ao usuário
    jogadores = jog_svc.listar_por_usuario(user_id)
    if not jogadores:
        jog_svc.criar(nome=nome_orig, nivel=7.0, owner_user_id=user_id)
        jogadores = jog_svc.listar_por_usuario(user_id)
    assert len(jogadores) >= 1
    jogador = jogadores[0]
    jogador_id = jogador.id

    # 2. Inserir uma partida com dados do jogador
    partidas = load_json_data("partidas", []) or []
    nova_partida_id = max((p.get("id", 0) for p in partidas if isinstance(p, dict)), default=0) + 1
    sorteio_id = 99990 + (nova_partida_id % 100)

    nova_partida = {
        "id": nova_partida_id,
        "sorteio_id": sorteio_id,
        "data": "2026-08-20T10:00:00",
        "time_vencedor": 1,
        "gols_times": [3, 1],
        "jogadores_detalhes": [
            {
                "nome": nome_orig,
                "user_id": user_id,
                "owner_user_id": user_id,
                "jogador_id": jogador_id,
                "gols": 2,
                "assistencias": 1,
                "cartoes_amarelos": 0,
                "cartoes_vermelhos": 0,
                "time_numero": 1,
                "posicao": "linha"
            }
        ]
    }
    partidas.append(nova_partida)
    save_json_data("partidas", partidas)
    stats_svc.invalidar_cache_stats()

    # Verificar estatísticas iniciais
    stats_orig = stats_svc.obter_stats_jogador(nome_orig, jogador_id=jogador_id, user_id=user_id)
    assert stats_orig["total_partidas"] == 1
    assert stats_orig["gols"] == 2
    assert stats_orig["assistencias"] == 1

    # 3. Alterar nome, sobrenome e username do usuário
    username_novo = f"atleta_novo_{uniq}"
    nome_novo = f"Atleta Editado{uniq} NovoNome"

    auth_svc.atualizar_perfil_usuario(
        user_id=user_id,
        username=username_novo,
        nome=nome_novo
    )

    # 4. Verificar se o histórico permanece 100% acessível pelo novo nome, jogador_id e user_id
    stats_novo = stats_svc.obter_stats_jogador(nome_novo, jogador_id=jogador_id, user_id=user_id)
    assert stats_novo["total_partidas"] == 1, "Histórico deve ser preservado após alteração de nome"
    assert stats_novo["gols"] == 2, "Gols devem ser mantidos"
    assert stats_novo["assistencias"] == 1, "Assistências devem ser mantidas"
    assert stats_novo["historico_partidas"][0]["partida_id"] == nova_partida_id

    # Limpeza da partida de teste criada
    partidas_atualizadas = [p for p in load_json_data("partidas", []) if p.get("id") != nova_partida_id]
    save_json_data("partidas", partidas_atualizadas)
    stats_svc.invalidar_cache_stats()

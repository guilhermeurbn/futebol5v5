import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.jogador_service import JogadorService
from services.auth_service import AuthService
from services.historico_service import HistoricoService
from services.votacao_service import VotacaoService


def test_sincronizar_jogador_avulso_com_usuario():
    # 1. Setup serviços
    jog_svc = JogadorService()
    auth_svc = AuthService()
    hist_svc = HistoricoService()
    vot_svc = VotacaoService()

    # 2. Criar jogador avulso com nível 7.5
    avulso = jog_svc.criar(
        nome="Luan 2 Teste",
        nivel=7.5,
        tipo="avulso",
        posicao="linha"
    )

    # 3. Criar usuário de destino (que cria automaticamente um jogador com nivel 5.5)
    usuario = auth_svc.criar_usuario(
        email="luan.teste@exemplo.com",
        username="luanteste",
        nome="Luan Silva",
        password="password123",
        role="usuario"
    )

    # 4. Criar sorteio no histórico com o jogador avulso
    sorteio_fake = {
        "id": 9999,
        "times": [
            {
                "numero": 1,
                "jogadores": [
                    {
                        "id": avulso.id,
                        "nome": avulso.nome,
                        "tipo": "avulso",
                        "owner_user_id": None
                    }
                ],
                "soma": 7.5
            }
        ]
    }
    historico_raw = hist_svc._carregar_raw()
    historico_raw.append(sorteio_fake)
    hist_svc._salvar(historico_raw)

    # 5. Criar partida no votacoes_partidas com participante externo
    vot_dados = vot_svc._carregar()
    vot_dados['partidas'].append({
        "id": 9999,
        "sorteio_id": 9999,
        "status": "aberta",
        "participantes": [
            {
                "user_id": None,
                "username": "",
                "nome_usuario": "",
                "jogador_nome": avulso.nome,
                "time_numero": 1,
                "externo": True
            }
        ],
        "times": sorteio_fake["times"]
    })
    vot_svc._salvar(vot_dados)

    # 6. Executar sincronização
    resultado = jog_svc.sincronizar_jogador_avulso(
        jogador_avulso_id=avulso.id,
        usuario_destino_id=usuario['id']
    )

    assert resultado['sucesso'] is True
    assert resultado['nome_avulso'] == "Luan 2 Teste"

    # 7. Verificar se o sorteio no histórico foi atualizado
    sorteio_atualizado = hist_svc.obter_sorteio(9999)
    assert sorteio_atualizado is not None
    j_sorteio = sorteio_atualizado['times'][0]['jogadores'][0]
    assert j_sorteio['nome'] == "Luan Silva"
    assert j_sorteio['owner_user_id'] == usuario['id']
    assert j_sorteio['tipo'] == "fixo"

    # 8. Verificar se a nota 7.5 do avulso foi transferida para o perfil do usuário
    j_usuario = jog_svc.obter_por_id(resultado['target_jogador_id'])
    assert j_usuario is not None
    assert float(j_usuario.nivel) == 7.5

    # 9. Verificar se o usuário agora tem permissão para votar na partida aberta
    partida_votacao = vot_svc.obter_partida(9999)
    assert partida_votacao is not None
    part_user = next((p for p in partida_votacao['participantes'] if p['user_id'] == usuario['id']), None)
    assert part_user is not None
    assert part_user['externo'] is False
    assert part_user['jogador_nome'] == "Luan Silva"

    # Cleanup: remover dados de teste
    try:
        jog_svc.deletar(resultado['target_jogador_id'])
    except Exception:
        pass
    try:
        auth_svc.deletar_usuario(usuario['id'])
    except Exception:
        pass
    hist_svc.deletar_sorteio(9999)
    vot_dados = vot_svc._carregar()
    vot_dados['partidas'] = [p for p in vot_dados['partidas'] if p.get('id') != 9999]
    vot_svc._salvar(vot_dados)

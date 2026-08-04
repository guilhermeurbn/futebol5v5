import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.jogador_service import JogadorService
from services.auth_service import AuthService
from services.historico_service import HistoricoService
from services.partida_service import PartidaService


def test_sincronizar_jogador_avulso_com_usuario():
    # 1. Setup serviços
    jog_svc = JogadorService()
    auth_svc = AuthService()
    hist_svc = HistoricoService()

    # 2. Criar jogador avulso
    avulso = jog_svc.criar(
        nome="Luan 2 Teste",
        nivel=6.0,
        tipo="avulso",
        posicao="linha"
    )

    # 3. Criar usuário de destino
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
                "soma": 6
            }
        ]
    }
    historico_raw = hist_svc._carregar_raw()
    historico_raw.append(sorteio_fake)
    hist_svc._salvar(historico_raw)

    # 5. Executar sincronização
    resultado = jog_svc.sincronizar_jogador_avulso(
        jogador_avulso_id=avulso.id,
        usuario_destino_id=usuario['id']
    )

    assert resultado['sucesso'] is True
    assert resultado['nome_avulso'] == "Luan 2 Teste"

    # 6. Verificar se o sorteio no histórico foi atualizado
    sorteio_atualizado = hist_svc.obter_sorteio(9999)
    assert sorteio_atualizado is not None
    j_sorteio = sorteio_atualizado['times'][0]['jogadores'][0]
    assert j_sorteio['nome'] == "Luan Silva"
    assert j_sorteio['owner_user_id'] == usuario['id']
    assert j_sorteio['tipo'] == "fixo"

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

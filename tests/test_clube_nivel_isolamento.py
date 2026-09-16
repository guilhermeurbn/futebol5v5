"""
Testes unitários para o isolamento de nível / habilidade dos jogadores por clube.
"""

import pytest
from services.jogador_service import JogadorService


@pytest.fixture
def clean_jogador_service(monkeypatch):
    """Fixture que limpa o armazenamento de jogadores em memória"""
    storage = {"jogadores": []}

    def fake_load(namespace, default):
        if namespace == "jogadores":
            return storage["jogadores"]
        return default

    def fake_save(namespace, payload):
        if namespace == "jogadores":
            storage["jogadores"] = payload

    monkeypatch.setattr("services.jogador_service.load_json_data", fake_load)
    monkeypatch.setattr("services.jogador_service.save_json_data", fake_save)

    svc = JogadorService()
    return svc, storage


def test_nivel_padrao_no_clube_001(clean_jogador_service):
    """Garante que no Clube 001 (NaTrave) o nível retornado é o nível base do jogador (ex: 8.0)"""
    svc, storage = clean_jogador_service
    j = svc.criar(nome="Guilherme Urbano", nivel=8.0)
    j_dict = j.para_dict()

    # No Clube 001 retorna 8.0
    n_001 = JogadorService.obter_nivel_no_clube(j_dict, "001")
    assert n_001 == 8.0


def test_nivel_inicial_padrao_em_novo_clube(clean_jogador_service):
    """Garante que ao entrar em um novo clube (ex: 002) o nível inicial seja 5.5 por padrão"""
    svc, storage = clean_jogador_service
    j = svc.criar(nome="Guilherme Urbano", nivel=8.0)
    j_dict = j.para_dict()

    # No Clube 002 (sem configuração prévia) retorna 5.5
    n_002 = JogadorService.obter_nivel_no_clube(j_dict, "002")
    assert n_002 == 5.5


def test_atualizacao_nivel_isolada_por_clube(clean_jogador_service):
    """Testa se alterar a nota no Clube 002 (para 6.5) altera apenas no Clube 002, mantendo 8.0 no Clube 001"""
    svc, storage = clean_jogador_service
    j = svc.criar(nome="Guilherme Urbano", nivel=8.0)

    # Alterar nota do Guilherme apenas no Clube 002
    j_atualizado = svc.atualizar_nivel_no_clube(j.id, "002", 6.5)
    assert j_atualizado is not None

    # Verificar que no Clube 002 agora é 6.5
    assert JogadorService.obter_nivel_no_clube(j_atualizado, "002") == 6.5

    # Verificar que no Clube 001 continua sendo 8.0 intacto
    assert JogadorService.obter_nivel_no_clube(j_atualizado, "001") == 8.0

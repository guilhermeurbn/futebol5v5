"""
Testes unitários automatizados para isolamento de banco de dados e cache por clube.
Valida que operações em um clube (ex: 002) não interferem em outro (ex: 001).
"""

import pytest
from services.db import (
    load_json_data,
    save_json_data,
    clear_db_cache,
    resolver_namespace_clube,
    _cache,
)


@pytest.fixture(autouse=True)
def limpar_cache_antes_depois():
    clear_db_cache()
    yield
    clear_db_cache()


def test_resolver_namespace_globais():
    """Namespaces de usuário e clubes devem permanecer sempre globais."""
    assert resolver_namespace_clube("users", "001") == "users"
    assert resolver_namespace_clube("users", "002") == "users"
    assert resolver_namespace_clube("clubes", "002") == "clubes"
    assert resolver_namespace_clube("image_assets", "003") == "image_assets"


def test_resolver_namespace_clube_001():
    """Clube 001 mantém namespace padrão original para retrocompatibilidade."""
    assert resolver_namespace_clube("partidas", "001") == "partidas"
    assert resolver_namespace_clube("historico", "001") == "historico"
    assert resolver_namespace_clube("presencas", "001") == "presencas"
    assert resolver_namespace_clube("votacoes_partidas", "001") == "votacoes_partidas"


def test_resolver_namespace_novos_clubes():
    """Novos clubes (002, 003...) recebem namespace particionado e isolado."""
    assert resolver_namespace_clube("partidas", "002") == "clube_002_partidas"
    assert resolver_namespace_clube("historico", "002") == "clube_002_historico"
    assert resolver_namespace_clube("presencas", "003") == "clube_003_presencas"
    assert resolver_namespace_clube("votacoes_partidas", "002") == "clube_002_votacoes_partidas"


def test_isolamento_gravacao_e_leitura_partidas():
    """
    Gravar partidas no Clube 002 não pode alterar as partidas do Clube 001.
    """
    partidas_001 = [{"id": 1, "titulo": "Final NaTrave 001"}]
    partidas_002 = [{"id": 99, "titulo": "Estreia Clube 002"}]

    save_json_data("test_partidas", partidas_001, clube_codigo="001")
    save_json_data("test_partidas", partidas_002, clube_codigo="002")

    lidas_001 = load_json_data("test_partidas", [], clube_codigo="001")
    lidas_002 = load_json_data("test_partidas", [], clube_codigo="002")

    assert len(lidas_001) == 1
    assert lidas_001[0]["titulo"] == "Final NaTrave 001"

    assert len(lidas_002) == 1
    assert lidas_002[0]["titulo"] == "Estreia Clube 002"


def test_isolamento_cache_em_memoria():
    """
    O cache em memória deve ter chaves independentes para cada clube.
    Modificar o Clube 002 não afeta a chave do Clube 001.
    """
    save_json_data("test_historico", [{"id": 1}], clube_codigo="001")
    save_json_data("test_historico", [{"id": 2}], clube_codigo="002")

    # Ambas devem estar em chaves separadas no _cache
    assert "test_historico" in _cache
    assert "clube_002_test_historico" in _cache

    # Atualizar Clube 002
    save_json_data("test_historico", [{"id": 20}], clube_codigo="002")

    # Clube 001 deve permanecer inalterado
    cache_001 = load_json_data("test_historico", [], clube_codigo="001")
    assert cache_001[0]["id"] == 1

    cache_002 = load_json_data("test_historico", [], clube_codigo="002")
    assert cache_002[0]["id"] == 20

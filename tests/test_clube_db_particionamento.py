"""
Testes unitários automatizados para isolamento de banco de dados e cache por clube.
Valida que:
1. Todos os clubes (incluindo 001) seguem a convenção padronizada clube_{codigo}_{namespace}.
2. O namespace de jogadores é isolado por clube (clube_001_jogadores, clube_002_jogadores).
3. Existe fallback transparente de leitura para o Clube 001 para dados legados não-prefixados.
4. Operações em um clube (ex: 002) não interferem em outro (ex: 001).
"""

import os
import glob
import pytest
from services.db import (
    load_json_data,
    save_json_data,
    clear_db_cache,
    resolver_namespace_clube,
    _cache,
    _repo_root,
)
from services.jogador_service import JogadorService


@pytest.fixture(autouse=True)
def limpar_cache_antes_depois():
    clear_db_cache()
    yield
    clear_db_cache()
    data_dir = _repo_root() / "data"
    for f in glob.glob(str(data_dir / "*test_*")):
        try:
            os.remove(f)
        except OSError:
            pass


def test_resolver_namespace_globais():
    """Namespaces de usuário, catálogo de clubes e mídias devem permanecer sempre globais."""
    assert resolver_namespace_clube("users", "001") == "users"
    assert resolver_namespace_clube("users", "002") == "users"
    assert resolver_namespace_clube("clubes", "002") == "clubes"
    assert resolver_namespace_clube("image_assets", "003") == "image_assets"
    assert resolver_namespace_clube("admin_notificacoes", "001") == "admin_notificacoes"


def test_resolver_namespace_clube_001_padronizado():
    """Clube 001 agora segue a mesma convenção padronizada de todos os outros clubes."""
    assert resolver_namespace_clube("partidas", "001") == "clube_001_partidas"
    assert resolver_namespace_clube("jogadores", "001") == "clube_001_jogadores"
    assert resolver_namespace_clube("historico", "001") == "clube_001_historico"
    assert resolver_namespace_clube("presencas", "001") == "clube_001_presencas"
    assert resolver_namespace_clube("votacoes_partidas", "001") == "clube_001_votacoes_partidas"


def test_resolver_namespace_novos_clubes():
    """Novos clubes (002, 003...) recebem namespace particionado e isolado."""
    assert resolver_namespace_clube("partidas", "002") == "clube_002_partidas"
    assert resolver_namespace_clube("jogadores", "002") == "clube_002_jogadores"
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
    assert "clube_001_test_historico" in _cache
    assert "clube_002_test_historico" in _cache

    # Atualizar Clube 002
    save_json_data("test_historico", [{"id": 20}], clube_codigo="002")

    # Clube 001 deve permanecer inalterado
    cache_001 = load_json_data("test_historico", [], clube_codigo="001")
    assert cache_001[0]["id"] == 1

    cache_002 = load_json_data("test_historico", [], clube_codigo="002")
    assert cache_002[0]["id"] == 20


def test_fallback_transparente_leitura_legado_001():
    """
    Se o arquivo/registro clube_001_test_fallback não existir, mas o arquivo legado test_fallback.json existir,
    o sistema deve ler o dado legado automaticamente com fallback.
    """
    data_dir = _repo_root() / "data"
    legado_file = data_dir / "test_fallback_legado.json"
    import json
    with open(legado_file, "w", encoding="utf-8") as f:
        json.dump([{"legado": True, "valor": 42}], f)

    clear_db_cache()
    # Solicitar com clube_codigo="001"
    resultado = load_json_data("test_fallback_legado", [], clube_codigo="001")
    assert len(resultado) == 1
    assert resultado[0]["legado"] is True
    assert resultado[0]["valor"] == 42


def test_isolamento_jogadores_por_clube():
    """
    Valida que JogadorService isola jogadores entre o Clube 001 e o Clube 002.
    """
    import uuid
    uid = uuid.uuid4().hex[:6]
    nome_001 = f"Artilheiro 001 {uid}"
    nome_002 = f"Zagueiro 002 {uid}"

    svc = JogadorService()
    clear_db_cache()

    # Criar atleta no Clube 001
    j1 = svc.criar(nome=nome_001, nivel=9.0, tipo="fixo", clube_codigo="001")
    # Criar atleta no Clube 002
    j2 = svc.criar(nome=nome_002, nivel=6.5, tipo="avulso", clube_codigo="002")

    lista_001 = svc.listar(clube_codigo="001")
    lista_002 = svc.listar(clube_codigo="002")

    nomes_001 = [j.nome for j in lista_001]
    nomes_002 = [j.nome for j in lista_002]

    assert nome_001 in nomes_001
    assert nome_002 not in nomes_001

    assert nome_002 in nomes_002
    assert nome_001 not in nomes_002

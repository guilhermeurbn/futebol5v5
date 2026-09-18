"""
Testes unitários para o ClubeService (Identificação 001, 002..., unicidade de nomes e schemas Pydantic).
"""

import pytest
from services.clube_service import (
    formatar_id_clube,
    normalizar_texto,
    gerar_slug,
    ClubeSchema,
    ClubeService
)


@pytest.fixture(autouse=True)
def setup_clean_db(monkeypatch):
    """Garante um armazenamento em memória limpo antes de cada teste de clube"""
    storage = {"clubes": []}

    def fake_load(namespace, default=None, *args, **kwargs):
        if namespace == "clubes":
            return storage["clubes"]
        return default

    def fake_save(namespace, payload, *args, **kwargs):
        if namespace == "clubes":
            storage["clubes"] = payload

    monkeypatch.setattr("services.clube_service.load_json_data", fake_load)
    monkeypatch.setattr("services.clube_service.save_json_data", fake_save)


def test_formatar_id_clube_regras():
    """Testa a regra de formatação dos IDs dos clubes: 001 a 999 -> 3 dígitos; 1000+ -> sem corte"""
    assert formatar_id_clube(1) == "001"
    assert formatar_id_clube(2) == "002"
    assert formatar_id_clube(42) == "042"
    assert formatar_id_clube(999) == "999"
    assert formatar_id_clube(1000) == "1000"
    assert formatar_id_clube(1001) == "1001"


def test_normalizar_texto_e_slug():
    """Testa remoção de acentos e geração de slugs amigáveis de URL"""
    assert normalizar_texto("NaTrave Futebol") == "natrave futebol"
    assert normalizar_texto("São Paulo FC") == "sao paulo fc"
    assert gerar_slug("NaTrave 5v5!") == "natrave-5v5"
    assert gerar_slug("Clube  dos   Amigos") == "clube-dos-amigos"


def test_pydantic_schema_validacao():
    """Testa a validação estrita com Pydantic para ClubeSchema"""
    clube = ClubeSchema(id_num=1, nome="NaTrave", slug="natrave")
    assert clube.codigo_formatado == "001"
    assert clube.nome == "NaTrave"

    with pytest.raises(Exception):
        ClubeSchema(id_num=2, nome="A", slug="a")


def test_garantir_clube_natrave_001():
    """Testa se o Clube 001 (NaTrave) é criado automaticamente com ID 1 ('001')"""
    clube_001 = ClubeService.garantir_clube_natrave_001()
    assert clube_001["id_num"] == 1
    assert clube_001["codigo_formatado"] == "001"
    assert clube_001["nome"] == "NaTrave"
    assert clube_001["slug"] == "natrave"


def test_criar_novos_clubes_sequenciais():
    """Testa a criação de múltiplos clubes com IDs sequenciais (001, 002, 003...)"""
    c1 = ClubeService.garantir_clube_natrave_001()
    assert c1["codigo_formatado"] == "001"

    c2 = ClubeService.criar_clube("Pelada das Quintas")
    assert c2["id_num"] == 2
    assert c2["codigo_formatado"] == "002"
    assert c2["slug"] == "pelada-das-quintas"

    c3 = ClubeService.criar_clube("Futebol & Resenha")
    assert c3["id_num"] == 3
    assert c3["codigo_formatado"] == "003"


def test_unicidade_estrita_de_nome():
    """Garante que não seja permitido criar dois clubes com o mesmo nome (mesmo variando caixa/acentos)"""
    ClubeService.garantir_clube_natrave_001()
    ClubeService.criar_clube("Amigos da Bola")

    with pytest.raises(ValueError) as exc_info:
        ClubeService.criar_clube("amigos da bola")
    assert "já existe um clube cadastrado" in str(exc_info.value).lower()

    with pytest.raises(ValueError):
        ClubeService.criar_clube("Ámigos dá Bolá")


def test_busca_clube_por_codigo_e_slug():
    """Testa métodos de busca por código ('001', '002') e por slug ('natrave')"""
    ClubeService.garantir_clube_natrave_001()
    c2 = ClubeService.criar_clube("Liga dos Campeões", slug="liga-campeoes")

    b1 = ClubeService.obter_clube_por_codigo("001")
    assert b1 is not None
    assert b1["nome"] == "NaTrave"

    b2 = ClubeService.obter_clube_por_codigo("002")
    assert b2 is not None
    assert b2["nome"] == "Liga dos Campeões"

    b_slug = ClubeService.obter_clube_por_slug("liga-campeoes")
    assert b_slug is not None
    assert b_slug["id_num"] == 2


def test_id_forte_clube_e_codigo_amigavel():
    """Testa se cada clube recebe um ID forte único (clb_...) e mantém o código amigável (001, 002...)"""
    c1 = ClubeService.garantir_clube_natrave_001()
    assert c1["id"] == ClubeService.ID_FORTE_NATRAVE_001
    assert c1["codigo_formatado"] == "001"

    c2 = ClubeService.criar_clube("Clube Alfa")
    assert c2["id"].startswith("clb_")
    assert c2["codigo_formatado"] == "002"
    assert c2["id"] != c1["id"]

    c3 = ClubeService.criar_clube("Clube Beta")
    assert c3["id"].startswith("clb_")
    assert c3["codigo_formatado"] == "003"
    assert c3["id"] != c2["id"]


def test_busca_por_id_forte_ou_codigo():
    """Testa busca unificada por ID forte e por código público amigável"""
    ClubeService.garantir_clube_natrave_001()
    c2 = ClubeService.criar_clube("Clube Especial")
    id_forte = c2["id"]

    # Busca por ID forte
    busca_forte = ClubeService.obter_clube_por_id_forte(id_forte)
    assert busca_forte is not None
    assert busca_forte["nome"] == "Clube Especial"
    assert busca_forte["codigo_formatado"] == "002"

    # Busca genérica via obter_clube_por_id usando ID forte
    busca_gen = ClubeService.obter_clube_por_id(id_forte)
    assert busca_gen is not None
    assert busca_gen["id"] == id_forte

    # Busca via obter_clube_por_codigo usando ID forte
    busca_cod = ClubeService.obter_clube_por_codigo(id_forte)
    assert busca_cod is not None
    assert busca_cod["id"] == id_forte

    # Busca pelo código numérico e amigável
    busca_num = ClubeService.obter_clube_por_id(2)
    assert busca_num is not None
    assert busca_num["id"] == id_forte

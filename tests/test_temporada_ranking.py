import pytest
import os
import tempfile
from datetime import datetime
from services.temporada_service import TemporadaService
from services.votacao_service import VotacaoService


@pytest.fixture
def temp_temporada_service():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    service = TemporadaService(data_file=temp_path)
    yield service
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_temporada_service_initialization_and_metrics(temp_temporada_service):
    """Testa que a Temporada #1 e configurada corretamente com datas, contagem e duracao"""
    ativa = temp_temporada_service.obter_temporada_ativa()

    assert ativa["id"] == 1
    assert "Temporada #1" in ativa["nome"]
    assert ativa["data_inicio_fmt"] == "01/07/2026"
    assert ativa["data_fim_fmt"] == "04/10/2026"
    assert "1º Lugar" in ativa["descricao_premio"]


def test_ranking_jogadores_geral_date_filter(monkeypatch):
    """Testa que o ranking filtra corretamente partidas dentro do intervalo de datas da temporada"""
    service = VotacaoService(arquivo="data/votacoes_partidas.json")

    partidas_mock = [
        {
            "id": 1,
            "status": "encerrada",
            "data": "2026-07-15T12:00:00",  # Antes da temporada
            "participantes": [{"jogador_nome": "Alex", "time_numero": 1}],
            "votos": [{"user_id": "u1", "votos": [{"jogador_nome": "Alex", "nota": 10.0}]}]
        },
        {
            "id": 2,
            "status": "encerrada",
            "data": "2026-08-10T12:00:00",  # DENTRO da temporada (04/08 a 04/10)
            "participantes": [{"jogador_nome": "Bruno", "time_numero": 1}],
            "votos": [{"user_id": "u1", "votos": [{"jogador_nome": "Bruno", "nota": 9.0}]}]
        }
    ]

    monkeypatch.setattr(service, 'listar', lambda *args, **kwargs: partidas_mock)

    # Filtrar no periodo da temporada #1
    resultado_temporada = service.ranking_jogadores_geral(
        limite=50,
        data_inicio="2026-08-04T00:00:00",
        data_fim="2026-10-04T23:59:59"
    )

    # Apenas Bruno deve estar no ranking da temporada
    jogadores_temp = [j["jogador_nome"] for j in resultado_temporada["ranking"]]
    assert "Bruno" in jogadores_temp
    assert "Alex" not in jogadores_temp
    assert resultado_temporada["total_partidas"] == 1


def test_pagina_ranking_com_temporada(monkeypatch):
    """Testa renderizacao da pagina de ranking com parametro tipo=temporada e tipo=geral"""
    from app import app
    with app.test_client() as client:
        res_temp = client.get('/ranking?tipo=temporada')
        assert res_temp.status_code == 200
        body_temp = res_temp.get_data(as_text=True)
        assert 'COMPETIÇÃO OFICIAL DA TEMPORADA' in body_temp
        assert 'Temporada #1' in body_temp
        assert '01/07/2026' in body_temp
        assert '04/10/2026' in body_temp

        res_geral = client.get('/ranking?tipo=geral')
        assert res_geral.status_code == 200
        body_geral = res_geral.get_data(as_text=True)
        assert 'Ranking Histórico Geral' in body_geral


def test_novo_clube_inicia_sem_competicao_ativa(temp_temporada_service):
    """Testa que um novo clube (ex: '002') inicia zerado, sem competição ativa"""
    ativa_001 = temp_temporada_service.obter_temporada_ativa(clube_codigo="001")
    assert ativa_001.get("id") == 1
    assert "Temporada #1" in ativa_001.get("nome", "")

    # Novo clube 002 não deve ter competição ativa
    ativa_002 = temp_temporada_service.obter_temporada_ativa(clube_codigo="002")
    assert ativa_002 == {}


def test_novo_clube_abrir_competicao_isolada(temp_temporada_service):
    """Testa que abrir competição em um novo clube não afeta o clube 001"""
    # 1. Abre competição no clube 002
    nova = temp_temporada_service.abrir_nova_competicao(
        nome="Liga de Estreia 002",
        tipo_duracao="meses",
        valor_duracao=2,
        clube_codigo="002"
    )
    assert nova.get("nome") == "Liga de Estreia 002"

    # 2. Confirma que clube 002 tem a nova competição
    ativa_002 = temp_temporada_service.obter_temporada_ativa(clube_codigo="002")
    assert ativa_002.get("nome") == "Liga de Estreia 002"

    # 3. Confirma que clube 001 continua com a Temporada #1 original
    ativa_001 = temp_temporada_service.obter_temporada_ativa(clube_codigo="001")
    assert ativa_001.get("id") == 1
    assert "Temporada #1" in ativa_001.get("nome", "")


def test_pagina_ranking_novo_clube_inicia_zerado(monkeypatch):
    """Testa que a página de ranking para um novo clube exibe 'Nenhuma competição ativa' e não exibe a Temporada #1"""
    from services.clube_service import ClubeService
    monkeypatch.setattr(
        ClubeService,
        'obter_clube_por_codigo',
        lambda cod: {'codigo_formatado': '999', 'slug': 'clube-novo', 'nome': 'Clube Novo'} if str(cod) == '999' else None
    )
    monkeypatch.setattr(
        ClubeService,
        'obter_clube_por_slug',
        lambda slug: {'codigo_formatado': '999', 'slug': 'clube-novo', 'nome': 'Clube Novo'} if slug == 'clube-novo' else None
    )
    from app import app
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['clube_codigo'] = '999'
            sess['clube_slug'] = 'clube-novo'

        res = client.get('/ranking?tipo=temporada')
        assert res.status_code == 200
        body = res.get_data(as_text=True)
        assert 'Nenhuma competição ativa' in body
        assert 'Temporada #1 - Edição de Prêmios' not in body
        assert '01/07/2026' not in body


def test_excluir_competicao_ativa(temp_temporada_service):
    """Testa que excluir_competicao_ativa zera a temporada ativa do clube"""
    # 1. Abre uma competição para teste
    temp_temporada_service.abrir_nova_competicao(
        nome="Liga Para Apagar",
        tipo_duracao="meses",
        valor_duracao=1,
        clube_codigo="003"
    )
    assert temp_temporada_service.obter_temporada_ativa(clube_codigo="003").get("nome") == "Liga Para Apagar"

    # 2. Exclui a competição ativa
    sucesso = temp_temporada_service.excluir_competicao_ativa(clube_codigo="003")
    assert sucesso is True

    # 3. Deve voltar a ficar zerada
    assert temp_temporada_service.obter_temporada_ativa(clube_codigo="003") == {}


def test_api_competicao_excluir_endpoint(monkeypatch):
    """Testa endpoint POST /api/competicao/excluir com permissões"""
    from app import app
    old_csrf = app.config.get('WTF_CSRF_ENABLED', True)
    app.config['WTF_CSRF_ENABLED'] = False
    try:
        with app.test_client() as client:
            # 1. Sem login / não-admin deve retornar 401, 403 ou redirecionar
            res_nao_logado = client.post('/api/competicao/excluir')
            assert res_nao_logado.status_code in [302, 401, 403]

            # 2. Como usuário comum (não admin) -> deve retornar 403
            with client.session_transaction() as sess:
                sess['user_id'] = 'user_comum'
                sess['role'] = 'usuario'
                sess['clube_codigo'] = '001'

            res_comum = client.post('/api/competicao/excluir')
            assert res_comum.status_code == 403

            # 3. Como admin -> deve retornar 200 e sucesso
            with client.session_transaction() as sess:
                sess['user_id'] = 'admin_001'
                sess['role'] = 'admin'
                sess['clube_codigo'] = '001'

            res_admin = client.post('/api/competicao/excluir')
            assert res_admin.status_code == 200
            dados = res_admin.get_json()
            assert dados['sucesso'] is True
    finally:
        app.config['WTF_CSRF_ENABLED'] = old_csrf


def test_ranking_html_tem_opcao_apagar_e_dupla_confirmacao():
    """Valida que o template ranking.html possui o botão 'Apagar sorteio' e o modal de dupla confirmação"""
    with open('templates/ranking.html', 'r', encoding='utf-8') as f:
        conteudo = f.read()

    assert 'Apagar sorteio' in conteudo
    assert 'modalConfirmarExclusaoCompeticao' in conteudo
    assert 'etapaExclusao1' in conteudo
    assert 'etapaExclusao2' in conteudo
    assert 'Quero apagar' in conteudo
    assert 'Sim, apagar mesmo' in conteudo
    assert 'submeterExclusaoDefinitiva()' in conteudo


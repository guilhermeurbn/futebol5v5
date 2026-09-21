import os
import pytest
from app import app

@pytest.fixture
def judge_client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    from services.juiz_partida_service import JuizPartidaService
    jps = JuizPartidaService()
    jps._salvar(jps._estado_vazio(), '001')
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'juiz_oficial'
            sess['role'] = 'juiz'
            sess['clube_id'] = 1
            sess['clube_codigo'] = '001'
        yield c

def test_juiz_tour_assets_rendered(judge_client):
    """Verifica se os assets do tour do juiz e os IDs de navegação estão no HTML"""
    res = judge_client.get('/jogar', follow_redirects=True)
    assert res.status_code == 200
    html = res.data.decode('utf-8')

    # Assets CSS e JS
    assert 'juiz-tour.css' in html
    assert 'juiz-tour.js' in html

    # IDs do rodapé para o highlight interativo do tour
    assert 'id="tourJuizTabCriar"' in html
    assert 'id="tourJuizTabTimes"' in html
    assert 'id="tourJuizTabVotacoes"' in html
    assert 'id="tourJuizTabHistorico"' in html
    assert 'id="tourJuizTabCronometro"' in html
    assert 'id="tourJuizTabSair"' in html

    # Botão de disparo único no topo do painel do juiz
    assert 'judge-tour-pill-btn' in html
    assert 'iniciarJuizTour' in html
    assert 'Tour pelo Juiz' in html

def test_juiz_criar_partida_tem_botao_voltar(judge_client):
    """Verifica se a tela de escolha de quantidade possui o botão de voltar ao painel inicial e volta de fato"""
    res = judge_client.get('/jogar/criar-partida?novo=1')
    assert res.status_code == 200
    html = res.data.decode('utf-8')
    assert 'Voltar ao Painel do Juiz' in html or 'Voltar ao Início' in html
    assert 'btnVoltarPainelJuiz' in html
    assert 'Trocar quantidade' in html

    # Clica no link de voltar (cancelar seleção)
    res_voltar = judge_client.get('/jogar/cancelar-selecao', follow_redirects=True)
    assert res_voltar.status_code == 200
    html_home = res_voltar.data.decode('utf-8')
    assert 'judge-start-card' in html_home
    assert 'judge-tour-pill-btn' in html_home

def test_juiz_tour_simulator_content():
    """Verifica se o simulador contém os 20 jogadores fictícios e as etapas de clique solicitadas"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    js_path = os.path.join(base_dir, 'static', 'juiz-tour.js')
    css_path = os.path.join(base_dir, 'static', 'juiz-tour.css')

    assert os.path.exists(js_path), "juiz-tour.js deve existir em static/"
    assert os.path.exists(css_path), "juiz-tour.css deve existir em static/"

    with open(js_path, 'r', encoding='utf-8') as f:
        js_content = f.read()

    # Verifica os 20 jogadores fictícios
    assert 'JOGADORES_FICTICIOS' in js_content
    assert 'Gabriel Costa' in js_content
    assert 'Bruno Rocha' in js_content
    assert 'Thiago Neves' in js_content
    assert 'Danilo Alcantara' in js_content
    assert 'Renan Pires' in js_content

    # Verifica as etapas interativas do simulador
    assert 'TOTAL_STEPS = 8' in js_content
    assert 'Selecionar jogadores' in js_content
    assert 'Sortear' in js_content
    assert 'sim-btn-sortear' in js_content
    assert 'Times Sorteados' in js_content
    assert 'sim-btn-edit-teams' in js_content
    assert 'btnSimCopiar' in js_content
    assert 'Copiar' in js_content
    assert 'Iniciar Rodada' in js_content
    assert 'Registro de Resultados' in js_content
    assert 'Abrir Votação' in js_content
    assert 'Encerrar Votação' in js_content
    assert 'Encerrar Partida' in js_content
    assert 'Exemplo no Histórico' in js_content
    assert 'sim-history-demo-card' in js_content
    assert 'Partida #14' in js_content
    assert 'Time Campeão' in js_content
    assert 'sim-champion-player-tag' in js_content
    assert 'Cronômetro da Partida' in js_content
    assert 'sim-timer-box' in js_content
    assert 'sim-timer-display' in js_content
    assert 'btnTimerToggle' in js_content
    assert 'tourJuizTabVotacoes' in js_content
    assert 'tourJuizTabHistorico' in js_content
    assert 'tourJuizTabCronometro' in js_content
    assert 'tourJuizTabSair' in js_content
    assert 'interceptarCliqueAbas' in js_content
    assert 'btnVoltarEtapa1' in js_content
    assert 'btnVoltarEtapa2' in js_content
    assert 'window.iniciarJuizTour' in js_content

    with open(css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()

    # Verifica design limpo, sem sombras difusas
    assert '#juizTourOverlay' in css_content
    assert '#juizTourCard' in css_content
    assert 'box-shadow: none !important;' in css_content
    assert '.juiz-tour-step-mini' in css_content
    assert '.juiz-tour-btn-skip' in css_content
    assert '.sim-btn-edit-teams' in css_content
    assert '.sim-team-actions-compact-row' in css_content
    assert '.sim-history-demo-card' in css_content
    assert '.sim-champion-player-tag' in css_content
    assert '.sim-timer-box' in css_content


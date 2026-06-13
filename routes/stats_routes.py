"""
Rotas de Estatísticas, Rankings e Exportação
- Stats por jogador, times, combos
- Exportação em CSV, TXT, PDF
- Sugestões inteligentes
- Rankings gerais
"""
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, session, send_file, Response
from functools import wraps
import io
import logging

from routes.commons import login_required
from services.stats_service import StatsService
from services.historico_service import HistoricoService
from services.export_service import ExportService
from services.sugestoes_service import SugestoesService
from services.ranking_service import RankingService
from services.votacao_service import VotacaoService
from services.jogador_service import JogadorService

stats_bp = Blueprint('stats', __name__)
logger = logging.getLogger(__name__)

stats_service = StatsService()
historico_service = HistoricoService()
export_service = ExportService()
sugestoes_service = SugestoesService()
ranking_service = RankingService()
votacao_service = VotacaoService()
jogador_service = JogadorService()


# ============================================================
# HELPERS
# ============================================================

def _usuario_logado():
    return {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'nome': session.get('nome'),
        'role': session.get('role', 'usuario'),
        'senha_temporaria_ativa': bool(session.get('senha_temporaria_ativa')),
        'autenticado': bool(session.get('user_id'))
    }


# ============================================================
# ESTATÍSTICAS GERAIS
# ============================================================

@stats_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """API: Retorna estatísticas gerais"""
    try:
        stats = historico_service.obter_estatisticas()
        return jsonify({'sucesso': True, 'estatisticas': stats})
    except Exception as e:
        logger.error(f"Erro ao retornar estatísticas: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao calcular estatísticas'}), 500


@stats_bp.route('/estatisticas')
@stats_bp.route('/stats')
def estatisticas():
    """Redireciona para página inicial"""
    return redirect(url_for('jogador_crud.index'))


# ============================================================
# ESTATÍSTICAS POR JOGADOR
# ============================================================

@stats_bp.route('/api/stats/players', methods=['GET'])
@login_required
def api_stats_players():
    """API: Estatísticas detalhadas por jogador"""
    try:
        stats = stats_service.calcular_stats_jogadores()
        
        # Ordenar por win_rate (decrescente)
        stats_ordenadas = dict(
            sorted(
                stats.items(),
                key=lambda x: x[1].get('win_rate', 0),
                reverse=True
            )
        )
        
        return jsonify(stats_ordenadas)
    except Exception as e:
        logger.error(f"Erro ao calcular stats de jogadores: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao calcular estatísticas'}), 500


@stats_bp.route('/stats/players', methods=['GET'])
def stats_players():
    """Página de stats de jogadores (redireciona)"""
    return redirect(url_for('jogador_crud.index'))


# ============================================================
# ESTATÍSTICAS POR TIME
# ============================================================

@stats_bp.route('/api/stats/times', methods=['GET'])
@login_required
def api_stats_times():
    """API: Estatísticas de times"""
    try:
        stats = stats_service.calcular_stats_times()
        
        # Ordenar por win_rate (decrescente)
        stats_ordenadas = dict(
            sorted(
                stats.items(),
                key=lambda x: x[1].get('win_rate', 0),
                reverse=True
            )
        )
        
        return jsonify(stats_ordenadas)
    except Exception as e:
        logger.error(f"Erro ao calcular stats de times: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao calcular estatísticas'}), 500


@stats_bp.route('/stats/times', methods=['GET'])
def stats_times_page():
    """Página de stats de times (redireciona)"""
    return redirect(url_for('jogador_crud.index'))


# ============================================================
# ESTATÍSTICAS GERAIS DE SORTEIOS
# ============================================================

@stats_bp.route('/api/stats/geral', methods=['GET'])
@login_required
def api_stats_geral():
    """API: Estatísticas gerais de sorteios"""
    try:
        stats = stats_service.calcular_estatisticas_sorteios()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Erro ao calcular stats gerais: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao calcular estatísticas'}), 500


# ============================================================
# COMBOS VENCEDORES
# ============================================================

@stats_bp.route('/api/stats/combos', methods=['GET'])
@login_required
def api_stats_combos():
    """API: Melhores combos vencedores"""
    try:
        combos = stats_service.get_combos_vencedores()
        return jsonify(combos)
    except Exception as e:
        logger.error(f"Erro ao retornar combos: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao calcular combos'}), 500


@stats_bp.route('/stats/combos', methods=['GET'])
def stats_combos_page():
    """Página de combos (redireciona)"""
    return redirect(url_for('jogador_crud.index'))


# ============================================================
# COMPARAÇÃO ENTRE JOGADORES
# ============================================================

@stats_bp.route('/api/stats/comparacao/<player1>/<player2>', methods=['GET'])
@login_required
def api_stats_comparacao(player1, player2):
    """API: Comparação entre dois jogadores"""
    try:
        comparacao = stats_service.get_comparacao_players(player1, player2)
        return jsonify(comparacao)
    except Exception as e:
        logger.error(f"Erro ao comparar jogadores: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao comparar jogadores'}), 500


# ============================================================
# CHARTS
# ============================================================

@stats_bp.route('/charts', methods=['GET'])
def charts():
    """Página de charts (redireciona)"""
    return redirect(url_for('jogador_crud.index'))


# ============================================================
# EXPORTAÇÃO - CSV
# ============================================================

@stats_bp.route('/export/sorteio/csv', methods=['GET'])
@login_required
def export_sorteio_csv():
    """Exporta último sorteio em CSV"""
    try:
        if 'ultimo_sorteio' not in session:
            return jsonify({'erro': 'Nenhum sorteio realizado'}), 400
        
        sorteio_data = session['ultimo_sorteio']
        times_json = sorteio_data.get('times', [])
        times = [time.get('jogadores', []) for time in times_json]
        somas = sorteio_data.get('somas', [])
        diferenca = sorteio_data.get('diferenca', 0)
        
        csv_content = export_service.exportar_sorteio_csv(times, somas, diferenca)
        
        return send_file(
            io.BytesIO(csv_content.encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'sorteio_{sorteio_data.get("sorteio_id")}.csv'
        )
    except Exception as e:
        logger.error(f"Erro ao exportar CSV: {str(e)}")
        return jsonify({'erro': 'Erro ao exportar'}), 500


@stats_bp.route('/export/historico/csv', methods=['GET'])
@login_required
def export_historico_csv():
    """Exporta histórico completo em CSV"""
    try:
        sorteios = historico_service.listar_sorteios()
        csv_content = export_service.exportar_historico_csv(sorteios)
        
        return send_file(
            io.BytesIO(csv_content.encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='historico_sorteios.csv'
        )
    except Exception as e:
        logger.error(f"Erro ao exportar histórico CSV: {str(e)}")
        return jsonify({'erro': 'Erro ao exportar'}), 500


@stats_bp.route('/export/estatisticas/csv', methods=['GET'])
@login_required
def export_estatisticas_csv():
    """Exporta estatísticas em CSV"""
    try:
        stats = historico_service.obter_estatisticas()
        csv_content = export_service.exportar_estatisticas_csv(stats)
        
        return send_file(
            io.BytesIO(csv_content.encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='estatisticas_sorteios.csv'
        )
    except Exception as e:
        logger.error(f"Erro ao exportar estatísticas CSV: {str(e)}")
        return jsonify({'erro': 'Erro ao exportar'}), 500


# ============================================================
# EXPORTAÇÃO - TXT
# ============================================================

@stats_bp.route('/export/sorteio/txt', methods=['GET'])
@login_required
def export_sorteio_txt():
    """Retorna último sorteio em texto simples"""
    try:
        if 'ultimo_sorteio' not in session:
            return jsonify({'erro': 'Nenhum sorteio realizado'}), 400
        
        sorteio_data = session['ultimo_sorteio']
        times_json = sorteio_data.get('times', [])
        times = [time.get('jogadores', []) for time in times_json]
        somas = sorteio_data.get('somas', [])
        diferenca = sorteio_data.get('diferenca', 0)
        
        txt_content = export_service.exportar_sorteio_texto(
            times, somas, diferenca, sorteio_data.get('sorteio_id') or sorteio_data.get('id')
        )
        return Response(txt_content, mimetype='text/plain; charset=utf-8')
    except Exception as e:
        logger.error(f"Erro ao exportar TXT: {str(e)}")
        return jsonify({'erro': 'Erro ao exportar'}), 500


@stats_bp.route('/api/export/sorteio/txt', methods=['GET'])
@login_required
def api_export_sorteio_txt():
    """API para copiar texto do último sorteio"""
    try:
        if 'ultimo_sorteio' not in session:
            return jsonify({'sucesso': False, 'erro': 'Nenhum sorteio realizado'}), 400

        sorteio_data = session['ultimo_sorteio']
        times_json = sorteio_data.get('times', [])
        times = [time.get('jogadores', []) for time in times_json]
        somas = sorteio_data.get('somas', [])
        diferenca = sorteio_data.get('diferenca', 0)

        txt_content = export_service.exportar_sorteio_texto(
            times, somas, diferenca, sorteio_data.get('sorteio_id') or sorteio_data.get('id')
        )
        return jsonify({'sucesso': True, 'conteudo': txt_content})
    except Exception as e:
        logger.error(f"Erro ao exportar TXT via API: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao exportar'}), 500


# ============================================================
# EXPORTAÇÃO - PDF
# ============================================================

@stats_bp.route('/export/sorteio/pdf', methods=['GET'])
@login_required
def export_sorteio_pdf():
    """Exporta último sorteio em PDF"""
    try:
        if 'ultimo_sorteio' not in session:
            return jsonify({'erro': 'Nenhum sorteio realizado'}), 400

        sorteio_data = session['ultimo_sorteio']
        times_json = sorteio_data.get('times', [])
        times = [time.get('jogadores', []) for time in times_json]
        somas = sorteio_data.get('somas', [])
        diferenca = sorteio_data.get('diferenca', 0)

        pdf_bytes = export_service.exportar_sorteio_pdf(
            times, somas, diferenca,
            sorteio_id=sorteio_data.get('sorteio_id')
        )

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'sorteio_{sorteio_data.get("sorteio_id")}.pdf'
        )
    except Exception as e:
        logger.error(f"Erro ao exportar PDF: {str(e)}")
        return jsonify({'erro': 'Erro ao exportar'}), 500


@stats_bp.route('/api/export/sorteio', methods=['POST'])
@login_required
def api_export_sorteio_data():
    """API para armazenar dados do último sorteio na sessão"""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({'sucesso': False, 'erro': 'Corpo JSON invalido'}), 400
        session['ultimo_sorteio'] = data
        session.modified = True
        return jsonify({'sucesso': True, 'mensagem': 'Sorteio armazenado para exportação'})
    except Exception as e:
        logger.error(f"Erro ao armazenar sorteio: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao armazenar'}), 500


# ============================================================
# SUGESTÕES INTELIGENTES
# ============================================================

@stats_bp.route('/api/sugestoes/nivel', methods=['POST'])
@login_required
def api_sugestoes_nivel():
    """API: Sugestões por nível"""
    try:
        dados = request.get_json(silent=True) or {}
        selecionados = dados.get('selecionados', [])
        todos = jogador_service.listar_para_dict()
        
        sugestoes = sugestoes_service.obter_sugestoes_nivel(selecionados, todos, 5)
        
        return jsonify({
            'sucesso': True,
            'sugestoes': sugestoes,
            'categoria': 'Sugestões por Nível'
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao sugerir por nível: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao sugerir'}), 500


@stats_bp.route('/api/sugestoes/diversidade', methods=['POST'])
@login_required
def api_sugestoes_diversidade():
    """API: Sugestões por diversidade"""
    try:
        dados = request.get_json(silent=True) or {}
        selecionados = dados.get('selecionados', [])
        todos = jogador_service.listar_para_dict()
        
        sugestoes = sugestoes_service.obter_sugestoes_diversidade(selecionados, todos, 5)
        
        return jsonify({
            'sucesso': True,
            'sugestoes': sugestoes,
            'categoria': 'Menos Utilizados'
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao sugerir por diversidade: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao sugerir'}), 500


@stats_bp.route('/api/sugestoes/vencedores', methods=['POST'])
@login_required
def api_sugestoes_vencedores():
    """API: Sugestões por jogadores vencedores"""
    try:
        dados = request.get_json(silent=True) or {}
        selecionados = dados.get('selecionados', [])
        todos = jogador_service.listar_para_dict()
        
        sugestoes = sugestoes_service.obter_sugestoes_vencedoras(selecionados, todos, 5)
        
        return jsonify({
            'sucesso': True,
            'sugestoes': sugestoes,
            'categoria': 'Jogadores Vencedores'
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao sugerir vencedores: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao sugerir'}), 500


@stats_bp.route('/api/sugestoes/duplas', methods=['POST'])
@login_required
def api_sugestoes_duplas():
    """API: Sugestões por duplas vencedoras"""
    try:
        dados = request.get_json(silent=True) or {}
        selecionados = dados.get('selecionados', [])
        todos = jogador_service.listar_para_dict()
        
        sugestoes = sugestoes_service.obter_sugestoes_melhores_duplas(selecionados, todos, 5)
        
        return jsonify({
            'sucesso': True,
            'sugestoes': sugestoes,
            'categoria': 'Duplas Vencedoras'
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao sugerir duplas: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao sugerir'}), 500


@stats_bp.route('/api/sugestoes/combinadas', methods=['POST'])
@login_required
def api_sugestoes_combinadas():
    """API: Sugestões combinadas (todas as estratégias)"""
    try:
        dados = request.get_json(silent=True) or {}
        selecionados = dados.get('selecionados', [])
        todos = jogador_service.listar_para_dict()
        
        sugestoes = sugestoes_service.obter_sugestoes_combinadas(selecionados, todos, 3)
        
        return jsonify({
            'sucesso': True,
            'sugestoes': sugestoes
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao sugerir combinadas: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao sugerir'}), 500


# ============================================================
# RANKING DE JOGADORES
# ============================================================

@stats_bp.route('/ranking')
def pagina_ranking():
    """Página de ranking geral de jogadores"""
    try:
        dados = votacao_service.ranking_jogadores_geral(50)
        return render_template('ranking.html', dados=dados, usuario=_usuario_logado())
    except Exception as e:
        logger.error(f"Erro ao carregar ranking: {str(e)}")
        return render_template('ranking.html', dados=[], erro='Erro ao carregar ranking'), 500


@stats_bp.route('/api/ranking/geral')
def api_ranking_geral():
    """API: Ranking geral de jogadores"""
    try:
        limite = request.args.get('limite', 50, type=int)
        dados = votacao_service.ranking_jogadores_geral(limite)
        
        return jsonify({
            'sucesso': True,
            'dados': dados
        })
    except Exception as e:
        logger.error(f"Erro ao retornar ranking: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao retornar ranking'}), 500


@stats_bp.route('/api/ranking/periodo/<int:dias>')
def api_ranking_periodo(dias):
    """API: Ranking de um período (desativado)"""
    return jsonify({'sucesso': False, 'erro': 'Endpoint desativado'}), 410


@stats_bp.route('/api/ranking/stats')
def api_ranking_stats():
    """API: Stats do ranking (desativado)"""
    return jsonify({'sucesso': False, 'erro': 'Endpoint desativado'}), 410

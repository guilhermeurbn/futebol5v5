"""
Rotas de Partidas, Sorteios e Favoritos
- Sorteios, histórico de partidas, favoritos, undo/redo
- QR codes e compartilhamento
"""
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, session, send_file, Response
from functools import wraps
import io
import random
import logging

from services.jogador_service import JogadorService
from services.balanceamento import BalanceadorTimes
from services.historico_service import HistoricoService
from services.partida_service import PartidaService
from services.favorito_service import FavoritoService
from services.undoredo_service import UndoRedoService
from services.qrcode_service import QRCodeService
from services.export_service import ExportService
from services.juiz_partida_service import JuizPartidaService
from services.votacao_service import VotacaoService
from services.jogador_stats_service import JogadorStatsService

partida_bp = Blueprint('partida', __name__)
logger = logging.getLogger(__name__)

jogador_service = JogadorService()
historico_service = HistoricoService()
partida_service = PartidaService()
favorito_service = FavoritoService()
undoredo_service = UndoRedoService()
qrcode_service = QRCodeService()
export_service = ExportService()
juiz_partida_service = JuizPartidaService()
votacao_service = VotacaoService()
jogador_stats_service = JogadorStatsService()


# ============================================================
# HELPERS
# ============================================================

def _is_admin():
    return session.get('role') in ['super_admin', 'admin']


def _is_juiz():
    return session.get('role') == 'juiz'


def _usuario_logado():
    return {
        'id': session.get('user_id'),
        'username': session.get('username'),
        'nome': session.get('nome'),
        'role': session.get('role', 'usuario'),
        'senha_temporaria_ativa': bool(session.get('senha_temporaria_ativa')),
        'autenticado': bool(session.get('user_id'))
    }


def admin_or_juiz_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api/'):
                return jsonify({'sucesso': False, 'erro': 'Autenticacao obrigatoria'}), 401
            return redirect(url_for('auth.login_page'))
        if not (_is_admin() or _is_juiz()):
            if request.path.startswith('/api/'):
                return jsonify({'sucesso': False, 'erro': 'Acesso restrito'}), 403
            return redirect(url_for('jogador_crud.index'))
        return f(*args, **kwargs)
    return wrapper


def _sortear_diferente_do_anterior(presentes, tentativas_max=8):
    """Tenta gerar um sorteio diferente dos mais recentes"""
    assinaturas_bloqueadas = _assinaturas_recentes_stack(limite=5)
    if 'ultimo_sorteio' in session:
        assinatura_sessao = _assinatura_times_json(session.get('ultimo_sorteio', {}).get('times', []))
        if assinatura_sessao:
            assinaturas_bloqueadas.add(assinatura_sessao)

    tentativas_max = max(10, tentativas_max)
    resultado = None
    
    for _ in range(max(1, tentativas_max)):
        candidato = BalanceadorTimes.sortear_multiplos_times_com_goleiros(presentes)
        assinatura_candidato = _assinatura_times_obj(candidato[0])
        resultado = candidato

        if not assinaturas_bloqueadas or assinatura_candidato not in assinaturas_bloqueadas:
            return candidato

    # Fallback: força uma variação
    if resultado:
        variacao = _forcar_variacao_times(resultado[0], assinaturas_bloqueadas)
        if variacao:
            somas = [sum(j.nivel for j in time) for time in variacao]
            return variacao, somas, resultado[2], resultado[3]

    return resultado


def _assinatura_times_obj(times):
    """Cria assinatura estável de composição dos times a partir de objetos Jogador"""
    times_assinatura = []
    for time in times:
        nomes = sorted(getattr(j, 'nome', str(j)).strip().lower() for j in time)
        times_assinatura.append('|'.join(nomes))
    return '||'.join(sorted(times_assinatura))


def _assinatura_times_json(times_json):
    """Cria assinatura estável de composição dos times a partir de JSON"""
    times_assinatura = []
    for time in times_json:
        jogadores = time.get('jogadores', [])
        nomes = sorted(str(j.get('nome', '')).strip().lower() for j in jogadores)
        times_assinatura.append('|'.join(nomes))
    return '||'.join(sorted(times_assinatura))


def _assinaturas_recentes_stack(limite=5):
    """Retorna assinaturas dos sorteios mais recentes da pilha"""
    pilha, indice_atual = undoredo_service.obter_historico()
    if not pilha or indice_atual < 0:
        return set()

    inicio = max(0, indice_atual - (limite - 1))
    recentes = pilha[inicio:indice_atual + 1]
    assinaturas = set()
    for item in recentes:
        assinatura = _assinatura_times_json(item.get('times', []))
        if assinatura:
            assinaturas.add(assinatura)
    return assinaturas


def _forcar_variacao_times(times, assinaturas_bloqueadas):
    """Força uma variação simples trocando jogadores entre times"""
    if len(times) < 2:
        return None

    base_times = [time[:] for time in times]
    tentativas = 50
    for _ in range(tentativas):
        i, j = random.sample(range(len(base_times)), 2)
        if not base_times[i] or not base_times[j]:
            continue

        idx_i = random.randrange(len(base_times[i]))
        idx_j = random.randrange(len(base_times[j]))

        novo = [time[:] for time in base_times]
        novo[i][idx_i], novo[j][idx_j] = novo[j][idx_j], novo[i][idx_i]

        assinatura_nova = _assinatura_times_obj(novo)
        if assinatura_nova not in assinaturas_bloqueadas:
            return novo

    return None


def _montar_sorteio_exportacao(sorteio_id, times, somas, diferenca, melhor_time, tem_aviso, aviso_msg):
    """Monta um payload serializável para exportação"""
    times_json = []
    for idx, time in enumerate(times):
        times_json.append({
            'numero': idx + 1,
            'jogadores': [j.para_dict() for j in time],
            'soma': somas[idx]
        })

    return {
        'sorteio_id': sorteio_id,
        'times': times_json,
        'num_times': len(times),
        'somas': somas,
        'diferenca': diferenca,
        'melhor_time': melhor_time,
        'tem_aviso': tem_aviso,
        'aviso_msg': aviso_msg
    }


def _salvar_ultimo_sorteio_sessao(payload):
    session['ultimo_sorteio'] = payload
    session.modified = True


# ============================================================
# SORTEAR TIMES
# ============================================================

@partida_bp.route('/sortear')
def sortear():
    """Página com times sorteados"""
    try:
        presentes = jogador_service.listar_presentes()
        times, somas, tem_aviso, aviso_msg = _sortear_diferente_do_anterior(presentes)
        num_times = len(times)
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        melhor_time = BalanceadorTimes.obter_melhor_time(somas)
        
        # Registrar no histórico
        sorteio = historico_service.adicionar_sorteio(times, somas, num_times, diferenca)
        sorteio_id = sorteio.get('id')
        if _is_juiz():
            juiz_partida_service.registrar_sorteio(sorteio_id)

        # Salvar para download/exportação
        sorteio_data = _montar_sorteio_exportacao(
            sorteio_id, times, somas, diferenca, melhor_time, tem_aviso, aviso_msg
        )
        _salvar_ultimo_sorteio_sessao(sorteio_data)
        undoredo_service.adicionar_sorteio(sorteio_data)
        
        return render_template(
            'times.html',
            jogadores=presentes,
            times=times,
            somas=somas,
            num_times=num_times,
            diferenca=diferenca,
            melhor_time=melhor_time,
            sorteio_id=sorteio_id,
            tem_aviso=tem_aviso,
            aviso_msg=aviso_msg,
            usuario=_usuario_logado()
        )
    except ValueError as e:
        logger.error(f"Erro ao sortear: {str(e)}")
        return render_template('index.html', erro=str(e)), 400
    except Exception as e:
        logger.error(f"Erro inesperado ao sortear: {str(e)}")
        return render_template('index.html', erro='Erro ao sortear times'), 500


@partida_bp.route('/api/times')
def sortear_api():
    """API: Sorteia times"""
    try:
        presentes = jogador_service.listar_presentes()
        times, somas, tem_aviso, aviso_msg = _sortear_diferente_do_anterior(presentes)
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        melhor_time = BalanceadorTimes.obter_melhor_time(somas)
        
        # Registrar no histórico
        sorteio = historico_service.adicionar_sorteio(times, somas, len(times), diferenca)
        if _is_juiz():
            juiz_partida_service.registrar_sorteio(sorteio.get('id'))

        sorteio_data = _montar_sorteio_exportacao(
            sorteio.get('id'), times, somas, diferenca, melhor_time, tem_aviso, aviso_msg
        )
        _salvar_ultimo_sorteio_sessao(sorteio_data)
        undoredo_service.adicionar_sorteio(sorteio_data)
        
        return jsonify({
            'sucesso': True,
            'sorteio_id': sorteio.get('id'),
            'times': sorteio_data['times'],
            'num_times': len(times),
            'diferenca': diferenca,
            'melhor_time': melhor_time,
            'tem_aviso': tem_aviso,
            'aviso_msg': aviso_msg
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao sortear via API: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao sortear'}), 500


# ============================================================
# HISTÓRICO
# ============================================================

@partida_bp.route('/historico')
def historico():
    """Página com histórico de sorteios"""
    try:
        sorteios = historico_service.listar_sorteios()
        sorteios = list(reversed(sorteios))  # Mais recente primeiro
        return render_template('historico.html', sorteios=sorteios, usuario=_usuario_logado())
    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {str(e)}")
        return render_template('historico.html', sorteios=[], erro='Erro ao carregar histórico'), 500


@partida_bp.route('/sorteio/<int:sorteio_id>')
def ver_sorteio(sorteio_id):
    """Visualiza um sorteio específico"""
    try:
        sorteio = historico_service.obter_sorteio(sorteio_id)
        if not sorteio:
            return render_template('historico.html', sorteios=[], erro="Sorteio não encontrado"), 404

        partida_votacao = votacao_service.obter_por_sorteio(sorteio.get('id'))
        resultado_partida = _obter_resultado_sorteio(sorteio_id)
        ranking_top10 = []
        melhor_jogador = None

        if partida_votacao and partida_votacao.get('ranking'):
            ranking_top10 = partida_votacao['ranking'].get('ranking_jogadores', [])[:10]
            melhor_jogador = partida_votacao['ranking'].get('melhor_jogador')
        
        return render_template(
            'sorteio_detalhe.html',
            sorteio=sorteio,
            partida_votacao=partida_votacao,
            resultado_partida=resultado_partida,
            ranking_top10=ranking_top10,
            melhor_jogador=melhor_jogador,
            usuario=_usuario_logado()
        )
    except Exception as e:
        logger.error(f"Erro ao visualizar sorteio: {str(e)}")
        return render_template('historico.html', sorteios=[], erro='Erro ao carregar sorteio'), 500


@partida_bp.route('/api/historico')
def api_historico():
    """API: Retorna histórico de sorteios"""
    try:
        sorteios = historico_service.listar_sorteios()
        sorteios = list(reversed(sorteios))
        return jsonify({'sucesso': True, 'sorteios': sorteios})
    except Exception as e:
        logger.error(f"Erro ao retornar histórico: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao carregar histórico'}), 500


def _obter_resultado_sorteio(sorteio_id):
    """Obtém resultado da última partida de um sorteio"""
    partidas = partida_service.obter_partidas_sorteio(sorteio_id)
    if not partidas:
        return None
    partidas_ordenadas = sorted(partidas, key=lambda item: (item.get('data', ''), item.get('id', 0)), reverse=True)
    return partidas_ordenadas[0] if partidas_ordenadas else None


# ============================================================
# RESULTADO DE PARTIDA
# ============================================================

@partida_bp.route('/resultado_partida/<int:sorteio_id>')
@admin_or_juiz_required
def resultado_partida_page(sorteio_id):
    """Página para registrar resultado de uma partida"""
    try:
        sorteio = historico_service.obter_sorteio(sorteio_id)
        if not sorteio:
            return render_template('historico.html', sorteios=[], erro="Sorteio não encontrado"), 404

        partida_votacao = votacao_service.obter_por_sorteio(sorteio.get('id'))
        resultado = _obter_resultado_sorteio(sorteio_id)
        
        if partida_votacao and partida_votacao.get('status') == 'encerrada':
            return ver_sorteio(sorteio_id)

        if resultado:
            return ver_sorteio(sorteio_id)

        return render_template(
            'resultado_partida.html',
            sorteio=sorteio,
            sorteio_id=sorteio_id,
            usuario=_usuario_logado()
        )
    except Exception as e:
        logger.error(f"Erro ao carregar resultado: {str(e)}")
        return render_template('historico.html', sorteios=[], erro='Erro ao carregar'), 500


@partida_bp.route('/api/partida/registrar', methods=['POST'])
@admin_or_juiz_required
def registrar_resultado_partida():
    """API: Registra resultado de uma partida"""
    try:
        dados = request.get_json(silent=True) or {}
        sorteio_id = dados.get('sorteio_id')
        time_vencedor = dados.get('time_vencedor')
        gols_times = dados.get('gols_times', [])
        notas = dados.get('notas', '')
        jogadores_detalhes = dados.get('jogadores_detalhes', [])
        times_desempenho = dados.get('times_desempenho', [])
        
        if not sorteio_id or not time_vencedor:
            return jsonify({
                'sucesso': False,
                'erro': 'Sorteio ID e Time Vencedor são obrigatórios'
            }), 400
        
        if not gols_times:
            return jsonify({'sucesso': False, 'erro': 'Registre gols de todos os times'}), 400
        
        partida = partida_service.registrar_resultado(
            sorteio_id, time_vencedor, gols_times, notas, times_desempenho
        )
        
        partida_id = partida.get('id')
        for detalhe in jogadores_detalhes:
            jogador_stats_service.registrar_desempenho_jogador(
                partida_id=partida_id,
                nome_jogador=detalhe.get('nome'),
                gols=detalhe.get('gols', 0),
                assistencias=detalhe.get('assistencias', 0),
                cartoes_amarelos=detalhe.get('cartoes_amarelos', 0),
                cartoes_vermelhos=detalhe.get('cartoes_vermelhos', 0),
                time_numero=detalhe.get('time_numero', 1),
                posicao=detalhe.get('posicao', 'linha')
            )

        partida['jogadores_detalhes'] = jogadores_detalhes
        votacao_service.atualizar_resultado_da_rodada(sorteio_id, partida)
        if _is_juiz():
            juiz_partida_service.marcar_resultado_registrado(sorteio_id, partida.get('id'))

        return jsonify({
            'sucesso': True,
            'partida': partida,
            'mensagem': 'Resultado registrado com sucesso!',
            'proximo_passo_url': url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id)
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao registrar resultado: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao registrar resultado'}), 500


# ============================================================
# CAMPEONATO
# ============================================================

@partida_bp.route('/campeonato')
def campeonato_page():
    return redirect(url_for('jogador_crud.index'))


@partida_bp.route('/api/campeonato')
def api_campeonato():
    """API: Retorna dados do campeonato"""
    try:
        campeonato = partida_service.obter_campeonato()
        placar_geral = partida_service.obter_placar_geral()
        return jsonify({
            'sucesso': True,
            'campeonato': campeonato,
            'placar_geral': placar_geral
        })
    except Exception as e:
        logger.error(f"Erro ao retornar campeonato: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao carregar campeonato'}), 500


# ============================================================
# FAVORITOS
# ============================================================

@partida_bp.route('/api/favoritar-time', methods=['POST'])
def api_favoritar_time():
    """API: Favorita um time"""
    try:
        dados = request.get_json(silent=True) or {}
        sorteio_id = dados.get('sorteio_id')
        time_numero = dados.get('time_numero')
        jogadores = dados.get('jogadores', [])
        pontuacao = dados.get('pontuacao', 0)
        nome = dados.get('nome', '')
        
        if not sorteio_id or not time_numero or not jogadores:
            return jsonify({'sucesso': False, 'erro': 'Dados incompletos'}), 400
        
        favorito = favorito_service.favoritar_time(
            sorteio_id, time_numero, jogadores, pontuacao, nome
        )
        
        return jsonify({
            'sucesso': True,
            'favorito': favorito,
            'mensagem': 'Time favoritado com sucesso!'
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao favoritar time: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao favoritar'}), 500


@partida_bp.route('/favoritos')
def listar_favoritos_page():
    return redirect(url_for('jogador_crud.index'))


@partida_bp.route('/api/favoritos')
def api_listar_favoritos():
    """API: Lista todos os favoritos"""
    try:
        favoritos = favorito_service.listar_favoritos()
        return jsonify({'sucesso': True, 'favoritos': favoritos})
    except Exception as e:
        logger.error(f"Erro ao listar favoritos: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao listar favoritos'}), 500


@partida_bp.route('/api/favorito/<int:fav_id>/remover', methods=['DELETE'])
def api_remover_favorito(fav_id):
    """API: Remove um favorito"""
    try:
        sucesso = favorito_service.remover_favorito(fav_id)
        if sucesso:
            return jsonify({'sucesso': True, 'mensagem': 'Favorito removido com sucesso'})
        return jsonify({'sucesso': False, 'erro': 'Favorito não encontrado'}), 404
    except Exception as e:
        logger.error(f"Erro ao remover favorito: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao remover'}), 500


@partida_bp.route('/api/favorito/<int:fav_id>/renomear', methods=['POST'])
def api_renomear_favorito(fav_id):
    """API: Renomeia um favorito"""
    try:
        dados = request.get_json(silent=True) or {}
        novo_nome = dados.get('nome', '')
        
        if not novo_nome:
            return jsonify({'sucesso': False, 'erro': 'Nome não pode ser vazio'}), 400
        
        favorito = favorito_service.renomear_favorito(fav_id, novo_nome)
        if favorito:
            return jsonify({'sucesso': True, 'favorito': favorito, 'mensagem': 'Renomeado com sucesso'})
        return jsonify({'sucesso': False, 'erro': 'Favorito não encontrado'}), 404
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao renomear favorito: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao renomear'}), 500


@partida_bp.route('/api/favorito/<int:fav_id>/usar', methods=['POST'])
def api_usar_favorito(fav_id):
    """API: Marca favorito como usado"""
    try:
        sucesso = favorito_service.incrementar_uso(fav_id)
        if sucesso:
            favorito = favorito_service.obter_favorito(fav_id)
            return jsonify({'sucesso': True, 'favorito': favorito, 'mensagem': 'Favorito utilizado'})
        return jsonify({'sucesso': False, 'erro': 'Favorito não encontrado'}), 404
    except Exception as e:
        logger.error(f"Erro ao usar favorito: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao usar favorito'}), 500


# ============================================================
# UNDO / REDO
# ============================================================

@partida_bp.route('/api/sorteio/undo', methods=['POST'])
def api_undo_sorteio():
    """API: Desfaz o sorteio"""
    try:
        sorteio = undoredo_service.undo()
        status = undoredo_service.obter_status()
        
        if sorteio:
            return jsonify({
                'sucesso': True,
                'sorteio': sorteio,
                'status': status,
                'mensagem': f'Voltou para sorteio #{status["sorteio_atual"]}'
            })
        return jsonify({
            'sucesso': False,
            'erro': 'Nenhum sorteio anterior disponível',
            'status': status
        }), 400
    except Exception as e:
        logger.error(f"Erro ao desfazer sorteio: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao desfazer'}), 500


@partida_bp.route('/api/sorteio/redo', methods=['POST'])
def api_redo_sorteio():
    """API: Refaz o sorteio"""
    try:
        sorteio = undoredo_service.redo()
        status = undoredo_service.obter_status()
        
        if sorteio:
            return jsonify({
                'sucesso': True,
                'sorteio': sorteio,
                'status': status,
                'mensagem': f'Avançou para sorteio #{status["sorteio_atual"]}'
            })
        return jsonify({
            'sucesso': False,
            'erro': 'Nenhum sorteio posterior disponível',
            'status': status
        }), 400
    except Exception as e:
        logger.error(f"Erro ao refazer sorteio: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao refazer'}), 500


@partida_bp.route('/api/sorteio/status', methods=['GET'])
def api_status_sorteio():
    """API: Retorna status do undo/redo"""
    try:
        status = undoredo_service.obter_status()
        sorteio_atual = undoredo_service.obter_atual()
        return jsonify({'sucesso': True, 'status': status, 'sorteio_atual': sorteio_atual})
    except Exception as e:
        logger.error(f"Erro ao retornar status: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao retornar status'}), 500


@partida_bp.route('/api/sorteio/adicionar-stack', methods=['POST'])
def api_adicionar_stack():
    """API: Adiciona sorteio à pilha"""
    try:
        sorteio_data = request.get_json(silent=True) or {}
        if not sorteio_data:
            return jsonify({'sucesso': False, 'erro': 'Corpo JSON invalido'}), 400
        
        indice, total = undoredo_service.adicionar_sorteio(sorteio_data)
        status = undoredo_service.obter_status()
        
        return jsonify({
            'sucesso': True,
            'status': status,
            'mensagem': f'Sorteio {indice + 1} de {total} adicionado'
        })
    except Exception as e:
        logger.error(f"Erro ao adicionar sorteio à pilha: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao adicionar'}), 500


# ============================================================
# QR CODE E COMPARTILHAMENTO
# ============================================================

@partida_bp.route('/api/qrcode/sorteio/<int:sorteio_id>', methods=['GET'])
def api_qrcode_sorteio(sorteio_id):
    """API: Gera QR code de um sorteio"""
    try:
        sorteio = historico_service.obter_sorteio(sorteio_id)
        if not sorteio:
            return jsonify({'sucesso': False, 'erro': 'Sorteio não encontrado'}), 404
        
        sorteio_data = {
            'id': sorteio_id,
            'times': sorteio.get('times', []),
            'pontuacoes': sorteio.get('pontuacoes', []),
            'num_times': sorteio.get('num_times', 0)
        }
        
        url, qr_bytes = qrcode_service.gerar_qr_sorteio(sorteio_data)
        
        return send_file(
            io.BytesIO(qr_bytes),
            mimetype='image/png',
            as_attachment=False,
            download_name=f'qrcode_sorteio_{sorteio_id}.png'
        )
    except Exception as e:
        logger.error(f"Erro ao gerar QR code: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao gerar QR code'}), 500


@partida_bp.route('/compartilhado', methods=['GET'])
def compartilhado_page():
    """Página para exibir sorteio compartilhado"""
    try:
        dados_b64 = request.args.get('sorteio')
        if not dados_b64:
            return render_template('compartilhado_vazio.html'), 400
        
        sorteio_data = qrcode_service.decodificar_sorteio(dados_b64)
        return render_template('compartilhado.html', sorteio=sorteio_data, usuario=_usuario_logado())
    except ValueError as e:
        return render_template('compartilhado_vazio.html', erro=str(e)), 400
    except Exception as e:
        logger.error(f"Erro ao decodificar sorteio: {str(e)}")
        return render_template('compartilhado_vazio.html', erro='Erro ao decodificar'), 500


@partida_bp.route('/api/qrcode/link-compartilhamento/<int:sorteio_id>', methods=['GET'])
def api_link_compartilhamento(sorteio_id):
    """API: Gera link de compartilhamento"""
    try:
        sorteio = historico_service.obter_sorteio(sorteio_id)
        if not sorteio:
            return jsonify({'sucesso': False, 'erro': 'Sorteio não encontrado'}), 404
        
        sorteio_data = {
            'id': sorteio_id,
            'times': sorteio.get('times', []),
            'pontuacoes': sorteio.get('pontuacoes', []),
            'num_times': sorteio.get('num_times', 0),
            'data': sorteio.get('data', '')
        }
        
        url_base = request.host_url.rstrip('/')
        url_compartilhamento, qr_bytes = qrcode_service.gerar_qr_sorteio(sorteio_data, url_base)
        
        import base64
        qr_b64 = base64.b64encode(qr_bytes).decode()
        
        return jsonify({
            'sucesso': True,
            'sorteio_id': sorteio_id,
            'url': url_compartilhamento,
            'qr_code': f'data:image/png;base64,{qr_b64}'
        })
    except Exception as e:
        logger.error(f"Erro ao gerar link: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao gerar link'}), 500

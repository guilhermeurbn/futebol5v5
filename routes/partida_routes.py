"""
Rotas de Partidas e Sorteios
- Sorteios, histórico de partidas, undo/redo
- QR codes e compartilhamento
"""
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, session, send_file, Response, flash
from functools import wraps
import io
import random
import logging

from services.jogador_service import JogadorService
from services.balanceamento import BalanceadorTimes
from services.historico_service import HistoricoService
from services.partida_service import PartidaService
from services.undoredo_service import UndoRedoService
from services.qrcode_service import QRCodeService
from services.export_service import ExportService
from services.juiz_partida_service import JuizPartidaService
from services.votacao_service import VotacaoService
from services.jogador_stats_service import JogadorStatsService
from services.db import clear_db_cache

partida_bp = Blueprint('partida', __name__)
logger = logging.getLogger(__name__)

jogador_service = JogadorService()
historico_service = HistoricoService()
partida_service = PartidaService()
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
    return session.get('role') in ['admin']


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


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api/'):
                return jsonify({'sucesso': False, 'erro': 'Autenticacao obrigatoria'}), 401
            return redirect(url_for('auth.login_page'))
        if not _is_admin():
            if request.path.startswith('/api/'):
                return jsonify({'sucesso': False, 'erro': 'Apenas Administradores têm permissão'}), 403
            return redirect(url_for('partida.historico', erro='Apenas Administradores podem excluir histórico'))
        return f(*args, **kwargs)
    return wrapper


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
    if _is_admin():
        return redirect(url_for('jogador_crud.index'))

    if not session.get('user_id'):
        return redirect(url_for('auth.login_page'))

    if not _is_juiz():
        return redirect(url_for('jogador_crud.index'))

    fluxo = juiz_partida_service.obter_estado()
    if (fluxo.get('status') or 'idle') not in {'selecionando', 'sorteada'}:
        return redirect(url_for('juiz.jogar_page'))

    if (fluxo.get('status') or 'idle') == 'sorteada' and fluxo.get('partida_atual', {}).get('sorteio_id'):
        return redirect(url_for('juiz.juiz_times_page', sorteio_id=fluxo['partida_atual']['sorteio_id']))

    try:
        presentes = jogador_service.listar_presentes()
        if len(presentes) not in {10, 15, 20}:
            return render_template('index.html', erro='Selecione exatamente 10, 15 ou 20 jogadores antes de sortear.'), 400

        times, somas, tem_aviso, aviso_msg = _sortear_diferente_do_anterior(presentes)
        num_times = len(times)
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        melhor_time = BalanceadorTimes.obter_melhor_time(somas)
        
        times_json = [
            {
                "numero": idx + 1,
                "jogadores": [j.para_dict() for j in time],
                "soma": somas[idx]
            }
            for idx, time in enumerate(times)
        ]

        if _is_juiz():
            juiz_partida_service.salvar_rascunho_sorteio(times_json, somas, diferenca)

        # Salvar para download/exportação
        sorteio_data = _montar_sorteio_exportacao(
            'rascunho', times, somas, diferenca, melhor_time, tem_aviso, aviso_msg
        )
        _salvar_ultimo_sorteio_sessao(sorteio_data)
        undoredo_service.adicionar_sorteio(sorteio_data)
        return redirect(url_for('juiz.juiz_times_page'))
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
        if not session.get('user_id') or not _is_juiz():
            return jsonify({'sucesso': False, 'erro': 'Acesso restrito ao juiz'}), 403

        fluxo = juiz_partida_service.obter_estado()
        if (fluxo.get('status') or 'idle') not in {'selecionando', 'sorteada'}:
            return jsonify({'sucesso': False, 'erro': 'Fluxo do juiz fora da etapa de selecao'}), 409

        presentes = jogador_service.listar_presentes()
        if len(presentes) not in {10, 15, 20}:
            return jsonify({'sucesso': False, 'erro': 'Selecione exatamente 10, 15 ou 20 jogadores.'}), 400

        times, somas, tem_aviso, aviso_msg = _sortear_diferente_do_anterior(presentes)
        diferenca = BalanceadorTimes.calcular_diferenca_multiplos(somas)
        melhor_time = BalanceadorTimes.obter_melhor_time(somas)
        
        # Registrar no histórico como um novo sorteio único e independente
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

def _enriquecer_sorteio_historico(sorteio):
    """Anexa status de resultado e votação para a visão resumida do histórico."""
    item = dict(sorteio)
    sorteio_id = item.get('id')
    resultado_partida = _obter_resultado_sorteio(sorteio_id)
    partida_votacao = votacao_service.obter_por_sorteio(sorteio_id)
    ranking = ((partida_votacao or {}).get('ranking') or {})
    ranking_jogadores = list(ranking.get('ranking_jogadores') or [])
    if ranking_jogadores:
        ranking_jogadores = sorted(
            ranking_jogadores,
            key=lambda x: (float(x.get('nota_media') or 0), float(x.get('pontos') or 0), int(x.get('votos') or 0)),
            reverse=True
        )
    ranking_top10 = ranking_jogadores  # Return all players in ranking without truncation
    melhor_jogador = ranking_jogadores[0] if ranking_jogadores else ranking.get('melhor_jogador')
    status_votacao = (partida_votacao or {}).get('status') or 'nao_iniciada'

    media_geral = float(ranking.get('media_geral') or 0.0)
    if not media_geral and ranking_jogadores:
        votados = [float(j.get('nota_media') or 0) for j in ranking_jogadores if int(j.get('votos') or 0) > 0 or float(j.get('nota_media') or 0) > 0]
        if votados:
            media_geral = round(sum(votados) / len(votados), 2)
        else:
            todas_notas = [float(j.get('nota_media') or 0) for j in ranking_jogadores if float(j.get('nota_media') or 0) > 0]
            if todas_notas:
                media_geral = round(sum(todas_notas) / len(todas_notas), 2)

    resultado_resumo = []
    if resultado_partida:
        desempenho_times = resultado_partida.get('times_desempenho') or []
        for idx, gols in enumerate(resultado_partida.get('gols_times', []) or [], start=1):
            desempenho = next(
                (item_desempenho for item_desempenho in desempenho_times if int(item_desempenho.get('time_numero', 0) or 0) == idx),
                None,
            )
            resultado_resumo.append({
                'time_numero': idx,
                'gols': gols,
                'desempenho': desempenho or {'vitorias': 0, 'empates': 0, 'derrotas': 0},
            })

    card_campeao_url = (resultado_partida or {}).get('card_campeao_url') or (partida_votacao or {}).get('card_campeao_url')

    item.update({
        'card_campeao_url': card_campeao_url,
        'resultado_partida': resultado_partida,
        'resultado_resumo': resultado_resumo,
        'partida_votacao': partida_votacao,
        'votacao_status': status_votacao,
        'votacao_encerrada': status_votacao == 'encerrada',
        'votacao_aberta': status_votacao == 'aberta',
        'ranking_top10': ranking_top10,
        'ranking_total_jogadores': len(ranking_jogadores) or ranking.get('total_jogadores') or 0,
        'ranking_media_geral': media_geral,
        'melhor_jogador': melhor_jogador,
    })
    return item


def _resumo_historico_vazio():
    return {
        'total_sorteios': 0,
        'com_resultado': 0,
        'votacoes_encerradas': 0,
        'votacoes_abertas': 0,
    }

@partida_bp.route('/historico')
def historico():
    """Página com histórico de sorteios"""
    try:
        sorteio_id_param = request.args.get('sorteio_id') or request.args.get('sorteio')
        target_sorteio_id = int(sorteio_id_param) if (sorteio_id_param and sorteio_id_param.isdigit()) else None
        sorteios_raw = historico_service.listar_sorteios() or []
        sorteios_raw = [s for s in sorteios_raw if not s.get('rascunho')]
        sorteios = list(reversed(sorteios_raw))
        sorteios = [_enriquecer_sorteio_historico(sorteio) for sorteio in sorteios]
        resumo = {
            'total_sorteios': len(sorteios),
            'com_resultado': sum(1 for sorteio in sorteios if sorteio.get('resultado_partida')),
            'votacoes_encerradas': sum(1 for sorteio in sorteios if sorteio.get('votacao_encerrada')),
            'votacoes_abertas': sum(1 for sorteio in sorteios if sorteio.get('votacao_aberta')),
        }
        return render_template('historico.html', sorteios=sorteios, resumo=resumo, usuario=_usuario_logado(), target_sorteio_id=target_sorteio_id)
    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {str(e)}")
        return render_template(
            'historico.html',
            sorteios=[],
            resumo=_resumo_historico_vazio(),
            target_sorteio_id=None,
            erro='Erro ao carregar histórico',
        ), 500


@partida_bp.route('/sorteio/<int:sorteio_id>')
def ver_sorteio(sorteio_id):
    """Visualiza um sorteio específico"""
    try:
        sorteio = historico_service.obter_sorteio(sorteio_id)
        if not sorteio:
            return render_template('historico.html', sorteios=[], resumo=_resumo_historico_vazio(), erro="Sorteio não encontrado"), 404

        partida_votacao = votacao_service.obter_por_sorteio(sorteio.get('id'))
        resultado_partida = _obter_resultado_sorteio(sorteio_id)
        ranking_top10 = []
        melhor_jogador = None

        if partida_votacao and partida_votacao.get('ranking'):
            ranking_top10 = partida_votacao['ranking'].get('ranking_jogadores', [])
            melhor_jogador = partida_votacao['ranking'].get('melhor_jogador')

        if _is_juiz():
            return render_template(
                'juiz_times.html',
                sorteio=sorteio,
                partida_votacao=partida_votacao,
                resultado_partida=resultado_partida,
                usuario=_usuario_logado(),
            )
        
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
        return render_template('historico.html', sorteios=[], resumo=_resumo_historico_vazio(), erro='Erro ao carregar sorteio'), 500


@partida_bp.route('/sorteio/<int:sorteio_id>/deletar', methods=['POST'])
@admin_required
def deletar_sorteio_historico(sorteio_id):
    """Exclui um sorteio e todos os seus dados vinculados em cascata (partida, votação e estatísticas)."""
    try:
        from services.votacao_service import VotacaoService
        from services.jogador_stats_service import JogadorStatsService
        from services.db import clear_db_cache
        votacao_svc = VotacaoService()

        # 1. Apaga do histórico de sorteios
        historico_service.deletar_sorteio(sorteio_id)

        # 2. Apaga resultados de partidas vinculados
        partida_service.deletar_partida_do_sorteio(sorteio_id)

        # 3. Apaga rodada de votação vinculada
        votacao_svc.deletar_votacao_do_sorteio(sorteio_id)

        # 4. Limpa caches globais em memória do banco e atualiza estatísticas dos jogadores
        clear_db_cache()
        JogadorStatsService.invalidar_cache_stats()
        try:
            from services.jogador_service import sincronizar_dados_e_partidas
            sincronizar_dados_e_partidas()
        except Exception:
            pass

        # 5. Se for a partida ativa do juiz, reseta o fluxo
        estado_juiz = juiz_partida_service.obter_estado()
        partida_atual = (estado_juiz.get('partida_atual') or {})
        if int(partida_atual.get('sorteio_id', 0) or 0) == int(sorteio_id):
            juiz_partida_service.finalizar_partida()

        msg = f"Sorteio #{sorteio_id} e todos os seus dados foram excluídos com sucesso."
        if _is_juiz():
            return redirect(url_for('juiz.juiz_historico', sucesso=msg))
        return redirect(url_for('partida.historico', sucesso=msg))
    except Exception as e:
        logger.error(f"Erro ao deletar sorteio #{sorteio_id}: {str(e)}")
        if _is_juiz():
            return redirect(url_for('juiz.juiz_historico', erro='Erro ao excluir sorteio'))
        return redirect(url_for('partida.historico', erro='Erro ao excluir sorteio'))


@partida_bp.route('/sorteio/<int:sorteio_id>/trocar-foto', methods=['POST'])
@admin_or_juiz_required
def trocar_foto_sorteio(sorteio_id):
    """Substitui a foto do time campeão de um sorteio de forma totalmente segura com exclusão da foto anterior."""
    try:
        from services.upload_service import UploadService, UploadError
        from services.partida_service import PartidaService
        from services.votacao_service import VotacaoService
        from services.jogador_stats_service import JogadorStatsService
        from services.db import clear_db_cache

        upload_svc = UploadService()
        partida_svc = PartidaService()
        votacao_svc = VotacaoService()

        json_data = request.get_json(silent=True) or {}
        file_storage = request.files.get('foto_campeao') or request.files.get('foto') or request.files.get('file')
        base64_data = request.form.get('card_campeao_base64') or json_data.get('card_campeao_base64') or request.form.get('foto_base64') or json_data.get('foto_base64')
        remover_foto = request.form.get('remover_foto') == '1' or json_data.get('remover_foto')

        # 1. Obter URL da foto antiga antes da substituição
        partidas_existentes = partida_svc.obter_partidas_sorteio(sorteio_id)
        foto_antiga_url = (partidas_existentes[0].get('card_campeao_url') if partidas_existentes else None)
        if not foto_antiga_url:
            partida_v = votacao_svc.obter_por_sorteio(sorteio_id)
            if partida_v:
                foto_antiga_url = partida_v.get('card_campeao_url')

        nova_url = None

        if remover_foto:
            nova_url = "sem_foto"
            if foto_antiga_url:
                upload_svc.remover_card_campeao(foto_antiga_url)
        elif file_storage or base64_data:
            nova_url = upload_svc.processar_foto_campeao(
                file_storage=file_storage,
                base64_data=base64_data,
                sorteio_id=str(sorteio_id),
                foto_antiga_url=foto_antiga_url
            )
        else:
            msg_erro = "Selecione uma imagem ou foto válida para enviar."
            if request.is_json or json_data:
                return jsonify({'sucesso': False, 'erro': msg_erro}), 400
            flash(msg_erro, 'warning')
            return redirect(request.referrer or url_for('partida.historico'))

        # 2. Atualiza no partida_service
        partida_svc.atualizar_foto_campeao(sorteio_id, nova_url)

        # 3. Atualiza no votacao_service se houver
        partida_votacao = votacao_svc.obter_por_sorteio(sorteio_id)
        if partida_votacao:
            partida_votacao['card_campeao_url'] = nova_url
            dados = votacao_svc._carregar()
            alvo = votacao_svc._find_partida_em_dados(dados, partida_votacao['id'])
            if alvo:
                alvo['card_campeao_url'] = nova_url
                if alvo.get('resultado_partida'):
                    alvo['resultado_partida']['card_campeao_url'] = nova_url
                votacao_svc._salvar(dados)

        # 4. Limpa caches globais em memória
        clear_db_cache()
        JogadorStatsService.invalidar_cache_stats()

        # 5. Apaga a foto antiga de forma segura se a nova foi salva com sucesso e a foto antiga for diferente
        if foto_antiga_url and foto_antiga_url != nova_url and foto_antiga_url != "sem_foto":
            upload_svc.remover_card_campeao(foto_antiga_url)

        msg_sucesso = f"Foto do Sorteio #{sorteio_id} atualizada com sucesso!"
        if request.is_json or json_data:
            return jsonify({'sucesso': True, 'card_campeao_url': nova_url, 'mensagem': msg_sucesso})

        flash(msg_sucesso, 'success')
        return redirect(request.referrer or url_for('partida.historico', sucesso=msg_sucesso))

    except UploadError as ue:
        logger.warning("Erro de validação ao trocar foto do sorteio #%s: %s", sorteio_id, ue)
        if request.is_json:
            return jsonify({'sucesso': False, 'erro': str(ue)}), 400
        flash(f"Erro ao enviar foto: {str(ue)}", 'danger')
        return redirect(url_for('partida.historico', erro=str(ue)))
    except Exception as e:
        logger.error("Erro inesperado ao trocar foto do sorteio #%s: %s", sorteio_id, e, exc_info=True)
        if request.is_json:
            return jsonify({'sucesso': False, 'erro': 'Erro interno ao processar a substituição de foto'}), 500
        flash("Erro ao processar a substituição de foto.", 'danger')
        return redirect(url_for('partida.historico', erro='Erro ao processar a substituição de foto.'))


@partida_bp.route('/api/sorteio/<sorteio_id>/times', methods=['POST'])
@admin_or_juiz_required
def atualizar_times_sorteio(sorteio_id):
    """Atualiza composição dos times de um sorteio (troca manual pelo juiz), suportando rascunhos e oficial."""
    try:
        sorteio = None
        is_rascunho = False

        if str(sorteio_id).lower() == 'rascunho' or str(sorteio_id) == '0':
            from services.juiz_partida_service import JuizPartidaService
            juiz_svc = JuizPartidaService()
            rascunho = juiz_svc.obter_rascunho()
            if rascunho:
                is_rascunho = True
                sorteio = {
                    'id': 'rascunho',
                    'is_rascunho': True,
                    'times': rascunho.get('times', []),
                    'num_times': rascunho.get('num_times', len(rascunho.get('times', []))),
                    'pontuacoes': rascunho.get('somas', []),
                    'diferenca': rascunho.get('diferenca', 0),
                }
        else:
            try:
                s_id_int = int(sorteio_id)
                sorteio = historico_service.obter_sorteio(s_id_int)
            except (ValueError, TypeError):
                sorteio = None

        if not sorteio:
            return jsonify({'sucesso': False, 'erro': 'Sorteio não encontrado'}), 404

        dados = request.get_json(silent=True) or {}
        times_recebidos = dados.get('times', [])
        if not isinstance(times_recebidos, list) or not times_recebidos:
            return jsonify({'sucesso': False, 'erro': 'Payload de times inválido'}), 400

        times_originais = sorteio.get('times', []) or []
        if len(times_recebidos) != len(times_originais):
            return jsonify({'sucesso': False, 'erro': 'Quantidade de times inválida'}), 400

        def _player_key(jogador):
            player_id = jogador.get('id')
            if player_id is not None and str(player_id).strip() != '' and str(player_id).strip().lower() != 'none':
                return str(player_id)
            return f"{jogador.get('nome', '')}|{jogador.get('nivel', '')}|{jogador.get('posicao', '')}"

        jogadores_por_chave = {}
        chaves_originais = []
        tamanhos_originais = []
        for time in times_originais:
            jogadores_time = time.get('jogadores', []) or []
            tamanhos_originais.append(len(jogadores_time))
            for jogador in jogadores_time:
                chave = _player_key(jogador)
                jogadores_por_chave[chave] = jogador
                chaves_originais.append(chave)

        chaves_recebidas = []
        times_atualizados = []
        for idx, time in enumerate(times_recebidos):
            chaves_time = time.get('jogadores', []) or []
            if len(chaves_time) != tamanhos_originais[idx]:
                return jsonify({'sucesso': False, 'erro': 'Quantidade de jogadores por time inválida'}), 400

            jogadores_time = []
            for chave in chaves_time:
                chave_norm = str(chave)
                jogador = jogadores_por_chave.get(chave_norm)
                if not jogador:
                    return jsonify({'sucesso': False, 'erro': 'Jogador inválido na troca'}), 400
                jogadores_time.append(jogador)
                chaves_recebidas.append(chave_norm)

            times_atualizados.append({
                'numero': idx + 1,
                'jogadores': jogadores_time,
                'soma': round(sum(float(j.get('nivel', 0) or 0) for j in jogadores_time), 2),
            })

        if sorted(chaves_recebidas) != sorted(chaves_originais):
            return jsonify({'sucesso': False, 'erro': 'Os jogadores do sorteio foram alterados de forma inválida'}), 400

        if is_rascunho:
            from services.juiz_partida_service import JuizPartidaService
            sorteio_atualizado = JuizPartidaService().atualizar_rascunho_times(times_atualizados)
        else:
            sorteio_atualizado = historico_service.atualizar_times_sorteio(int(sorteio_id), times_atualizados)

        if not sorteio_atualizado:
            return jsonify({'sucesso': False, 'erro': 'Não foi possível salvar as alterações'}), 500

        # Mantém exportação/compartilhamento alinhados com a versão editada.
        _salvar_ultimo_sorteio_sessao({
            'sorteio_id': sorteio_atualizado.get('id'),
            'times': sorteio_atualizado.get('times', []),
            'num_times': len(times_atualizados),
            'somas': [t.get('soma', 0) for t in times_atualizados],
            'diferenca': round(max([t.get('soma', 0) for t in times_atualizados]) - min([t.get('soma', 0) for t in times_atualizados]), 2) if times_atualizados else 0,
        })
        clear_db_cache()
        JogadorStatsService.invalidar_cache_stats()

        return jsonify({'sucesso': True, 'sorteio': sorteio_atualizado})
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao atualizar times do sorteio: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao salvar alterações dos times'}), 500


@partida_bp.route('/sorteio/<int:sorteio_id>/compartilhar')
@admin_or_juiz_required
def compartilhar_sorteio(sorteio_id):
    """Central enxuta de compartilhamento do sorteio mais recente."""
    sorteio = historico_service.obter_sorteio(sorteio_id)
    if not sorteio:
        return render_template('historico.html', sorteios=[], resumo=_resumo_historico_vazio(), erro="Sorteio não encontrado"), 404

    sorteio_data = {
        'sorteio_id': sorteio.get('id'),
        'times': sorteio.get('times', []),
        'num_times': sorteio.get('num_times', 0),
        'somas': sorteio.get('pontuacoes', []),
        'diferenca': sorteio.get('diferenca', 0),
    }
    _salvar_ultimo_sorteio_sessao(sorteio_data)
    return render_template(
        'juiz_compartilhar.html',
        sorteio=sorteio,
        usuario=_usuario_logado(),
    )


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
            return render_template('historico.html', sorteios=[], resumo=_resumo_historico_vazio(), erro="Sorteio não encontrado"), 404

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
        return render_template('historico.html', sorteios=[], resumo=_resumo_historico_vazio(), erro='Erro ao carregar'), 500


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
            'proximo_passo_url': url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id, sucesso='Resultado registrado. Agora abra a votacao.') if _is_juiz() else url_for('admin.admin_page', sorteio_id=sorteio_id)
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao registrar resultado: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao registrar resultado'}), 500

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

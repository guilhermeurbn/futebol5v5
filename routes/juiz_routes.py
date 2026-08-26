"""
Rotas do Fluxo do Juiz
- Criar partida, finalizar partida, seleção de jogadores
"""
from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify, flash
from functools import wraps
import logging

from services.jogador_service import JogadorService
from services.juiz_partida_service import JuizPartidaService
from services.historico_service import HistoricoService
from services.partida_service import PartidaService
from services.votacao_service import VotacaoService
from services.db import clear_db_cache
from services.jogador_stats_service import JogadorStatsService

juiz_bp = Blueprint('juiz', __name__)
logger = logging.getLogger(__name__)

jogador_service = JogadorService()
juiz_partida_service = JuizPartidaService()
historico_service = HistoricoService()
partida_service = PartidaService()
votacao_service = VotacaoService()


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


def _is_juiz():
    return session.get('role') == 'juiz'


def juiz_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login_page'))
        from routes.auth_routes import _usuario_sem_email
        if _usuario_sem_email(user_id):
            return redirect(url_for('auth.completar_email_page'))
        if not _is_juiz():
            return redirect(url_for('jogador_crud.index'))
        return f(*args, **kwargs)
    return wrapper


def _sincronizar_fluxo_juiz():
    """Sincroniza estado do fluxo com dados persistidos"""
    estado = juiz_partida_service.obter_estado()
    partida_atual = estado.get('partida_atual') or {}

    from services.votacao_service import VotacaoService
    vot_svc = VotacaoService()

    # Auto-recuperar apenas se o juiz estiver num fluxo ativo (não idle)
    status = estado.get('status') or 'idle'
    if status != 'idle' and (not partida_atual or not partida_atual.get('votacao_aberta')):
        votacoes = vot_svc.listar()
        abertas = [v for v in votacoes if v.get('status') == 'aberta']
        for v_aberta in abertas:
            s_id = v_aberta.get('sorteio_id')
            if s_id and not historico_service.obter_sorteio(s_id):
                # O sorteio foi apagado do histórico: excluir votação órfã
                try:
                    vot_svc.deletar_votacao_do_sorteio(s_id)
                except Exception:
                    pass
                continue

            if s_id:
                juiz_partida_service.iniciar_partida()
                juiz_partida_service.marcar_resultado_registrado(s_id)
                juiz_partida_service.marcar_votacao_aberta(s_id, v_aberta.get('id'))
                return juiz_partida_service.obter_estado()

    if not partida_atual:
        return estado

    sorteio_id = partida_atual.get('sorteio_id')
    votacao_partida_id = partida_atual.get('votacao_partida_id')

    if not votacao_partida_id and sorteio_id:
        v_partida = vot_svc.obter_por_sorteio(sorteio_id)
        if v_partida:
            votacao_partida_id = v_partida.get('id')
            juiz_partida_service.marcar_resultado_registrado(sorteio_id)
            juiz_partida_service.marcar_votacao_aberta(sorteio_id, votacao_partida_id)
            estado = juiz_partida_service.obter_estado()
            partida_atual = estado.get('partida_atual') or {}

    if sorteio_id and not partida_atual.get('resultado_registrado'):
        resultado = _obter_resultado_sorteio(sorteio_id)
        if resultado:
            juiz_partida_service.marcar_resultado_registrado(sorteio_id, resultado.get('id'))
            estado = juiz_partida_service.obter_estado()
            partida_atual = estado.get('partida_atual') or {}
            votacao_partida_id = partida_atual.get('votacao_partida_id')

    if votacao_partida_id:
        partida_votacao = vot_svc.obter_partida(votacao_partida_id)
        
        if partida_votacao and partida_votacao.get('status') == 'aberta' and estado.get('status') != 'votacao_aberta':
            juiz_partida_service.marcar_votacao_aberta(
                partida_votacao.get('sorteio_id'),
                partida_votacao.get('id')
            )
            estado = juiz_partida_service.obter_estado()
        elif partida_votacao and partida_votacao.get('status') == 'encerrada':
            juiz_partida_service.finalizar_partida(_resumo_encerramento_para_juiz(partida_votacao))
            try:
                jogador_service.limpar_presenca()
            except Exception:
                pass
            estado = juiz_partida_service.obter_estado()

    return estado


def _obter_resultado_sorteio(sorteio_id):
    """Obtém resultado da última partida de um sorteio"""
    partidas = partida_service.obter_partidas_sorteio(sorteio_id)
    if not partidas:
        return None
    partidas_ordenadas = sorted(partidas, key=lambda item: (item.get('data', ''), item.get('id', 0)), reverse=True)
    return partidas_ordenadas[0] if partidas_ordenadas else None


def _resumo_encerramento_para_juiz(partida):
    """Cria resumo de encerramento compatível com o serviço"""
    if not partida:
        return None
    ranking = partida.get('ranking') or {}
    return {
        'titulo': partida.get('titulo'),
        'sorteio_id': partida.get('sorteio_id'),
        'partida_id': partida.get('id'),
        'encerrado_em': partida.get('encerrado_em'),
        'resultado_resumido': partida.get('resultado_resumido', []),
        'melhor_jogador': ranking.get('melhor_jogador'),
        'melhor_time': ranking.get('melhor_time'),
        'total_votos': ranking.get('total_votos', 0),
        'pendentes': ranking.get('participantes_pendentes', []),
        'ranking_top5': (ranking.get('ranking_jogadores') or [])[:5],
    }


def _destino_fluxo_juiz(estado):
    """Determina para onde o juiz deve ir no fluxo"""
    partida_atual = (estado or {}).get('partida_atual') or {}
    status = (estado or {}).get('status') or 'idle'

    if status == 'selecionando':
        return None

    sorteio_id = partida_atual.get('sorteio_id')
    votacao_partida_id = partida_atual.get('votacao_partida_id')

    if status == 'sorteada' and sorteio_id:
        return url_for('juiz.juiz_times_page', sorteio_id=sorteio_id)
    if status == 'resultado_registrado' and sorteio_id:
        return url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id)
    if status == 'votacao_aberta' and sorteio_id:
        return url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id)
    if votacao_partida_id and sorteio_id:
        return url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id)
    if votacao_partida_id:
        return url_for('votacao.votacao_admin_page')
    return None


def _destino_partida_oficial_aberta(estado):
    """Retorna destino da partida aberta apenas quando ja existe sorteio."""
    partida_atual = (estado or {}).get('partida_atual') or {}
    status = (estado or {}).get('status') or 'idle'
    if status == 'selecionando':
        return None
    if not partida_atual.get('sorteio_id'):
        return None
    return _destino_fluxo_juiz(estado)


def _salvar_ultimo_sorteio_sessao(payload):
    session['ultimo_sorteio'] = payload
    session.modified = True


def _resolver_sorteio_juiz(sorteio_id_hint=None):
    """Resolve sorteio dando prioridade ao rascunho temporário do juiz, depois ao histórico."""
    if sorteio_id_hint:
        try:
            s_id = int(sorteio_id_hint)
            s_obj = historico_service.obter_sorteio(s_id)
            if s_obj:
                return s_id, s_obj
        except (TypeError, ValueError):
            pass

    rascunho = juiz_partida_service.obter_rascunho()
    if rascunho:
        sorteio_draft = {
            'id': 'rascunho',
            'is_rascunho': True,
            'times': rascunho.get('times', []),
            'num_times': rascunho.get('num_times', len(rascunho.get('times', []))),
            'pontuacoes': rascunho.get('somas', []),
            'diferenca': rascunho.get('diferenca', 0),
            'total_jogadores': rascunho.get('total_jogadores', 0),
        }
        return 'rascunho', sorteio_draft

    estado = juiz_partida_service.obter_estado()
    sorteio_fluxo = ((estado.get('partida_atual') or {}).get('sorteio_id'))
    if sorteio_fluxo:
        try:
            s_id = int(sorteio_fluxo)
            s_obj = historico_service.obter_sorteio(s_id)
            if s_obj:
                return s_id, s_obj
        except (TypeError, ValueError):
            pass

    sorteios = historico_service.listar_sorteios() or []
    if sorteios:
        sorteio_recente = max(sorteios, key=lambda s: int(s.get('id', 0) or 0))
        s_id = int(sorteio_recente.get('id', 0) or 0)
        return s_id, sorteio_recente

    return None, None


# ============================================================
# FLUXO PRINCIPAL DO JUIZ
# ============================================================

@juiz_bp.route('/jogar/historico', methods=['GET'])
@juiz_required
def juiz_historico():
    """Lista os sorteios anteriores em uma pagina dedicada ao juiz."""
    try:
        sorteio_destaque_id = request.args.get('sorteio_id', type=int)
        sorteios = sorted(
            historico_service.listar_sorteios() or [],
            key=lambda item: int(item.get('id', 0) or 0),
            reverse=True
        )

        from routes.partida_routes import _enriquecer_sorteio_historico
        sorteios = [_enriquecer_sorteio_historico(item) for item in sorteios]

        estado = juiz_partida_service.obter_estado()
        sorteio_atual_id = ((estado.get('partida_atual') or {}).get('sorteio_id'))
        return render_template(
            'juiz_historico.html',
            sorteios=sorteios,
            sorteio_atual_id=sorteio_atual_id,
            sorteio_destaque_id=sorteio_destaque_id,
            usuario=_usuario_logado(),
        )
    except Exception as e:
        logger.error(f"Erro ao carregar histórico do juiz: {str(e)}")
        return render_template(
            'juiz_historico.html',
            sorteios=[],
            sorteio_destaque_id=None,
            erro='Erro ao carregar histórico do juiz',
            usuario=_usuario_logado(),
        ), 500


@juiz_bp.route('/jogar/times', methods=['GET'])
@juiz_required
def juiz_times_page():
    """Tela isolada de times do fluxo do juiz."""
    try:
        sorteio_id_hint = request.args.get('sorteio_id')
        sorteio_id, sorteio = _resolver_sorteio_juiz(sorteio_id_hint=sorteio_id_hint)
        if not sorteio:
            return redirect(url_for('juiz.jogar_page'))

        # Salva o sorteio na sessão para a API de exportação TXT
        _salvar_ultimo_sorteio_sessao({
            'sorteio_id': sorteio.get('id'),
            'times': sorteio.get('times', []),
            'num_times': sorteio.get('num_times', 0),
            'somas': sorteio.get('pontuacoes', []),
            'diferenca': sorteio.get('diferenca', 0),
        })

        estado_fluxo = _sincronizar_fluxo_juiz()
        partida_votacao = votacao_service.obter_por_sorteio(sorteio_id) if sorteio_id != 'rascunho' else None
        resultado_partida = _obter_resultado_sorteio(sorteio_id) if sorteio_id != 'rascunho' else None
        todos_jogadores = sorted(jogador_service.listar(), key=lambda j: (j.nome or '').lower())

        return render_template(
            'juiz_times.html',
            sorteio=sorteio,
            estado_fluxo=estado_fluxo,
            partida_votacao=partida_votacao,
            resultado_partida=resultado_partida,
            todos_jogadores=todos_jogadores,
            usuario=_usuario_logado(),
        )
    except Exception as e:
        logger.error(f"Erro ao carregar times do juiz: {str(e)}")
        return redirect(url_for('juiz.jogar_page'))


@juiz_bp.route('/jogar/compartilhar', methods=['GET'])
@juiz_required
def juiz_compartilhar_page():
    """Redireciona para a página de times unificada."""
    sorteio_id_hint = request.args.get('sorteio_id')
    if sorteio_id_hint:
        return redirect(url_for('juiz.juiz_times_page', sorteio_id=sorteio_id_hint, _anchor='acoes-sorteio'))
    return redirect(url_for('juiz.juiz_times_page', _anchor='acoes-sorteio'))


def _ids_iguais(val1, val2):
    if val1 is None or val2 is None:
        return False
    return str(val1).strip().lower() == str(val2).strip().lower()


@juiz_bp.route('/jogar/substituir-jogador', defaults={'sorteio_id': None}, methods=['POST'])
@juiz_bp.route('/jogar/substituir-jogador/<sorteio_id>', methods=['POST'])
@juiz_required
def juiz_substituir_jogador(sorteio_id=None):
    """Substitui 1 jogador específico de um sorteio com suporte total a UUIDs e rascunhos."""
    try:
        saindo_id_raw = request.form.get('saindo_id')
        entrando_id_raw = request.form.get('entrando_id')
        confirmar_goleiro_extra = request.form.get('confirmar_goleiro_extra', type=int) or 0

        if not saindo_id_raw or not entrando_id_raw:
            flash("Selecione o jogador que vai sair e o substituto.", "warning")
            return redirect(url_for('juiz.juiz_times_page'))

        if _ids_iguais(saindo_id_raw, entrando_id_raw):
            flash("O jogador que entra não pode ser o mesmo que vai sair.", "warning")
            return redirect(url_for('juiz.juiz_times_page'))

        sorteio_id_resolved, sorteio = _resolver_sorteio_juiz(sorteio_id_hint=sorteio_id if (sorteio_id and str(sorteio_id).isdigit()) else None)
        if not sorteio:
            flash("Sorteio não encontrado.", "danger")
            return redirect(url_for('juiz.jogar_page'))

        todos_jogadores = jogador_service.listar()
        novo_jogador_obj = next(
            (j for j in todos_jogadores if _ids_iguais(j.id, entrando_id_raw) or str(j.nome or '').strip().lower() == str(entrando_id_raw).strip().lower()),
            None
        )
        if not novo_jogador_obj:
            flash("Novo jogador não encontrado no cadastro.", "danger")
            return redirect(url_for('juiz.juiz_times_page'))

        # Regra 2: O jogador que entra NÃO pode ser um jogador que já está no sorteio
        ids_no_sorteio = set()
        for t in sorteio.get('times', []):
            for j in t.get('jogadores', []):
                if j.get('id'):
                    ids_no_sorteio.add(str(j['id']).strip().lower())
                if j.get('nome'):
                    ids_no_sorteio.add(str(j['nome']).strip().lower())

        novo_id_norm = str(novo_jogador_obj.id).strip().lower()
        novo_nome_norm = str(novo_jogador_obj.nome).strip().lower()
        if (novo_id_norm in ids_no_sorteio or novo_nome_norm in ids_no_sorteio) and not _ids_iguais(saindo_id_raw, novo_jogador_obj.id):
            flash("O jogador substituto já está escalado neste sorteio.", "warning")
            return redirect(url_for('juiz.juiz_times_page'))

        # Encontrar o time onde o jogador saindo está
        time_alvo = None
        saindo_jogador_dict = None
        for t in sorteio.get('times', []):
            for j in t.get('jogadores', []):
                if _ids_iguais(j.get('id'), saindo_id_raw) or str(j.get('nome') or '').strip().lower() == str(saindo_id_raw).strip().lower():
                    time_alvo = t
                    saindo_jogador_dict = j
                    break
            if time_alvo:
                break

        if not time_alvo or not saindo_jogador_dict:
            flash("Jogador a ser substituído não foi encontrado nas equipes.", "warning")
            return redirect(url_for('juiz.juiz_times_page'))

        # Regra 3: Se o jogador que entra for goleiro, verificar se o time alvo já possui outro goleiro
        novo_eh_goleiro = bool(getattr(novo_jogador_obj, 'goleiro', False)) or (getattr(novo_jogador_obj, 'posicao', '') or '').lower() == 'goleiro'
        if novo_eh_goleiro:
            goleiros_no_time = [
                j for j in time_alvo.get('jogadores', [])
                if not _ids_iguais(j.get('id'), saindo_id_raw) and not (str(j.get('nome') or '').strip().lower() == str(saindo_id_raw).strip().lower()) and (
                    bool(j.get('goleiro')) or (j.get('posicao') or '').lower() == 'goleiro'
                )
            ]
            if goleiros_no_time and not confirmar_goleiro_extra:
                time_num = time_alvo.get('numero', 1)
                flash(
                    f"⚠️ O Time {time_num} passará a ter mais de 1 goleiro ({novo_jogador_obj.nome} e {goleiros_no_time[0].get('nome')}). "
                    f"Confirme se aprova ou não.",
                    "warning"
                )
                return redirect(url_for('juiz.juiz_times_page', pedir_confirmacao_goleiro=1, saindo_id=saindo_id_raw, entrando_id=entrando_id_raw, time_num=time_num))

        substituido = False
        antigo_nome = saindo_jogador_dict.get('nome') or 'Jogador'
        times_atualizados = []

        for t in sorteio.get('times', []):
            novos_jogadores_time = []
            for j in t.get('jogadores', []):
                if _ids_iguais(j.get('id'), saindo_id_raw) or str(j.get('nome') or '').strip().lower() == str(saindo_id_raw).strip().lower():
                    substituido = True
                    novos_jogadores_time.append({
                        'id': novo_jogador_obj.id,
                        'nome': novo_jogador_obj.nome,
                        'nivel': float(getattr(novo_jogador_obj, 'nivel', 3.0) or 3.0),
                        'tipo': getattr(novo_jogador_obj, 'tipo', 'avulso') or 'avulso',
                        'goleiro': novo_eh_goleiro,
                        'posicao': 'goleiro' if novo_eh_goleiro else getattr(novo_jogador_obj, 'posicao', 'linha'),
                        'foto': getattr(novo_jogador_obj, 'foto_url', None) or getattr(novo_jogador_obj, 'foto', None)
                    })
                else:
                    novos_jogadores_time.append(j)
            times_atualizados.append({
                'numero': t.get('numero'),
                'jogadores': novos_jogadores_time
            })

        if not substituido:
            flash("Jogador a ser substituído não foi encontrado nas equipes.", "warning")
            return redirect(url_for('juiz.juiz_times_page'))

        # Se for rascunho, atualizar no rascunho temporário do juiz
        if sorteio.get('is_rascunho') or sorteio_id_resolved == 'rascunho':
            juiz_partida_service.atualizar_rascunho_times(times_atualizados)
        else:
            historico_service.atualizar_times_sorteio(sorteio_id_resolved, times_atualizados)

        clear_db_cache()
        JogadorStatsService.invalidar_cache_stats()

        flash(f"Substituição realizada com sucesso: {antigo_nome} ➔ {novo_jogador_obj.nome}", "success")
        return redirect(url_for('juiz.juiz_times_page'))
    except Exception as e:
        logger.error(f"Erro ao substituir jogador: {str(e)}")
        flash("Erro ao realizar substituição do jogador.", "danger")
        return redirect(url_for('juiz.juiz_times_page'))


@juiz_bp.route('/jogar/iniciar-rodada', defaults={'sorteio_id': None}, methods=['GET', 'POST'])
@juiz_bp.route('/jogar/iniciar-rodada/<sorteio_id>', methods=['GET', 'POST'])
@juiz_required
def juiz_iniciar_rodada(sorteio_id=None):
    """Oficializa o rascunho do sorteio e inicia a rodada do juiz."""
    try:
        sorteio_id = sorteio_id or request.form.get('sorteio_id')
        rascunho = juiz_partida_service.obter_rascunho()
        if rascunho:
            times = rascunho.get('times', [])
            somas = rascunho.get('somas', [])
            num_times = rascunho.get('num_times', len(times))
            diferenca = rascunho.get('diferenca', 0)

            # Adicionar novo registro oficial no histórico
            sorteio_oficial = historico_service.adicionar_sorteio(times, somas, num_times, diferenca)
            novo_id = sorteio_oficial.get('id')
            sorteio_oficial['rascunho'] = False
            sorteio_oficial['oficial'] = True
            historico_service.atualizar_times_sorteio(novo_id, times)

            juiz_partida_service.registrar_sorteio(novo_id)
            juiz_partida_service.marcar_resultado_registrado(novo_id)
            juiz_partida_service.limpar_rascunho()

            clear_db_cache()
            JogadorStatsService.invalidar_cache_stats()

            flash(f"Rodada #{novo_id} iniciada com sucesso! Lançamento de placar e votação liberados.", "success")
            return redirect(url_for('votacao.votacao_admin_page', sorteio_id=novo_id))
        else:
            if not sorteio_id or str(sorteio_id) == 'rascunho':
                sorteios = historico_service.listar_sorteios() or []
                if sorteios:
                    sorteio_recente = max(sorteios, key=lambda s: int(s.get('id', 0) or 0))
                    sorteio_id = sorteio_recente.get('id')

            if not sorteio_id:
                flash("Nenhum sorteio ativo para iniciar a rodada.", "warning")
                return redirect(url_for('juiz.jogar_page'))

            sorteio = historico_service.obter_sorteio(int(sorteio_id))
            if not sorteio:
                flash("Sorteio não encontrado.", "danger")
                return redirect(url_for('juiz.jogar_page'))

            sorteio['rascunho'] = False
            sorteio['oficial'] = True
            historico_service.atualizar_times_sorteio(int(sorteio_id), sorteio.get('times', []))
            juiz_partida_service.marcar_resultado_registrado(int(sorteio_id))

            clear_db_cache()
            JogadorStatsService.invalidar_cache_stats()

            flash(f"Rodada #{sorteio_id} iniciada com sucesso! Lançamento de placar e votação liberados.", "success")
            return redirect(url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id))
    except Exception as e:
        logger.error(f"Erro ao iniciar rodada {sorteio_id}: {str(e)}")
        flash("Erro ao iniciar a rodada.", "danger")
        return redirect(url_for('juiz.juiz_times_page'))


@juiz_bp.route('/jogar/trocar-jogadores/<int:sorteio_id>', methods=['GET', 'POST'])
@juiz_required
def juiz_trocar_jogadores(sorteio_id):
    """Permite ao juiz trocar/substituir jogadores de um sorteio ativo."""
    return redirect(url_for('juiz.juiz_times_page', sorteio_id=sorteio_id))


@juiz_bp.route('/jogar/cronometro', methods=['GET'])
@juiz_required
def juiz_cronometro():
    """Tela de cronometro para controle da partida pelo juiz."""
    try:
        estado = _sincronizar_fluxo_juiz()
        sorteio_atual_id = ((estado.get('partida_atual') or {}).get('sorteio_id'))
        if not sorteio_atual_id:
            sorteios = historico_service.listar_sorteios() or []
            maior_id = max((int(s.get('id', 0) or 0) for s in sorteios if isinstance(s, dict)), default=0)
            sorteio_atual_id = maior_id + 1
        return render_template(
            'juiz_cronometro.html',
            sorteio_atual_id=sorteio_atual_id,
            usuario=_usuario_logado(),
        )
    except Exception as e:
        logger.error(f"Erro ao carregar cronometro do juiz: {str(e)}")
        return render_template(
            'juiz_cronometro.html',
            sorteio_atual_id=None,
            erro='Erro ao carregar cronômetro',
            usuario=_usuario_logado(),
        ), 500


@juiz_bp.route('/jogar', methods=['GET'])
@juiz_required
def jogar_page():
    """Hub principal do fluxo do juiz"""
    try:
        estado_fluxo = _sincronizar_fluxo_juiz()
        if estado_fluxo and estado_fluxo.get('status') == 'selecionando':
            return redirect(url_for('juiz.juiz_criar_partida'))
        destino_aberto = _destino_partida_oficial_aberta(estado_fluxo)
        if destino_aberto:
            return redirect(destino_aberto)

        from services.presenca_service import PresencaService
        ps = PresencaService()

        todos_jogadores = jogador_service.listar()
        ultima_partida = estado_fluxo.get('ultima_partida_encerrada')
        return render_template(
            'juiz_home.html',
            todos_jogadores=todos_jogadores,
            total_jogadores=len(todos_jogadores),
            ultima_partida=ultima_partida,
            usuario=_usuario_logado(),
            proxima_terca_data=PresencaService.proxima_terca_feira(),
            presenca_resumo=ps.obter_resumo()
        )
    except Exception as e:
        logger.error(f"Erro ao carregar página do juiz: {str(e)}")
        return render_template('juiz_home.html', erro='Erro ao carregar página'), 500


@juiz_bp.route('/api/jogar/resumo', methods=['GET'])
@juiz_required
def api_jogar_resumo():
    """API: Resumo leve do painel do juiz."""
    try:
        estado_fluxo = _sincronizar_fluxo_juiz()
        todos_jogadores = jogador_service.listar()
        ultima_partida = estado_fluxo.get('ultima_partida_encerrada')

        return jsonify({
            'sucesso': True,
            'dados': {
                'total_jogadores': len(todos_jogadores),
                'total_presentes': len([j for j in todos_jogadores if j.presente]),
                'status_fluxo': estado_fluxo.get('status'),
                'ultima_partida': ultima_partida,
            }
        })
    except Exception as e:
        logger.error(f"Erro ao retornar resumo do juiz: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao retornar resumo'}), 500


# ============================================================
# CRIAR PARTIDA
# ============================================================

@juiz_bp.route('/jogar/criar-partida', methods=['GET', 'POST'])
@juiz_required
def juiz_criar_partida():
    """Inicia criação de partida"""
    try:
        novo_modo = request.args.get('novo', type=int) or request.args.get('trocar', type=int) or request.args.get('modo_edicao', type=int)
        estado_fluxo = _sincronizar_fluxo_juiz()
        if not novo_modo:
            destino_aberto = _destino_partida_oficial_aberta(estado_fluxo)
            if destino_aberto:
                return redirect(destino_aberto)

        if request.method == 'POST' or novo_modo:
            jogador_service.limpar_presenca()
            juiz_partida_service.iniciar_partida(session.get('user_id'))
        
        todos_jogadores = sorted(jogador_service.listar(), key=lambda j: j.nome.lower())
        fixos = [j for j in todos_jogadores if j.tipo == "fixo"]
        avulsos = [j for j in todos_jogadores if j.tipo == "avulso"]

        # Carregar inscrições de presença confirmadas via app
        from services.presenca_service import PresencaService
        ps = PresencaService()
        presenca_resumo = ps.obter_resumo()
        confirmados_respostas = presenca_resumo.get("confirmados", [])

        confirmados_ids = []
        for c in confirmados_respostas:
            u_id = str(c.get("user_id", ""))
            u_nome = (c.get("nome") or "").strip().lower()
            for j in todos_jogadores:
                j_owner = str(j.owner_user_id) if j.owner_user_id else ""
                j_nome = (j.nome or "").strip().lower()
                if (u_id and j_owner and u_id == j_owner) or (u_nome and u_nome == j_nome):
                    if j.id not in confirmados_ids:
                        confirmados_ids.append(j.id)
                    break

        presentes = [j for j in todos_jogadores if j.presente]

        return render_template(
            'juiz_criar_partida.html',
            todos_jogadores=todos_jogadores,
            fixos=fixos,
            avulsos=avulsos,
            presentes=presentes,
            total_presentes=len(presentes),
            total_jogadores=len(todos_jogadores),
            confirmados_ids=confirmados_ids,
            total_confirmados_inscritos=len(confirmados_ids),
            presenca_resumo=presenca_resumo,
            usuario=_usuario_logado()
        )
    except Exception as e:
        logger.error(f"Erro ao criar partida: {str(e)}")
        return render_template('juiz_home.html', erro='Erro ao criar partida'), 500


# ============================================================
# FINALIZAR PARTIDA
# ============================================================

@juiz_bp.route('/jogar/finalizar', methods=['POST'])
@juiz_required
def juiz_finalizar_partida():
    """Finaliza manualmente a partida quando não houve votação"""
    try:
        estado = juiz_partida_service.obter_estado()
        partida_atual = estado.get('partida_atual') or {}
        
        if not partida_atual:
            return redirect(url_for('juiz.jogar_page', erro='Nenhuma partida ativa para finalizar'))

        if not partida_atual.get('resultado_registrado'):
            return redirect(url_for('juiz.jogar_page', erro='Resultado não registrado; não é possível finalizar'))

        if partida_atual.get('votacao_partida_id') and not partida_atual.get('votacao_aberta'):
            return redirect(url_for('juiz.jogar_page', erro='A rodada ainda não foi liberada para votação'))

        sorteio_id = partida_atual.get('sorteio_id')
        resultado = _obter_resultado_sorteio(sorteio_id) if sorteio_id else None

        # Construir resumo
        import datetime
        resumo = {
            'titulo': f"Partida (sorteio {sorteio_id})" if sorteio_id else 'Partida',
            'sorteio_id': sorteio_id,
            'partida_id': resultado.get('id') if resultado else None,
            'encerrado_em': datetime.datetime.now().isoformat(),
            'resultado_resumido': [],
            'melhor_jogador': None,
            'melhor_time': None,
            'total_votos': 0,
            'pendentes': [],
            'ranking_top5': []
        }

        if resultado:
            gols = resultado.get('gols_times', []) or []
            desempenho = resultado.get('times_desempenho', []) or []
            resumo_res = []
            
            for idx, gols_time in enumerate(gols, start=1):
                item_des = next((t for t in desempenho if int(t.get('time_numero', 0) or 0) == idx), {})
                resumo_res.append({
                    'time_numero': idx,
                    'gols': int(gols_time or 0),
                    'vitorias': int(item_des.get('vitorias', 0) or 0),
                    'empates': int(item_des.get('empates', 0) or 0),
                    'derrotas': int(item_des.get('derrotas', 0) or 0),
                    'resultado': (
                        'vitoria' if (resultado.get('time_vencedor') and int(resultado.get('time_vencedor')) == idx)
                        else 'empate' if not resultado.get('time_vencedor') else 'derrota'
                    )
                })
            resumo['resultado_resumido'] = resumo_res

        juiz_partida_service.finalizar_partida(resumo)
        jogador_service.limpar_presenca()
        
        return redirect(url_for('juiz.jogar_page'))
    except Exception as e:
        logger.error(f"Erro ao finalizar partida: {str(e)}")
        return redirect(url_for('juiz.jogar_page', erro='Erro ao finalizar'))

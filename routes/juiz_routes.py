"""
Rotas do Fluxo do Juiz
- Criar partida, finalizar partida, seleção de jogadores
"""
from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify
from functools import wraps
import logging

from services.jogador_service import JogadorService
from services.juiz_partida_service import JuizPartidaService
from services.historico_service import HistoricoService
from services.partida_service import PartidaService
from services.votacao_service import VotacaoService

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

    if not partida_atual:
        return estado

    sorteio_id = partida_atual.get('sorteio_id')
    votacao_partida_id = partida_atual.get('votacao_partida_id')

    if sorteio_id and not partida_atual.get('resultado_registrado'):
        resultado = _obter_resultado_sorteio(sorteio_id)
        if resultado:
            juiz_partida_service.marcar_resultado_registrado(sorteio_id, resultado.get('id'))
            estado = juiz_partida_service.obter_estado()
            partida_atual = estado.get('partida_atual') or {}
            votacao_partida_id = partida_atual.get('votacao_partida_id')

    if votacao_partida_id:
        from services.votacao_service import VotacaoService
        votacao_service = VotacaoService()
        partida_votacao = votacao_service.obter_partida(votacao_partida_id)
        
        if partida_votacao and partida_votacao.get('status') == 'aberta' and estado.get('status') != 'votacao_aberta':
            juiz_partida_service.marcar_votacao_aberta(
                partida_votacao.get('sorteio_id'),
                partida_votacao.get('id')
            )
            estado = juiz_partida_service.obter_estado()
        elif partida_votacao and partida_votacao.get('status') != 'aberta':
            juiz_partida_service.finalizar_partida(_resumo_encerramento_para_juiz(partida_votacao))
            jogador_service.limpar_presenca()
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
    """Resolve sorteio prioritariamente pelo hint, depois fluxo atual, depois último histórico."""
    sorteio_id = None

    if sorteio_id_hint:
        try:
            sorteio_id = int(sorteio_id_hint)
        except (TypeError, ValueError):
            sorteio_id = None

    estado = juiz_partida_service.obter_estado()
    sorteio_fluxo = ((estado.get('partida_atual') or {}).get('sorteio_id'))
    if not sorteio_id and sorteio_fluxo:
        try:
            sorteio_id = int(sorteio_fluxo)
        except (TypeError, ValueError):
            sorteio_id = None

    if not sorteio_id:
        sorteios = historico_service.listar_sorteios() or []
        if sorteios:
            sorteio_recente = max(sorteios, key=lambda s: int(s.get('id', 0) or 0))
            sorteio_id = int(sorteio_recente.get('id', 0) or 0)

    if not sorteio_id:
        return None, None

    return sorteio_id, historico_service.obter_sorteio(sorteio_id)


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
            reverse=True,
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
        logger.error(f"Erro ao carregar historico do juiz: {str(e)}")
        return render_template(
            'juiz_historico.html',
            sorteios=[],
            sorteio_atual_id=None,
            sorteio_destaque_id=None,
            erro='Erro ao carregar histórico',
            usuario=_usuario_logado(),
        ), 500


@juiz_bp.route('/jogar/times', methods=['GET'])
@juiz_required
def juiz_times_page():
    """Tela isolada de times do fluxo do juiz."""
    try:
        sorteio_id_hint = request.args.get('sorteio_id', type=int)
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

        partida_votacao = votacao_service.obter_por_sorteio(sorteio_id)
        resultado_partida = _obter_resultado_sorteio(sorteio_id)

        return render_template(
            'juiz_times.html',
            sorteio=sorteio,
            partida_votacao=partida_votacao,
            resultado_partida=resultado_partida,
            usuario=_usuario_logado(),
        )
    except Exception as e:
        logger.error(f"Erro ao carregar times do juiz: {str(e)}")
        return redirect(url_for('juiz.jogar_page'))


@juiz_bp.route('/jogar/compartilhar', methods=['GET'])
@juiz_required
def juiz_compartilhar_page():
    """Redireciona para a página de times unificada."""
    sorteio_id_hint = request.args.get('sorteio_id', type=int)
    if sorteio_id_hint:
        return redirect(url_for('juiz.juiz_times_page', sorteio_id=sorteio_id_hint, _anchor='acoes-sorteio'))
    return redirect(url_for('juiz.juiz_times_page', _anchor='acoes-sorteio'))


@juiz_bp.route('/jogar/trocar-jogadores/<int:sorteio_id>', methods=['GET', 'POST'])
@juiz_required
def juiz_trocar_jogadores(sorteio_id):
    """Permite ao juiz trocar/substituir jogadores de um sorteio ativo antes do resultado ser registrado."""
    try:
        resultado_partida = _obter_resultado_sorteio(sorteio_id)
        if resultado_partida:
            return redirect(url_for('juiz.juiz_times_page', sorteio_id=sorteio_id))

        sorteio = historico_service.obter_sorteio(sorteio_id)
        if not sorteio:
            return redirect(url_for('juiz.jogar_page'))

        todos_jogadores = jogador_service.listar()
        jogador_ids = []
        for t in sorteio.get('times', []):
            for j in t.get('jogadores', []):
                j_id = j.get('id')
                if j_id and any(p.id == j_id for p in todos_jogadores):
                    if j_id not in jogador_ids:
                        jogador_ids.append(j_id)
                elif j.get('nome'):
                    nome_norm = (j.get('nome') or '').strip().lower()
                    match = next((p for p in todos_jogadores if (p.nome or '').strip().lower() == nome_norm), None)
                    if match and match.id not in jogador_ids:
                        jogador_ids.append(match.id)

        if jogador_ids:
            jogador_service.marcar_presenca(jogador_ids)

        juiz_partida_service.iniciar_partida(session.get('user_id'))
        juiz_partida_service.registrar_selecao(len(jogador_ids), jogador_ids)

        return redirect(url_for('juiz.juiz_criar_partida', trocar=1))
    except Exception as e:
        logger.error(f"Erro ao trocar jogadores do sorteio {sorteio_id}: {str(e)}")
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
        trocar_modo = request.args.get('trocar', type=int) or request.args.get('modo_edicao', type=int)
        estado_fluxo = _sincronizar_fluxo_juiz()
        if not trocar_modo:
            destino_aberto = _destino_partida_oficial_aberta(estado_fluxo)
            if destino_aberto:
                return redirect(destino_aberto)

        if request.method == 'POST':
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

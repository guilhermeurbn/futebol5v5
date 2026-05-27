"""
Rotas de Votação
- Votação de usuários e votação admin
"""
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, session
from functools import wraps
import logging

from services.votacao_service import VotacaoService
from services.auth_service import AuthService
from services.juiz_partida_service import JuizPartidaService
from services.historico_service import HistoricoService

votacao_bp = Blueprint('votacao', __name__)
logger = logging.getLogger(__name__)

votacao_service = VotacaoService()
auth_service = AuthService()
juiz_partida_service = JuizPartidaService()
historico_service = HistoricoService()


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


def _resposta_voto_somente_usuario():
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': 'Apenas usuarios podem votar'}), 403
    return redirect(url_for('jogador_crud.index'))


def _resolver_contexto_admin(sorteio_id_hint=None):
    """Monta contexto unificado da tela admin para evitar perdas em fluxos de erro."""
    ativa = votacao_service.obter_ativa()
    historico = votacao_service.listar()[:30]

    sorteios = historico_service.listar_sorteios() or []
    sorteios_ordenados = sorted(sorteios, key=lambda s: int(s.get('id', 0) or 0), reverse=True)

    fluxo_partida = None
    if _is_juiz():
        estado = juiz_partida_service.obter_estado()
        fluxo_partida = estado.get('partida_atual')

    selecionado = sorteio_id_hint
    if not selecionado and fluxo_partida:
        selecionado = fluxo_partida.get('sorteio_id')
    if not selecionado and ativa:
        selecionado = ativa.get('sorteio_id')
    if not selecionado and sorteios_ordenados:
        selecionado = sorteios_ordenados[0].get('id')

    sorteio_contexto = None
    if selecionado:
        try:
            selecionado = int(selecionado)
            sorteio_contexto = next((s for s in sorteios_ordenados if int(s.get('id', 0) or 0) == selecionado), None)
        except (TypeError, ValueError):
            selecionado = None

    voted_user_ids = {
        voto.get('user_id')
        for voto in (ativa or {}).get('votos', [])
        if voto.get('user_id')
    }

    pode_abrir_votacao = bool(selecionado)
    if _is_juiz() and fluxo_partida and not fluxo_partida.get('resultado_registrado'):
        pode_abrir_votacao = False

    return {
        'ativa': ativa,
        'historico': historico,
        'sorteios_disponiveis': sorteios_ordenados,
        'sorteio_contexto': sorteio_contexto,
        'selected_sorteio_id': selecionado,
        'fluxo_partida': fluxo_partida,
        'voted_user_ids': voted_user_ids,
        'pode_abrir_votacao': pode_abrir_votacao,
    }


# ============================================================
# VOTAÇÃO DE USUÁRIO
# ============================================================

@votacao_bp.route('/votacao', methods=['GET'])
def votacao_page():
    """Página para votação de usuários"""
    if _is_admin():
        return redirect(url_for('admin.admin_page'))

    if session.get('role') != 'usuario':
        return _resposta_voto_somente_usuario()

    try:
        partida = votacao_service.obter_ativa_para_usuario(session.get('user_id'))
        if not partida:
            return render_template('votacao_usuario.html', partida=None, voto=None, participante=None, usuario=_usuario_logado())

        participante = next(
            (p for p in partida.get('participantes', []) if p.get('user_id') == session.get('user_id')),
            None
        )
        voto = votacao_service.obter_voto_usuario(partida.get('id'), session.get('user_id'))
        jogadores_votaveis = partida.get('participantes', [])
        resultado_partida = partida.get('resultado_partida')
        
        return render_template(
            'votacao_usuario.html',
            partida=partida,
            participante=participante,
            voto=voto,
            jogadores_votaveis=jogadores_votaveis,
            resultado_partida=resultado_partida,
            usuario=_usuario_logado()
        )
    except Exception as e:
        logger.error(f"Erro ao carregar votação: {str(e)}")
        return render_template('votacao_usuario.html', erro='Erro ao carregar votação'), 500


@votacao_bp.route('/votacao/salvar', methods=['POST'])
def votacao_salvar():
    """Handler para salvar voto de usuário"""
    if _is_admin() or session.get('role') != 'usuario':
        return _resposta_voto_somente_usuario()

    partida_id = request.form.get('partida_id', type=int)
    try:
        nomes = request.form.getlist('jogador_nome')
        times = request.form.getlist('time_numero')
        notas = request.form.getlist('nota')

        votos_nao_zero = []
        for idx, nome in enumerate(nomes):
            nome = (nome or '').strip()
            if not nome:
                continue

            try:
                nota_valor = float((notas[idx] or '0').replace(',', '.'))
            except (ValueError, IndexError):
                nota_valor = 0.0

            try:
                time_numero = int(times[idx])
            except (ValueError, IndexError):
                time_numero = None

            item = {
                'jogador_nome': nome,
                'time_numero': time_numero,
                'nota': nota_valor
            }

            if nota_valor > 0:
                votos_nao_zero.append(item)

        if len(votos_nao_zero) < 5:
            raise ValueError('Voce precisa dar nota para pelo menos 5 jogadores')

        votos_obrigatorios = votos_nao_zero[:5]
        votos_extras = votos_nao_zero[5:]

        votacao_service.salvar_voto(
            partida_id=partida_id,
            user_id=session.get('user_id'),
            votos_obrigatorios=votos_obrigatorios,
            votos_extras=votos_extras
        )
        return redirect(url_for('votacao.votacao_page'))
    except ValueError as e:
        try:
            partida = votacao_service.obter_ativa_para_usuario(session.get('user_id'))
            participante = None
            voto = None
            jogadores_votaveis = partida.get('participantes', []) if partida else []
            resultado_partida = partida.get('resultado_partida') if partida else None
            if partida:
                participante = next(
                    (p for p in partida.get('participantes', []) if p.get('user_id') == session.get('user_id')),
                    None
                )
                voto = votacao_service.obter_voto_usuario(partida.get('id'), session.get('user_id'))
            return render_template(
                'votacao_usuario.html',
                partida=partida,
                participante=participante,
                voto=voto,
                jogadores_votaveis=jogadores_votaveis,
                resultado_partida=resultado_partida,
                erro=str(e),
                usuario=_usuario_logado()
            ), 400
        except Exception as inner_e:
            logger.error(f"Erro ao salvar voto: {str(inner_e)}")
            return render_template('votacao_usuario.html', erro='Erro ao salvar voto'), 500
    except Exception as e:
        logger.error(f"Erro ao salvar voto: {str(e)}")
        return render_template('votacao_usuario.html', erro='Erro ao salvar voto'), 500


# ============================================================
# VOTAÇÃO ADMIN/JUIZ
# ============================================================

@votacao_bp.route('/admin/votacao', methods=['GET'])
@admin_or_juiz_required
def votacao_admin_page():
    """Mantido por compatibilidade; redireciona para a central de rodada no admin."""
    sorteio_id = request.args.get('sorteio_id', type=int)
    sucesso = request.args.get('sucesso', '').strip()
    return redirect(url_for('admin.admin_page', sorteio_id=sorteio_id, sucesso=sucesso))


@votacao_bp.route('/admin/votacao/criar', methods=['POST'])
@admin_or_juiz_required
def votacao_admin_criar():
    """Cria nova votação"""
    try:
        titulo = (request.form.get('titulo', '') or '').strip()
        sorteio_id = request.form.get('sorteio_id', type=int)

        if not sorteio_id and _is_juiz():
            estado = juiz_partida_service.obter_estado()
            sorteio_id = ((estado.get('partida_atual') or {}).get('sorteio_id'))

        if not sorteio_id:
            sorteios = historico_service.listar_sorteios() or []
            if sorteios:
                sorteio_recente = max(sorteios, key=lambda s: int(s.get('id', 0) or 0))
                sorteio_id = sorteio_recente.get('id')

        sorteio = historico_service.obter_sorteio(int(sorteio_id)) if sorteio_id else None
        
        if not sorteio:
            contexto = _resolver_contexto_admin(sorteio_id_hint=sorteio_id)
            return render_template(
                'votacao_admin.html',
                **contexto,
                titulo_preenchido=titulo,
                erro='Nao ha sorteio no historico para iniciar votacao',
                usuario=_usuario_logado()
            ), 400

        usuarios = auth_service.listar_usuarios()
        
        from services.partida_service import PartidaService
        partida_service = PartidaService()
        
        def _obter_resultado_sorteio(sid):
            partidas = partida_service.obter_partidas_sorteio(sid)
            if not partidas:
                return None
            partidas_ordenadas = sorted(partidas, key=lambda item: (item.get('data', ''), item.get('id', 0)), reverse=True)
            return partidas_ordenadas[0] if partidas_ordenadas else None
        
        resultado_partida = _obter_resultado_sorteio(sorteio.get('id'))
        if _is_juiz() and not resultado_partida:
            raise ValueError('Registre o resultado da partida antes de abrir a votacao')

        partida_existente = votacao_service.obter_por_sorteio(sorteio.get('id'))
        if partida_existente and partida_existente.get('status') != 'aberta':
            raise ValueError('Esta rodada já foi encerrada e não pode abrir votação novamente')

        partida = votacao_service.criar_partida(
            times_json=sorteio.get('times', []),
            usuarios=usuarios,
            criado_por=session.get('user_id'),
            titulo=titulo,
            sorteio_id=sorteio.get('id'),
            resultado_partida=resultado_partida,
            duracao_horas=8,
        )
        
        if _is_juiz():
            juiz_partida_service.marcar_votacao_aberta(sorteio.get('id'), partida.get('id'))
        
        return redirect(url_for(
            'admin.admin_page',
            partida_id=partida.get('id'),
            sorteio_id=sorteio.get('id'),
            sucesso='Rodada aberta com sucesso.'
        ))
    except ValueError as e:
        sorteio_id_hint = request.form.get('sorteio_id', type=int)
        contexto = _resolver_contexto_admin(sorteio_id_hint=sorteio_id_hint)
        return render_template(
            'votacao_admin.html',
            **contexto,
            titulo_preenchido=(request.form.get('titulo', '') or '').strip(),
            erro=str(e),
            usuario=_usuario_logado()
        ), 400
    except Exception as e:
        logger.error(f"Erro ao criar votação: {str(e)}")
        sorteio_id_hint = request.form.get('sorteio_id', type=int)
        contexto = _resolver_contexto_admin(sorteio_id_hint=sorteio_id_hint)
        return render_template(
            'votacao_admin.html',
            **contexto,
            titulo_preenchido=(request.form.get('titulo', '') or '').strip(),
            erro='Erro ao criar votação',
            usuario=_usuario_logado()
        ), 500


@votacao_bp.route('/admin/votacao/<int:partida_id>/encerrar', methods=['POST'])
@admin_or_juiz_required
def votacao_admin_encerrar(partida_id):
    """Encerra votação e apura resultado"""
    try:
        partida_encerrada = votacao_service.encerrar_e_apurar(partida_id, session.get('user_id'))
        
        if _is_juiz():
            from services.jogador_service import JogadorService
            jogador_service = JogadorService()
            
            resumo = {
                'titulo': partida_encerrada.get('titulo'),
                'sorteio_id': partida_encerrada.get('sorteio_id'),
                'partida_id': partida_encerrada.get('id'),
                'encerrado_em': partida_encerrada.get('encerrado_em'),
                'resultado_resumido': partida_encerrada.get('resultado_resumido', []),
                'melhor_jogador': (partida_encerrada.get('ranking') or {}).get('melhor_jogador'),
                'melhor_time': (partida_encerrada.get('ranking') or {}).get('melhor_time'),
                'total_votos': (partida_encerrada.get('ranking') or {}).get('total_votos', 0),
                'pendentes': (partida_encerrada.get('ranking') or {}).get('participantes_pendentes', []),
                'ranking_top5': ((partida_encerrada.get('ranking') or {}).get('ranking_jogadores') or [])[:5],
            }
            
            juiz_partida_service.finalizar_partida(resumo)
            jogador_service.limpar_presenca()
            return redirect(url_for('juiz.jogar_page'))
        
        return redirect(url_for('admin.admin_page', partida_id=partida_id, sucesso='Rodada encerrada e ranking apurado.'))
    except ValueError as e:
        contexto = _resolver_contexto_admin()
        return render_template(
            'votacao_admin.html',
            **contexto,
            erro=str(e),
            usuario=_usuario_logado()
        ), 400
    except Exception as e:
        logger.error(f"Erro ao encerrar votação: {str(e)}")
        contexto = _resolver_contexto_admin()
        return render_template(
            'votacao_admin.html',
            **contexto,
            erro='Erro ao encerrar votação',
            usuario=_usuario_logado()
        ), 500

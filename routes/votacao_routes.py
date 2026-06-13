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
from services.partida_service import PartidaService

votacao_bp = Blueprint('votacao', __name__)
logger = logging.getLogger(__name__)

votacao_service = VotacaoService()
auth_service = AuthService()
juiz_partida_service = JuizPartidaService()
historico_service = HistoricoService()
partida_service = PartidaService()


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


def _resumo_encerramento(partida):
    ranking = (partida or {}).get('ranking') or {}
    return {
        'titulo': (partida or {}).get('titulo'),
        'sorteio_id': (partida or {}).get('sorteio_id'),
        'partida_id': (partida or {}).get('id'),
        'encerrado_em': (partida or {}).get('encerrado_em'),
        'resultado_resumido': (partida or {}).get('resultado_resumido', []),
        'melhor_jogador': ranking.get('melhor_jogador'),
        'melhor_time': ranking.get('melhor_time'),
        'total_votos': ranking.get('total_votos', 0),
        'pendentes': ranking.get('participantes_pendentes', []),
        'ranking_top5': (ranking.get('ranking_jogadores') or [])[:5],
    }


def _obter_resultado_sorteio(sorteio_id):
    partidas = partida_service.obter_partidas_sorteio(sorteio_id)
    if not partidas:
        return None
    return max(partidas, key=lambda item: (item.get('data', ''), item.get('id', 0)))


def _resolver_contexto_admin(sorteio_id_hint=None):
    """Monta contexto unificado da tela admin para evitar perdas em fluxos de erro."""
    ativa_global = votacao_service.obter_ativa()
    sorteios = historico_service.listar_sorteios() or []
    sorteios_ordenados = sorted(sorteios, key=lambda s: int(s.get('id', 0) or 0), reverse=True)

    fluxo_partida = None
    if _is_juiz():
        estado = juiz_partida_service.obter_estado()
        fluxo_partida = estado.get('partida_atual')

    selecionado = None
    if _is_juiz() and fluxo_partida and fluxo_partida.get('sorteio_id'):
        selecionado = fluxo_partida.get('sorteio_id')
    elif not _is_juiz():
        if sorteio_id_hint:
            selecionado = sorteio_id_hint
        elif ativa_global:
            selecionado = ativa_global.get('sorteio_id')
        elif sorteios_ordenados:
            selecionado = sorteios_ordenados[0].get('id')

    sorteio_contexto = None
    if selecionado:
        try:
            selecionado = int(selecionado)
            sorteio_contexto = next((s for s in sorteios_ordenados if int(s.get('id', 0) or 0) == selecionado), None)
        except (TypeError, ValueError):
            selecionado = None

    rodada_selecionada = votacao_service.obter_por_sorteio(selecionado) if selecionado else None
    ativa = (
        rodada_selecionada
        if rodada_selecionada and rodada_selecionada.get('status') == 'aberta'
        else None
    )
    if (
        _is_juiz()
        and fluxo_partida
        and fluxo_partida.get('votacao_partida_id')
        and rodada_selecionada
        and rodada_selecionada.get('status') == 'encerrada'
    ):
        juiz_partida_service.finalizar_partida(_resumo_encerramento(rodada_selecionada))
        fluxo_partida = None

    voted_user_ids = {
        voto.get('user_id')
        for voto in (ativa or {}).get('votos', [])
        if voto.get('user_id')
    }

    resultado_partida = _obter_resultado_sorteio(selecionado) if selecionado else None
    pode_abrir_votacao = bool(selecionado) and not rodada_selecionada and bool(resultado_partida)
    fluxo_corresponde = bool(
        fluxo_partida
        and selecionado
        and int(fluxo_partida.get('sorteio_id', 0) or 0) == int(selecionado)
    )
    if _is_juiz() and fluxo_partida and (not fluxo_corresponde or not resultado_partida):
        pode_abrir_votacao = False

    return {
        'ativa': ativa,
        'sorteios_disponiveis': sorteios_ordenados,
        'sorteio_contexto': sorteio_contexto,
        'selected_sorteio_id': selecionado,
        'fluxo_partida': fluxo_partida,
        'voted_user_ids': voted_user_ids,
        'pode_abrir_votacao': pode_abrir_votacao,
        'resultado_partida': resultado_partida,
        'rodada_selecionada': rodada_selecionada,
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

@votacao_bp.route('/admin/votacao/resultado', methods=['POST'])
@admin_or_juiz_required
def votacao_resultado_juiz():
    if not _is_juiz():
        return redirect(url_for('admin.admin_page'))

    sorteio_id = request.form.get('sorteio_id', type=int)
    try:
        contexto = _resolver_contexto_admin(sorteio_id_hint=sorteio_id)
        sorteio = contexto.get('sorteio_contexto')
        if not sorteio:
            raise ValueError('Crie uma partida antes de registrar o resultado')
        if contexto.get('rodada_selecionada'):
            raise ValueError('A votação desta partida já foi aberta')
        if contexto.get('resultado_partida'):
            raise ValueError('O resultado desta partida já foi registrado')

        estado = juiz_partida_service.obter_estado()
        partida_atual = estado.get('partida_atual') or {}
        if int(partida_atual.get('sorteio_id', 0) or 0) != int(sorteio_id or 0):
            raise ValueError('Este sorteio não pertence à partida atual do juiz')

        times_desempenho = []
        numeros_times = []
        for time in sorteio.get('times', []):
            try:
                numero = int(time.get('numero'))
                numeros_times.append(numero)
                item = {
                    'time_numero': numero,
                    'vitorias': int(request.form.get(f'vitorias_{numero}', 0)),
                    'empates': int(request.form.get(f'empates_{numero}', 0)),
                    'derrotas': int(request.form.get(f'derrotas_{numero}', 0)),
                    'gols': int(request.form.get(f'gols_{numero}', 0)),
                }
            except (TypeError, ValueError):
                raise ValueError('Use apenas números inteiros no resultado')
            if any(valor < 0 for chave, valor in item.items() if chave != 'time_numero'):
                raise ValueError('O resultado não pode ter números negativos')
            times_desempenho.append(item)

        if not numeros_times or len(set(numeros_times)) != len(numeros_times):
            raise ValueError('Os times deste sorteio são inválidos')

        total_vitorias = sum(item['vitorias'] for item in times_desempenho)
        total_empates = sum(item['empates'] for item in times_desempenho)
        total_jogos = total_vitorias + total_empates + sum(
            item['derrotas'] for item in times_desempenho
        )
        if total_jogos == 0:
            raise ValueError('Registre ao menos um jogo antes de continuar')
        if total_vitorias != sum(item['derrotas'] for item in times_desempenho):
            raise ValueError('O total de vitórias deve ser igual ao total de derrotas')
        empates_por_time = [item['empates'] for item in times_desempenho]
        if total_empates % 2 != 0 or max(empates_por_time, default=0) > total_empates / 2:
            raise ValueError('Cada empate deve aparecer para os dois times')

        gols_times = [item['gols'] for item in times_desempenho]
        maiores_vitorias = max(item['vitorias'] for item in times_desempenho)
        lideres = [
            item['time_numero']
            for item in times_desempenho
            if maiores_vitorias > 0 and item['vitorias'] == maiores_vitorias
        ]
        time_vencedor = lideres[0] if len(lideres) == 1 else None

        partida = partida_service.registrar_resultado(
            sorteio_id=sorteio_id,
            time_vencedor=time_vencedor,
            gols_times=gols_times,
            notas='',
            times_desempenho=times_desempenho,
        )
        juiz_partida_service.marcar_resultado_registrado(sorteio_id, partida.get('id'))
        return redirect(url_for(
            'votacao.votacao_admin_page',
            sorteio_id=sorteio_id,
            sucesso='Resultado salvo. Agora você pode abrir a votação dos jogadores.',
        ))
    except ValueError as e:
        contexto = _resolver_contexto_admin(sorteio_id_hint=sorteio_id)
        return render_template(
            'votacao_admin.html',
            **contexto,
            erro=str(e),
            usuario=_usuario_logado(),
        ), 400

@votacao_bp.route('/admin/votacao', methods=['GET'])
@admin_or_juiz_required
def votacao_admin_page():
    """Mantido por compatibilidade; redireciona para a central de rodada no admin."""
    sorteio_id = request.args.get('sorteio_id', type=int)
    sucesso = request.args.get('sucesso', '').strip()
    if _is_juiz():
        contexto = _resolver_contexto_admin(sorteio_id_hint=sorteio_id)
        return render_template(
            'votacao_admin.html',
            **contexto,
            sucesso=sucesso or None,
            usuario=_usuario_logado(),
        )
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
        
        resultado_partida = _obter_resultado_sorteio(sorteio.get('id'))
        if _is_juiz():
            estado = juiz_partida_service.obter_estado()
            fluxo_partida = estado.get('partida_atual') or {}
            if int(fluxo_partida.get('sorteio_id', 0) or 0) != int(sorteio.get('id')):
                raise ValueError('Este sorteio nao pertence a partida atual do juiz')
        if _is_juiz() and not resultado_partida:
            raise ValueError('Registre primeiro o resultado dos times')

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
            duracao_horas=12,
        )
        
        if _is_juiz():
            juiz_partida_service.marcar_votacao_aberta(sorteio.get('id'), partida.get('id'))
        
        if _is_juiz():
            return redirect(url_for('votacao.votacao_admin_page', sorteio_id=sorteio.get('id'), sucesso='Votacao aberta com sucesso.'))

        return redirect(url_for(
            'admin.admin_page',
            partida_id=partida.get('id'),
            sorteio_id=sorteio.get('id'),
            sucesso='Rodada aberta com sucesso.'
        ))
    except ValueError as e:
        if not _is_juiz():
            return redirect(url_for('admin.admin_page', erro=str(e)))
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
            
            juiz_partida_service.finalizar_partida(_resumo_encerramento(partida_encerrada))
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

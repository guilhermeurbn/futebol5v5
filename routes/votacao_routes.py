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
from services.upload_service import UploadService

votacao_bp = Blueprint('votacao', __name__)
logger = logging.getLogger(__name__)

votacao_service = VotacaoService()
auth_service = AuthService()
juiz_partida_service = JuizPartidaService()
historico_service = HistoricoService()
partida_service = PartidaService()
upload_service = UploadService()


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


def _resumo_ranking_encerrado(rodada):
    ranking = (rodada or {}).get('ranking') or {}
    ranking_jogadores = list(ranking.get('ranking_jogadores') or [])
    if ranking_jogadores:
        ranking_jogadores = sorted(
            ranking_jogadores,
            key=lambda x: (float(x.get('nota_media') or 0), float(x.get('pontos') or 0), int(x.get('votos') or 0)),
            reverse=True
        )

    media_geral = float(ranking.get('media_geral') or 0.0)
    if not media_geral and ranking_jogadores:
        votados = [float(item.get('nota_media', 0) or 0) for item in ranking_jogadores if int(item.get('votos', 0) or 0) > 0 or float(item.get('nota_media', 0) or 0) > 0]
        if votados:
            media_geral = round(sum(votados) / len(votados), 2)

    melhor_jog = ranking_jogadores[0] if ranking_jogadores else ranking.get('melhor_jogador')

    return {
        'ranking_jogadores': ranking_jogadores,
        'ranking_top10': ranking_jogadores,
        'media_geral': media_geral,
        'melhor_jogador': melhor_jog,
        'total_jogadores': len(ranking_jogadores),
    }


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
    else:
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

    voted_user_ids = set()
    for voto in (ativa or {}).get('votos', []):
        uid = voto.get('user_id')
        if uid is not None:
            voted_user_ids.add(uid)
            voted_user_ids.add(str(uid))
            try:
                voted_user_ids.add(int(uid))
            except (ValueError, TypeError):
                pass

    resultado_partida = _obter_resultado_sorteio(selecionado) if selecionado else None
    pode_abrir_votacao = bool(selecionado) and bool(resultado_partida)
    fluxo_corresponde = bool(
        fluxo_partida
        and selecionado
        and int(fluxo_partida.get('sorteio_id', 0) or 0) == int(selecionado)
    )
    if _is_juiz() and fluxo_partida and (not fluxo_corresponde or not resultado_partida):
        pode_abrir_votacao = False

    ranking_encerrado = _resumo_ranking_encerrado(rodada_selecionada) if rodada_selecionada else {
        'ranking_jogadores': [],
        'ranking_top10': [],
        'media_geral': 0.0,
        'melhor_jogador': None,
        'total_jogadores': 0,
    }

    maior_id = max((int(s.get('id', 0) or 0) for s in sorteios if isinstance(s, dict)), default=0)
    proximo_sorteio_num = int(selecionado) if selecionado else (maior_id + 1)

    if _is_juiz():
        rodada_iniciada = bool(
            fluxo_partida
            and (fluxo_partida.get('status') in ['resultado_registrado', 'votacao_aberta'])
        )
    else:
        rodada_iniciada = bool(
            sorteio_contexto
            and not sorteio_contexto.get('rascunho')
            and (
                (fluxo_partida and fluxo_partida.get('status') in ['resultado_registrado', 'votacao_aberta', 'encerrada'])
                or (resultado_partida is not None)
                or (rodada_selecionada is not None)
            )
        )

    if not rodada_iniciada and _is_juiz():
        resultado_partida = None
        pode_abrir_votacao = False

    card_campeao_url = (resultado_partida or {}).get('card_campeao_url') or (rodada_selecionada or {}).get('card_campeao_url')

    return {
        'ativa': ativa,
        'sorteios_disponiveis': sorteios_ordenados,
        'sorteio_contexto': sorteio_contexto,
        'selected_sorteio_id': selecionado,
        'proximo_sorteio_num': proximo_sorteio_num,
        'fluxo_partida': fluxo_partida,
        'voted_user_ids': voted_user_ids,
        'pode_abrir_votacao': pode_abrir_votacao,
        'resultado_partida': resultado_partida,
        'card_campeao_url': card_campeao_url,
        'resultado_concluido': bool(resultado_partida),
        'rodada_iniciada': rodada_iniciada,
        'rodada_selecionada': rodada_selecionada,
        'ranking_jogadores_encerrada': ranking_encerrado['ranking_jogadores'],
        'ranking_top10_encerrada': ranking_encerrado['ranking_top10'],
        'media_geral_jogadores': ranking_encerrado['media_geral'],
        'melhor_jogador_encerrada': ranking_encerrado['melhor_jogador'],
        'total_jogadores_votados': ranking_encerrado['total_jogadores'],
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
        current_user_id = session.get('user_id')
        partida = votacao_service.obter_ativa()
        if not partida:
            return render_template('votacao_usuario.html', partida=None, voto=None, participante=None, usuario=_usuario_logado())

        if not votacao_service.eh_participante(partida, current_user_id):
            return render_template(
                'votacao_usuario.html',
                partida=partida,
                participante=None,
                nao_participante=True,
                voto=None,
                usuario=_usuario_logado()
            )

        current_uid_str = str(current_user_id).strip() if current_user_id is not None else ""
        participante = next(
            (p for p in partida.get('participantes', []) if str(p.get('user_id')).strip() == current_uid_str),
            None
        )
        if not participante and _usuario_logado():
            u_logado = _usuario_logado()
            u_nome = (u_logado.get('nome') or '').strip().lower()
            u_uname = (u_logado.get('username') or '').strip().lower()
            participante = next(
                (p for p in partida.get('participantes', []) if (p.get('jogador_nome') or '').strip().lower() in [u_nome, u_uname]),
                None
            )

        voto = votacao_service.obter_voto_usuario(partida.get('id'), current_user_id)
        meu_nome = (participante.get('jogador_nome') if participante else '').strip()

        # Remove o próprio usuário/jogador das opções de voto (Anti-Self-Vote)
        jogadores_votaveis = [
            p for p in partida.get('participantes', [])
            if str(p.get('user_id')).strip() != current_uid_str and (p.get('jogador_nome') or '').strip() != meu_nome
        ]
        
        # Ordenar jogadores votáveis colocando o time campeão (com mais gols) primeiro
        resultado_resumido = partida.get('resultado_resumido') or []
        winning_team = None
        if resultado_resumido and isinstance(resultado_resumido, list) and len(resultado_resumido) >= 2:
            try:
                sorted_teams = sorted(resultado_resumido, key=lambda t: int((t or {}).get('gols', 0) or 0), reverse=True)
                if int((sorted_teams[0] or {}).get('gols', 0) or 0) > int((sorted_teams[1] or {}).get('gols', 0) or 0):
                    winning_team = (sorted_teams[0] or {}).get('time_numero')
            except Exception:
                pass

        if winning_team is not None:
            jogadores_votaveis = sorted(
                jogadores_votaveis,
                key=lambda p: (0 if p.get('time_numero') == winning_team else 1, int(p.get('time_numero', 0) or 0), (p.get('jogador_nome') or '').lower())
            )

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

        current_user_id = session.get('user_id')
        current_uid_str = str(current_user_id).strip() if current_user_id is not None else ""
        partida = votacao_service.obter_ativa()

        if not partida or not votacao_service.eh_participante(partida, current_user_id):
            return render_template(
                'votacao_usuario.html',
                partida=partida,
                participante=None,
                nao_participante=True,
                erro='Apenas os jogadores que participaram desta partida podem votar.'
            ), 403

        jogadores_votaveis = []
        if partida:
            participante_logado = next(
                (p for p in partida.get('participantes', []) if str(p.get('user_id')).strip() == current_uid_str),
                None
            )
            meu_nome = (participante_logado.get('jogador_nome') if participante_logado else '').strip()
            jogadores_votaveis = [
                p for p in partida.get('participantes', [])
                if str(p.get('user_id')).strip() != current_uid_str and (p.get('jogador_nome') or '').strip() != meu_nome
            ]
        
        min_esperado = min(5, len(jogadores_votaveis)) if jogadores_votaveis else 5

        if len(votos_nao_zero) < min_esperado:
            raise ValueError(f'Você precisa dar nota para pelo menos {min_esperado} jogador(es)')

        votos_obrigatorios = votos_nao_zero[:min_esperado]
        votos_extras = votos_nao_zero[min_esperado:]

        target_partida_id = partida_id or (partida.get('id') if partida else None)
        gols_marcados = request.form.get('gols_marcados', 0, type=int)

        votacao_service.salvar_voto(
            partida_id=target_partida_id,
            user_id=current_user_id,
            votos_obrigatorios=votos_obrigatorios,
            votos_extras=votos_extras,
            gols_marcados=gols_marcados
        )
        return redirect(url_for('votacao.votacao_page'))
    except ValueError as e:
        try:
            current_user_id = session.get('user_id')
            current_uid_str = str(current_user_id).strip() if current_user_id is not None else ""
            partida = votacao_service.obter_ativa_para_usuario(current_user_id)
            if not partida:
                partida = votacao_service.obter_ativa()
            participante = None
            voto = None
            jogadores_votaveis = []
            resultado_partida = partida.get('resultado_partida') if partida else None
            if partida:
                participante = next(
                    (p for p in partida.get('participantes', []) if str(p.get('user_id')).strip() == current_uid_str),
                    None
                )
                meu_nome = (participante.get('jogador_nome') if participante else '').strip()
                jogadores_votaveis = [
                    p for p in partida.get('participantes', [])
                    if str(p.get('user_id')).strip() != current_uid_str and (p.get('jogador_nome') or '').strip() != meu_nome
                ]
                voto = votacao_service.obter_voto_usuario(partida.get('id'), current_user_id)
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

        estado = juiz_partida_service.obter_estado()
        partida_atual = estado.get('partida_atual') or {}
        if not partida_atual or int(partida_atual.get('sorteio_id', 0) or 0) != int(sorteio_id or 0):
            juiz_partida_service.registrar_sorteio(sorteio_id)

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
        total_derrotas = sum(item['derrotas'] for item in times_desempenho)
        total_jogos = total_vitorias + total_empates + total_derrotas

        # Se V/E/D não foram fornecidos manualmente, infere a partir dos gols para 2 times
        if total_jogos == 0 and len(times_desempenho) == 2:
            t1, t2 = times_desempenho[0], times_desempenho[1]
            if t1['gols'] > t2['gols']:
                t1['vitorias'], t1['derrotas'] = 1, 0
                t2['vitorias'], t2['derrotas'] = 0, 1
            elif t2['gols'] > t1['gols']:
                t2['vitorias'], t2['derrotas'] = 1, 0
                t1['vitorias'], t1['derrotas'] = 0, 1
            else:
                t1['empates'], t2['empates'] = 1, 1

        gols_times = [item['gols'] for item in times_desempenho]
        maiores_vitorias = max(item['vitorias'] for item in times_desempenho)
        lideres = [
            item['time_numero']
            for item in times_desempenho
            if maiores_vitorias > 0 and item['vitorias'] == maiores_vitorias
        ]
        time_vencedor = lideres[0] if len(lideres) == 1 else None

        card_campeao_url = None
        foto_campeao_file = request.files.get('foto_campeao')
        card_campeao_base64 = request.form.get('card_campeao_base64')
        if card_campeao_base64 and isinstance(card_campeao_base64, str) and card_campeao_base64.startswith('data:image'):
            try:
                card_campeao_url = upload_service.processar_foto_campeao(base64_data=card_campeao_base64, sorteio_id=sorteio_id)
            except Exception as exc:
                logger.warning("Falha ao processar card do campeao por base64: %s", exc)
        elif foto_campeao_file and foto_campeao_file.filename:
            try:
                card_campeao_url = upload_service.processar_foto_campeao(file_storage=foto_campeao_file, sorteio_id=sorteio_id)
            except Exception as exc:
                logger.warning("Falha ao processar foto do campeao por arquivo: %s", exc)

        partida = partida_service.registrar_resultado(
            sorteio_id=sorteio_id,
            time_vencedor=time_vencedor,
            gols_times=gols_times,
            notas='',
            times_desempenho=times_desempenho,
            card_campeao_url=card_campeao_url,
        )
        juiz_partida_service.marcar_resultado_registrado(sorteio_id, partida.get('id'))

        partida_votacao = votacao_service.obter_por_sorteio(sorteio_id)
        if partida_votacao:
            partida_votacao['resultado_partida'] = partida
            if card_campeao_url:
                partida_votacao['card_campeao_url'] = card_campeao_url
            dados = votacao_service._carregar()
            alvo = votacao_service._find_partida_em_dados(dados, partida_votacao['id'])
            if alvo:
                alvo['resultado_partida'] = partida
                if card_campeao_url:
                    alvo['card_campeao_url'] = card_campeao_url
                votacao_service._salvar(dados)

        return redirect(url_for(
            'votacao.votacao_admin_page',
            sorteio_id=sorteio_id,
            sucesso='Resultado salvo com sucesso. Agora você pode abrir a votação dos jogadores.',
        ))
    except ValueError as e:
        contexto = _resolver_contexto_admin(sorteio_id_hint=sorteio_id)
        form_values = {}
        sorteio_contexto = contexto.get('sorteio_contexto') or {}
        for time in sorteio_contexto.get('times', []) or []:
            try:
                numero = int(time.get('numero'))
            except (TypeError, ValueError):
                continue

            for campo in ('vitorias', 'empates', 'derrotas', 'gols'):
                chave = f'{campo}_{numero}'
                valor = request.form.get(chave)
                form_values[chave] = (valor if valor is not None else '0')

        return render_template(
            'votacao_admin.html',
            **contexto,
            resultado_form_values=form_values,
            erro=str(e),
            usuario=_usuario_logado(),
        ), 400

@votacao_bp.route('/admin/votacao', methods=['GET'])
@admin_or_juiz_required
def votacao_admin_page():
    """Central de votação do admin/juiz com suporte a reabertura e edição de resultados."""
    sorteio_id = request.args.get('sorteio_id', type=int)
    editar_resultado = request.args.get('editar_resultado', type=int) or request.args.get('reabrir_resultado', type=int)
    sucesso = request.args.get('sucesso', '').strip()
    erro = request.args.get('erro', '').strip()

    if editar_resultado and sorteio_id and _is_juiz():
        juiz_partida_service.reabrir_partida(sorteio_id)

    if _is_juiz():
        contexto = _resolver_contexto_admin(sorteio_id_hint=sorteio_id)
        resultado_form_values = {}
        res_partida = contexto.get('resultado_partida')
        if res_partida and res_partida.get('times_desempenho'):
            for td in res_partida['times_desempenho']:
                num = td.get('time_numero')
                resultado_form_values[f'vitorias_{num}'] = str(td.get('vitorias', 0))
                resultado_form_values[f'empates_{num}'] = str(td.get('empates', 0))
                resultado_form_values[f'derrotas_{num}'] = str(td.get('derrotas', 0))
                resultado_form_values[f'gols_{num}'] = str(td.get('gols', 0))

        return render_template(
            'votacao_admin.html',
            **contexto,
            modo_edicao_resultado=False,
            resultado_form_values=resultado_form_values,
            sucesso=sucesso or None,
            erro=erro or None,
            usuario=_usuario_logado(),
        )
    return redirect(url_for('admin.admin_page', sorteio_id=sorteio_id, sucesso=sucesso))


@votacao_bp.route('/admin/votacao/salvar-foto-campeao', methods=['POST'])
@admin_or_juiz_required
def votacao_admin_salvar_foto_campeao():
    """Salva a foto/card do time campeão para a partida."""
    sorteio_id = request.form.get('sorteio_id', type=int)
    if not sorteio_id and _is_juiz():
        estado = juiz_partida_service.obter_estado()
        sorteio_id = ((estado.get('partida_atual') or {}).get('sorteio_id'))

    if not sorteio_id:
        return redirect(url_for('votacao.votacao_admin_page', erro='Sorteio não identificado'))

    partidas_existentes = partida_service.obter_partidas_sorteio(sorteio_id)
    foto_antiga_url = (partidas_existentes[0].get('card_campeao_url') if partidas_existentes else None)

    if request.form.get('remover_sem_foto'):
        # Limpa o status sem_foto para permitir adicionar foto
        if partidas_existentes:
            partida_obj = partidas_existentes[0]
            partida_service.registrar_resultado(
                sorteio_id=sorteio_id,
                time_vencedor=partida_obj.get('time_vencedor'),
                gols_times=partida_obj.get('gols_times', []),
                notas=partida_obj.get('notas', ''),
                times_desempenho=partida_obj.get('times_desempenho', []),
                card_campeao_url=''
            )
        return redirect(url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id))

    if request.form.get('sem_foto'):
        if foto_antiga_url:
            upload_service.remover_card_campeao(foto_antiga_url)
        card_campeao_url = 'sem_foto'
    else:
        card_campeao_url = None
        foto_campeao_file = request.files.get('foto_campeao') or request.files.get('foto_campeao_cam')
        card_campeao_base64 = request.form.get('card_campeao_base64')

        if card_campeao_base64 and isinstance(card_campeao_base64, str) and card_campeao_base64.startswith('data:image'):
            try:
                card_campeao_url = upload_service.processar_foto_campeao(base64_data=card_campeao_base64, sorteio_id=sorteio_id, foto_antiga_url=foto_antiga_url)
            except Exception as exc:
                logger.warning("Falha ao processar card do campeao por base64: %s", exc)
                return redirect(url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id, erro=str(exc)))
        elif foto_campeao_file and foto_campeao_file.filename:
            try:
                card_campeao_url = upload_service.processar_foto_campeao(file_storage=foto_campeao_file, sorteio_id=sorteio_id, foto_antiga_url=foto_antiga_url)
            except Exception as exc:
                logger.warning("Falha ao processar foto do campeao por arquivo: %s", exc)
                return redirect(url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id, erro=str(exc)))

    if card_campeao_url:
        # Salvar em partida_service
        partidas = partida_service.obter_partidas_sorteio(sorteio_id)
        if partidas:
            partida_obj = partidas[0]
            partida_service.registrar_resultado(
                sorteio_id=sorteio_id,
                time_vencedor=partida_obj.get('time_vencedor'),
                gols_times=partida_obj.get('gols_times', []),
                notas=partida_obj.get('notas', ''),
                times_desempenho=partida_obj.get('times_desempenho', []),
                card_campeao_url=card_campeao_url
            )
        # Salvar em votacao_service se houver partida de votacao
        partida_votacao = votacao_service.obter_por_sorteio(sorteio_id)
        if partida_votacao:
            partida_votacao['card_campeao_url'] = card_campeao_url
            dados = votacao_service._carregar()
            alvo = votacao_service._find_partida_em_dados(dados, partida_votacao['id'])
            if alvo:
                alvo['card_campeao_url'] = card_campeao_url
                if alvo.get('resultado_partida'):
                    alvo['resultado_partida']['card_campeao_url'] = card_campeao_url
                votacao_service._salvar(dados)

        msg = 'Opção "Sem foto" salva com sucesso!' if card_campeao_url == 'sem_foto' else 'Foto do time campeão salva com sucesso!'
        return redirect(url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id, sucesso=msg))

    return redirect(url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id))


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
        if partida_existente:
            if partida_existente.get('status') != 'aberta':
                partida = votacao_service.reabrir_rodada(partida_existente['id'], session.get('user_id', 'juiz'))
            else:
                partida = partida_existente
        else:
            partida = votacao_service.criar_partida(
                times_json=sorteio.get('times', []),
                usuarios=usuarios,
                criado_por=session.get('user_id'),
                titulo=titulo,
                sorteio_id=sorteio.get('id'),
                resultado_partida=resultado_partida,
                duracao_horas=20,
            )
        
        if _is_juiz():
            juiz_partida_service.marcar_votacao_aberta(sorteio.get('id'), partida.get('id'))

        # Processar foto/card do time campeão se enviado ao abrir a votação
        card_campeao_url = None
        foto_campeao_file = request.files.get('foto_campeao') or request.files.get('foto_campeao_cam')
        card_campeao_base64 = request.form.get('card_campeao_base64')
        if card_campeao_base64 and isinstance(card_campeao_base64, str) and card_campeao_base64.startswith('data:image'):
            try:
                card_campeao_url = upload_service.processar_foto_campeao(base64_data=card_campeao_base64, sorteio_id=sorteio.get('id'))
            except Exception as exc:
                logger.warning("Falha ao processar card do campeao por base64: %s", exc)
        elif foto_campeao_file and foto_campeao_file.filename:
            try:
                card_campeao_url = upload_service.processar_foto_campeao(file_storage=foto_campeao_file, sorteio_id=sorteio.get('id'))
            except Exception as exc:
                logger.warning("Falha ao processar foto do campeao enviada por arquivo: %s", exc)

        if card_campeao_url:
            partida['card_campeao_url'] = card_campeao_url
            dados = votacao_service._carregar()
            alvo = votacao_service._find_partida_em_dados(dados, partida['id'])
            if alvo:
                alvo['card_campeao_url'] = card_campeao_url
                votacao_service._salvar(dados)
            if resultado_partida:
                resultado_partida['card_campeao_url'] = card_campeao_url
                partida_service.registrar_resultado(
                    sorteio_id=sorteio.get('id'),
                    time_vencedor=resultado_partida.get('time_vencedor'),
                    gols_times=resultado_partida.get('gols_times', []),
                    notas=resultado_partida.get('notas', ''),
                    times_desempenho=resultado_partida.get('times_desempenho', []),
                    card_campeao_url=card_campeao_url
                )

        # Dispara e-mail de votação aberta APENAS para os participantes da partida
        try:
            from services.email_service import EmailService
            email_svc = EmailService()
            participantes = partida.get('participantes', [])
            email_svc.notify_votacao_aberta(participantes, partida_titulo=titulo)
        except Exception as exc:
            logger.warning(f"Erro ao disparar e-mails de votação aberta: {exc}")

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
        
        # Dispara e-mail de ranking disponível para todos os jogadores
        try:
            from services.email_service import EmailService
            from services.jogador_service import JogadorService
            email_svc = EmailService()
            todos_jogadores = JogadorService().listar()
            email_svc.notify_ranking_disponivel(todos_jogadores, partida_titulo=partida_encerrada.get('titulo', 'Ranking Atualizado'))
        except Exception as exc:
            logger.warning(f"Erro ao disparar e-mails de ranking disponível: {exc}")

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


@votacao_bp.route('/admin/votacao/<int:partida_id>/reabrir', methods=['POST'])
@admin_or_juiz_required
def votacao_admin_reabrir(partida_id):
    """Reabre uma rodada encerrada para correções de resultado ou novos votos"""
    try:
        partida_reaberta = votacao_service.reabrir_rodada(partida_id, session.get('user_id', 'juiz'))
        sorteio_id = partida_reaberta.get('sorteio_id')
        if sorteio_id:
            juiz_partida_service.reabrir_partida(sorteio_id)
        
        msg_sucesso = 'Rodada reaberta com sucesso! Agora você pode ajustar os resultados ou aguardar novos votos.'
        if _is_juiz():
            return redirect(url_for('votacao.votacao_admin_page', sorteio_id=sorteio_id, sucesso=msg_sucesso))

        return redirect(url_for('admin.admin_page', partida_id=partida_id, sucesso=msg_sucesso))
    except ValueError as e:
        contexto = _resolver_contexto_admin()
        return render_template(
            'votacao_admin.html',
            **contexto,
            erro=str(e),
            usuario=_usuario_logado()
        ), 400
    except Exception as e:
        logger.error(f"Erro ao reabrir votação: {str(e)}")
        contexto = _resolver_contexto_admin()
        return render_template(
            'votacao_admin.html',
            **contexto,
            erro='Erro ao reabrir votação',
            usuario=_usuario_logado()
        ), 500

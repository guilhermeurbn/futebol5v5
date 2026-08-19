"""
Rotas de Administração
- Dashboard admin, gerenciamento de usuários e notificações
"""
import os

from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify
from functools import wraps
import logging

from services.auth_service import AuthService
from services.email_service import EmailService
from services.notificacao_service import NotificacaoService
from services.jogador_service import JogadorService

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

auth_service = AuthService()
email_service = EmailService()
notificacao_service = NotificacaoService()
jogador_service = JogadorService()


# ============================================================
# DECORATORS
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


def _is_admin():
    return session.get('role') in ['admin']


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth.login_page'))
        from routes.auth_routes import _usuario_sem_email
        if _usuario_sem_email(user_id):
            return redirect(url_for('auth.completar_email_page'))
        if not _is_admin():
            return redirect(url_for('jogador_crud.index'))
        return f(*args, **kwargs)
    return wrapper


# ============================================================
# DASHBOARD
# ============================================================

@admin_bp.route('/admin', methods=['GET'])
def admin_redirect():
    """Redireciona a rota antiga /admin para a lista de jogadores"""
    return redirect(url_for('jogador_crud.index'))


def _garantir_e_obter_jogador_vinculado(user, jog_service):
    if user.get('role') != 'usuario':
        return None
    players = jog_service.listar_por_usuario(user['id'])
    if players:
        return players[0]
    try:
        return jog_service.criar(
            nome=user['nome'],
            nivel=5.5,
            tipo='avulso',
            posicao='linha',
            owner_user_id=user['id']
        )
    except Exception as e:
        logger.error(f"Erro ao auto-criar jogador para {user.get('username')}: {e}")
        return None


@admin_bp.route('/admin/ajustes', methods=['GET'])
@admin_required
def admin_page():
    """Dashboard administrativo"""
    try:
        usuarios = sorted(auth_service.listar_usuarios(), key=lambda u: (u.get('nome') or '').lower())
        for u in usuarios:
            u['jogador_vinculado'] = _garantir_e_obter_jogador_vinculado(u, jogador_service)
        notificacoes = notificacao_service.listar_notificacoes(apenas_nao_lidas=True, limite=15)
        sucesso = session.pop('admin_sucesso', request.args.get('sucesso', ''))
        erro = session.pop('admin_erro', request.args.get('erro', ''))
        senha_reset = session.pop('admin_senha_reset', None)
        
        jogadores_avulsos = [j.para_dict() if hasattr(j, 'para_dict') else j for j in jogador_service.listar() if j.tipo == 'avulso' or not j.owner_user_id]
        return render_template(
            'admin.html',
            usuarios=usuarios,
            jogadores_avulsos=jogadores_avulsos,
            notificacoes=notificacoes,
            total_notificacoes=notificacao_service.contar_nao_lidas(),
            total_usuarios=len(usuarios),
            sucesso=sucesso,
            erro=erro,
            senha_reset=senha_reset,
            usuario=_usuario_logado()
        )
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard admin: {str(e)}")
        return render_template('admin.html', erro='Erro ao carregar dashboard'), 500


@admin_bp.route('/api/admin/painel', methods=['GET'])
@admin_required
def api_admin_painel():
    """API: Resumo leve do painel admin."""
    try:
        usuarios = sorted(auth_service.listar_usuarios(), key=lambda u: (u.get('nome') or '').lower())
        for u in usuarios:
            player = _garantir_e_obter_jogador_vinculado(u, jogador_service)
            u['jogador_vinculado'] = player.para_dict() if player else None
        notificacoes = notificacao_service.listar_notificacoes(apenas_nao_lidas=True, limite=15)
        arquivadas = notificacao_service.listar_arquivadas(limite=10)

        return jsonify({
            'sucesso': True,
            'dados': {
                'total_usuarios': len(usuarios),
                'total_notificacoes': notificacao_service.contar_nao_lidas(),
                'usuarios': usuarios,
                'notificacoes': notificacoes,
                'arquivadas': arquivadas,
            }
        })
    except Exception as e:
        logger.error(f"Erro ao retornar painel admin: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro ao retornar painel admin'}), 500


# ============================================================
# NOTIFICAÇÕES
# ============================================================

@admin_bp.route('/admin/notificacoes/limpar', methods=['POST'])
@admin_required
def admin_limpar_notificacoes():
    """Marca todas as notificações como lidas"""
    try:
        notificacao_service.marcar_todas_como_lidas()
        return redirect(url_for('admin.admin_page', sucesso='Notificacoes marcadas como lidas'))
    except Exception as e:
        logger.error(f"Erro ao limpar notificações: {str(e)}")
        return redirect(url_for('admin.admin_page', erro='Erro ao limpar notificações'))


@admin_bp.route('/admin/notificacoes', methods=['GET'])
@admin_required
def admin_notificacoes_page():
    """Lista completa de notificações administrativas."""
    try:
        notificacoes = notificacao_service.listar_notificacoes(apenas_nao_lidas=True, limite=100)
        arquivadas = notificacao_service.listar_arquivadas(limite=50)
        return render_template(
            'admin_notificacoes.html',
            notificacoes=notificacoes,
            arquivadas=arquivadas,
            total_notificacoes=notificacao_service.contar_nao_lidas(),
            usuario=_usuario_logado(),
        )
    except Exception as e:
        logger.error(f"Erro ao carregar notificacoes admin: {str(e)}")
        return render_template('admin_notificacoes.html', notificacoes=[], arquivadas=[], erro='Erro ao carregar avisos', usuario=_usuario_logado()), 500


# ============================================================
# GERENCIAMENTO DE USUÁRIOS
# ============================================================

@admin_bp.route('/admin/usuarios', methods=['POST'])
@admin_required
def admin_criar_usuario():
    """Cria novo usuário (admin)"""
    try:
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '')
        nome = request.form.get('nome', '')
        password = request.form.get('password', '')
        role = request.form.get('role', 'usuario')
        
        if not email or '@' not in email:
            raise ValueError('Email deve ser valido')

        if not nome or len(nome) < 2:
            raise ValueError('Nome deve ter ao menos 2 caracteres')
        nome_partes = [p for p in nome.strip().split() if p]
        if len(nome_partes) < 2:
            raise ValueError('Por favor, insira o nome e sobrenome.')

        posicao = request.form.get('posicao', 'linha').strip().lower()
        if posicao not in ['linha', 'goleiro']:
            posicao = 'linha'

        usuario = auth_service.criar_usuario(email=email, username=username, nome=nome, password=password, role=role)
        if role == 'usuario':
            try:
                jogador_service.criar(
                    nome=nome,
                    nivel=5.5,
                    tipo='avulso',
                    posicao=posicao,
                    owner_user_id=usuario.get('id')
                )
            except Exception as e:
                logger.warning(f"Erro ao criar perfil de jogador para usuario {username}: {e}")
                try:
                    auth_service.deletar_usuario(usuario.get('id'))
                except Exception as rollback_exc:
                    logger.error(f"Falha ao desfazer usuario {username} apos erro ao criar jogador: {rollback_exc}")
                raise RuntimeError('Erro ao criar perfil de jogador') from e
        return redirect(url_for('admin.admin_page', sucesso='Usuario criado com sucesso'))
    except ValueError as e:
        logger.warning(f"Erro de validação ao criar usuário: {str(e)}")
        usuarios = auth_service.listar_usuarios()
        msg = str(e)
        if msg == "Username ja existe":
            msg = "Este nome de usuário já está em uso. Por favor, escolha outro."
        elif msg == "Email ja existe":
            msg = "Este e-mail já está em uso. Por favor, escolha outro."
        return render_template('admin.html', usuarios=usuarios, erro=msg, usuario=_usuario_logado()), 400
    except Exception as e:
        logger.error(f"Erro ao criar usuário: {str(e)}")
        usuarios = auth_service.listar_usuarios()
        return render_template('admin.html', usuarios=usuarios, erro='Erro ao criar usuário', usuario=_usuario_logado()), 500


@admin_bp.route('/admin/usuarios/<user_id>/resetar-senha', methods=['POST'])
@admin_required
def admin_resetar_senha_usuario(user_id):
    """Reseta senha de um usuário (admin)"""
    try:
        dados_reset = auth_service.resetar_senha_por_admin(
            user_id=user_id,
            executor_id=session.get('user_id')
        )
        session['admin_sucesso'] = f'Senha de {dados_reset.get("nome")} resetada com sucesso'
        if dados_reset.get('email'):
            try:
                resultado = email_service.send_temporary_password_email(
                    to_email=dados_reset.get('email'),
                    nome=dados_reset.get('nome') or dados_reset.get('username') or 'usuario',
                    username=dados_reset.get('username') or '',
                    senha_temporaria=dados_reset.get('senha_temporaria') or '',
                )
                if not resultado.ok:
                    logger.warning('Falha ao enviar email de senha temporaria para %s: %s', dados_reset.get('email'), resultado.error)
                    session.pop('admin_sucesso', None)
                    session['admin_erro'] = f'Usuario resetado, mas falha no email: {resultado.error}'
                else:
                    session['admin_sucesso'] = f'Senha de {dados_reset.get("nome")} resetada e email enviado com sucesso'
            except Exception as exc:
                logger.warning('Falha ao enviar email de senha temporaria para %s: %s', dados_reset.get('email'), exc)
                session.pop('admin_sucesso', None)
                session['admin_erro'] = f'Usuario resetado, mas falha no email: {exc}'
        session['admin_senha_reset'] = dados_reset
        return redirect(url_for('admin.admin_page'))
    except ValueError as e:
        logger.warning(f"Erro ao resetar senha: {str(e)}")
        session['admin_erro'] = str(e)
        return redirect(url_for('admin.admin_page'))
    except Exception as e:
        logger.error(f"Erro ao resetar senha: {str(e)}")
        session['admin_erro'] = 'Erro ao resetar senha'
        return redirect(url_for('admin.admin_page'))


@admin_bp.route('/admin/usuarios/<user_id>/ativo', methods=['POST'])
@admin_required
def admin_alterar_ativo_usuario(user_id):
    """Ativa ou desativa um usuário"""
    try:
        acao = request.form.get('acao', '').strip().lower()
        ativo = acao == 'ativar'

        auth_service.definir_ativo(
            user_id=user_id,
            ativo=ativo,
            executor_id=session.get('user_id')
        )
        mensagem = 'Usuario ativado com sucesso' if ativo else 'Usuario desativado com sucesso'
        return redirect(url_for('admin.admin_page', sucesso=mensagem))
    except ValueError as e:
        logger.warning(f"Erro ao alterar ativo: {str(e)}")
        return redirect(url_for('admin.admin_page', erro=str(e)))
    except Exception as e:
        logger.error(f"Erro ao alterar ativo do usuário: {str(e)}")
        return redirect(url_for('admin.admin_page', erro='Erro ao alterar status'))


@admin_bp.route('/admin/usuarios/<user_id>/email', methods=['POST'])
@admin_required
def admin_atualizar_email_usuario(user_id):
    """Atualiza o email de um usuário."""
    try:
        email = request.form.get('email', '').strip().lower()
        auth_service.atualizar_email(
            user_id=user_id,
            email=email,
            executor_id=session.get('user_id')
        )
        return redirect(url_for('admin.admin_page', sucesso='Email atualizado com sucesso'))
    except ValueError as e:
        logger.warning(f"Erro ao atualizar email: {str(e)}")
        return redirect(url_for('admin.admin_page', erro=str(e)))
    except Exception as e:
        logger.error(f"Erro ao atualizar email do usuário: {str(e)}")
        return redirect(url_for('admin.admin_page', erro='Erro ao atualizar email'))


@admin_bp.route('/admin/usuarios/<user_id>/deletar', methods=['POST'])
@admin_required
def admin_deletar_usuario(user_id):
    """Deleta um usuário do sistema"""
    try:
        auth_service.deletar_usuario(
            user_id=user_id,
            executor_id=session.get('user_id')
        )
        return redirect(url_for('admin.admin_page', sucesso='Usuario deletado com sucesso. Ele perderá suas credenciais.'))
    except ValueError as e:
        logger.warning(f"Erro ao deletar usuário: {str(e)}")
        return redirect(url_for('admin.admin_page', erro=str(e)))
    except Exception as e:
        logger.error(f"Erro ao deletar usuário: {str(e)}")
        return redirect(url_for('admin.admin_page', erro='Erro ao deletar usuário'))


@admin_bp.route('/admin/jogadores/sincronizar', methods=['POST'])
@admin_required
def admin_sincronizar_jogador():
    """Sincroniza um jogador avulso com uma conta de usuário cadastrado."""
    try:
        jogador_avulso_id = request.form.get('jogador_avulso_id', '').strip()
        usuario_destino_id = request.form.get('usuario_destino_id', '').strip()

        if not jogador_avulso_id or not usuario_destino_id:
            raise ValueError('Selecione o jogador avulso e o usuário de destino.')

        resultado = jogador_service.sincronizar_jogador_avulso(
            jogador_avulso_id=jogador_avulso_id,
            usuario_destino_id=usuario_destino_id
        )

        session['admin_sucesso'] = f"Jogador '{resultado['nome_avulso']}' sincronizado com sucesso para '{resultado['usuario_destino']}'!"
        return redirect(url_for('admin.admin_page'))
    except ValueError as e:
        logger.warning(f"Erro de validação ao sincronizar jogador: {str(e)}")
        session['admin_erro'] = str(e)
        return redirect(url_for('admin.admin_page'))
    except Exception as e:
        logger.error(f"Erro ao sincronizar jogador: {str(e)}")
        session['admin_erro'] = f"Erro ao sincronizar jogador: {str(e)}"
        return redirect(url_for('admin.admin_page'))


@admin_bp.route('/admin/partida/editar-nota-jogador', methods=['POST'])
@admin_required
def admin_editar_nota_jogador():
    """Permite ao administrador alterar manualmente a nota de um jogador em uma partida especifica."""
    try:
        dados = request.get_json(silent=True) or request.form.to_dict()
        partida_id = str(dados.get('partida_id', '')).strip()
        sorteio_id = str(dados.get('sorteio_id', '')).strip()
        jogador_nome = str(dados.get('jogador_nome', '')).strip()
        jogador_id = str(dados.get('jogador_id', '')).strip()
        
        try:
            nova_nota = float(dados.get('nova_nota'))
        except (TypeError, ValueError):
            return jsonify({'sucesso': False, 'erro': 'Nota inválida'}), 400

        if not (0.0 <= nova_nota <= 10.0):
            return jsonify({'sucesso': False, 'erro': 'A nota deve estar entre 0.0 e 10.0'}), 400

        if not partida_id and not sorteio_id:
            return jsonify({'sucesso': False, 'erro': 'Identificador de partida ausente'}), 400

        from services.db import load_json_data, save_json_data, clear_db_cache
        from services.jogador_stats_service import JogadorStatsService
        from services.jogador_service import sincronizar_dados_e_partidas

        stats_svc = JogadorStatsService()
        nome_norm = stats_svc._normalizar_nome(jogador_nome)

        # 1. Atualizar em votacoes_partidas
        vot_dados = load_json_data("votacoes_partidas", {})
        vot_list = vot_dados.get("partidas", []) if isinstance(vot_dados, dict) else []
        alterado_vot = False

        for vp in vot_list:
            if not isinstance(vp, dict):
                continue
            v_pid = str(vp.get("id") or "")
            v_sid = str(vp.get("sorteio_id") or "")
            if (partida_id and (v_pid == partida_id or v_sid == partida_id)) or (sorteio_id and (v_sid == sorteio_id or v_pid == sorteio_id)):
                ranking = vp.get("ranking")
                if not isinstance(ranking, dict):
                    ranking = {"ranking_jogadores": [], "ranking_times": []}
                    vp["ranking"] = ranking
                
                ranking_jogadores = ranking.get("ranking_jogadores", [])
                encontrado = False
                for rj in ranking_jogadores:
                    rj_nome = stats_svc._normalizar_nome(rj.get("jogador_nome", ""))
                    rj_uid = str(rj.get("user_id") or "")
                    if (jogador_id and rj_uid == jogador_id) or (nome_norm and rj_nome == nome_norm):
                        rj["nota_media"] = round(nova_nota, 2)
                        votos_cnt = int(rj.get("votos", 1) or 1)
                        rj["nota_total"] = round(nova_nota * votos_cnt, 2)
                        rj["pontos"] = round(nova_nota * votos_cnt, 2)
                        encontrado = True
                        alterado_vot = True
                        break
                
                if not encontrado and (jogador_nome or nome_norm):
                    ranking_jogadores.append({
                        "jogador_nome": jogador_nome,
                        "user_id": jogador_id or None,
                        "nota_media": round(nova_nota, 2),
                        "nota_total": round(nova_nota, 2),
                        "soma_pesos": 1.0,
                        "votos": 1,
                        "pontos": round(nova_nota, 2),
                        "gols": 0,
                        "confiabilidade_media": 1.0
                    })
                    ranking["ranking_jogadores"] = ranking_jogadores
                    alterado_vot = True

        if alterado_vot:
            save_json_data("votacoes_partidas", vot_dados)

        # 2. Atualizar em partidas
        partidas_list = load_json_data("partidas", [])
        alterado_partidas = False
        for p in partidas_list:
            if not isinstance(p, dict):
                continue
            p_pid = str(p.get("id") or "")
            p_sid = str(p.get("sorteio_id") or "")
            if (partida_id and (p_pid == partida_id or p_sid == partida_id)) or (sorteio_id and (p_sid == sorteio_id or p_pid == sorteio_id)):
                jogadores_detalhes = p.get("jogadores_detalhes", [])
                for det in jogadores_detalhes:
                    d_nome = stats_svc._normalizar_nome(det.get("nome", ""))
                    d_uid = str(det.get("user_id") or det.get("owner_user_id") or "")
                    if (jogador_id and d_uid == jogador_id) or (nome_norm and d_nome == nome_norm):
                        det["nota_media"] = round(nova_nota, 2)
                        det["nota_partida"] = round(nova_nota, 2)
                        det["nota"] = round(nova_nota, 2)
                        alterado_partidas = True

        if alterado_partidas:
            save_json_data("partidas", partidas_list)

        # 3. Limpar caches e ressincronizar estatísticas
        stats_svc.invalidar_cache_stats()
        clear_db_cache()
        sincronizar_dados_e_partidas()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Nota alterada com sucesso para {nova_nota:.2f}!',
            'nova_nota': round(nova_nota, 2)
        })

    except Exception as e:
        logger.error(f"Erro ao editar nota de jogador: {str(e)}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500





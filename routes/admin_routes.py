"""
Rotas de Administração
- Dashboard admin, gerenciamento de usuários e notificações
"""
import os

from flask import Blueprint, request, render_template, redirect, url_for, session
from functools import wraps
import logging

from services.auth_service import AuthService
from services.email_service import EmailService
from services.notificacao_service import NotificacaoService

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

auth_service = AuthService()
email_service = EmailService()
notificacao_service = NotificacaoService()


def _resolver_credenciais_resend(form):
    api_key = (form.get('resend_api_key') or '').strip()
    from_email = (form.get('resend_from_email') or '').strip()

    if not api_key:
        api_key = email_service._resolve_credentials()[0]
    if not from_email:
        from_email = email_service._resolve_credentials()[1]

    return api_key, from_email


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
    return session.get('role') in ['super_admin', 'admin']


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login_page'))
        if not _is_admin():
            return redirect(url_for('jogador_crud.index'))
        return f(*args, **kwargs)
    return wrapper


# ============================================================
# DASHBOARD
# ============================================================

@admin_bp.route('/admin', methods=['GET'])
@admin_required
def admin_page():
    """Dashboard administrativo"""
    try:
        usuarios = auth_service.listar_usuarios()
        notificacoes = notificacao_service.listar_notificacoes(apenas_nao_lidas=True, limite=15)
        sucesso = session.pop('admin_sucesso', request.args.get('sucesso', ''))
        erro = session.pop('admin_erro', request.args.get('erro', ''))
        senha_reset = session.pop('admin_senha_reset', None)
        
        return render_template(
            'admin.html',
            usuarios=usuarios,
            notificacoes=notificacoes,
            total_notificacoes=notificacao_service.contar_nao_lidas(),
            sucesso=sucesso,
            erro=erro,
            senha_reset=senha_reset,
            usuario=_usuario_logado()
        )
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard admin: {str(e)}")
        return render_template('admin.html', erro='Erro ao carregar dashboard'), 500


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

        auth_service.criar_usuario(email=email, username=username, nome=nome, password=password, role=role)
        return redirect(url_for('admin.admin_page', sucesso='Usuario criado com sucesso'))
    except ValueError as e:
        logger.warning(f"Erro de validação ao criar usuário: {str(e)}")
        usuarios = auth_service.listar_usuarios()
        return render_template('admin.html', usuarios=usuarios, erro=str(e), usuario=_usuario_logado()), 400
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
            api_key, from_email = _resolver_credenciais_resend(request.form)
            try:
                if not api_key or not from_email:
                    raise RuntimeError('Informe RESEND_API_KEY e RESEND_FROM_EMAIL para o teste')

                local_email_service = EmailService(api_key=api_key, from_email=from_email, base_url=email_service.base_url)
                resultado = local_email_service.send_temporary_password_email(
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



"""
Servico de autenticacao e usuarios.
"""
import json
import os
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from werkzeug.security import generate_password_hash, check_password_hash
from services.db import load_json_data, save_json_data


class AuthService:
    """Gerencia usuarios, senha e perfil."""

    _TEMP_PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    _DEFAULT_BOOTSTRAP_CREDENTIALS_FILE = Path(__file__).resolve().parent.parent / '.secrets' / 'initial_admin_credentials.json'

    def __init__(self, arquivo: str = "data/users.json"):
        self.arquivo = arquivo
        self._garantir_arquivo()

    def _garantir_arquivo(self) -> None:
        # If using a proper DATABASE_URL (production), do not auto-create
        # local default accounts to avoid shipping predictable credentials.
        if os.getenv("DATABASE_URL"):
            return
        if not os.path.exists(self.arquivo):
            self._salvar([])

        self._garantir_contas_padrao()

    def _garantir_contas_padrao(self) -> None:
        usuarios = self._carregar()
        alterou = False
        created_credentials = []

        env = os.getenv('FLASK_ENV', 'development')

        def _add_admin_if_missing(username: str, display_name: str):
            nonlocal alterou
            if any((u.get('username') or '').lower() == username.lower() for u in usuarios):
                return
            # Only auto-create default admins in non-production environments
            if env == 'production':
                return

            senha = self._gerar_senha_temporaria(12)
            usuarios.append({
                'id': str(uuid.uuid4()),
                'username': username.lower(),
                'nome': display_name,
                'password_hash': generate_password_hash(senha),
                'role': 'admin',
                'criado_em': datetime.now().isoformat(),
                'ativo': True,
                'senha_temporaria_ativa': True,
            })
            created_credentials.append({'username': username.lower(), 'password': senha})
            alterou = True

        # Ensure there's at least one admin user (only create in dev/test)
        if not any((u.get('role') == 'admin') for u in usuarios):
            _add_admin_if_missing('admin', 'Administrador')

        if alterou:
            self._salvar(usuarios)
            # Persist generated credentials only in local secrets storage
            try:
                creds_file = Path(os.getenv('ADMIN_BOOTSTRAP_CREDENTIALS_FILE', str(self._DEFAULT_BOOTSTRAP_CREDENTIALS_FILE))).expanduser()
                creds_file.parent.mkdir(parents=True, exist_ok=True)
                with creds_file.open('w', encoding='utf-8') as cf:
                    json.dump(created_credentials, cf, indent=2, ensure_ascii=False)
            except Exception:
                pass

    def _carregar(self) -> List[Dict]:
        if os.getenv("DATABASE_URL"):
            return load_json_data("users", [])
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _salvar(self, dados: List[Dict]) -> None:
        if os.getenv("DATABASE_URL"):
            save_json_data("users", dados)
            return
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    def listar_usuarios(self) -> List[Dict]:
        usuarios = self._carregar()
        saida = []
        for u in usuarios:
            saida.append({
                "id": u.get("id"),
                "email": u.get("email"),
                "username": u.get("username"),
                "nome": u.get("nome"),
                "role": u.get("role", "usuario"),
                "ativo": u.get("ativo", True),
                "senha_temporaria_ativa": u.get("senha_temporaria_ativa", False),
                "criado_em": u.get("criado_em"),
            })
        return saida

    def obter_por_username(self, username: str) -> Optional[Dict]:
        username = (username or "").strip().lower()
        if not username:
            return None

        for u in self._carregar():
            if (u.get("username") or "").lower() == username:
                return u
        return None

    def obter_por_id(self, user_id: str) -> Optional[Dict]:
        if not user_id:
            return None
        for u in self._carregar():
            if u.get("id") == user_id:
                return u
        return None

    def autenticar(self, username: str, password: str) -> Optional[Dict]:
        usuario = self.obter_por_username(username)
        if not usuario:
            return None
        if not usuario.get("ativo", True):
            return None

        if check_password_hash(usuario.get("password_hash", ""), password or ""):
            return {
                "id": usuario.get("id"),
                "email": usuario.get("email"),
                "username": usuario.get("username"),
                "nome": usuario.get("nome"),
                "role": usuario.get("role", "usuario"),
                "senha_temporaria_ativa": usuario.get("senha_temporaria_ativa", False),
            }
        return None

    def obter_por_email(self, email: str) -> Optional[Dict]:
        email = (email or "").strip().lower()
        if not email:
            return None

        for u in self._carregar():
            if (u.get("email") or "").strip().lower() == email:
                return u
        return None

    def criar_usuario(self, email: str = "", username: str = "", nome: str = "", password: str = "", role: str = "usuario") -> Dict:
        email = (email or "").strip().lower()
        username = (username or "").strip().lower()
        nome = (nome or "").strip()
        role = (role or "usuario").strip().lower()

        if email and "@" not in email:
            raise ValueError("Email deve ser valido")
        if not username or len(username) < 3:
            raise ValueError("Username deve ter ao menos 3 caracteres")
        if not nome or len(nome) < 2:
            raise ValueError("Nome deve ter ao menos 2 caracteres")
        if not password or len(password) < 6:
            raise ValueError("Senha deve ter ao menos 6 caracteres")
        if role not in ["admin", "juiz", "usuario"]:
            raise ValueError("Role invalida")

        usuarios = self._carregar()
        if email and any((u.get("email") or "").strip().lower() == email for u in usuarios):
            raise ValueError("Email ja existe")
        if any((u.get("username") or "").lower() == username for u in usuarios):
            raise ValueError("Username ja existe")

        novo = {
            "id": str(uuid.uuid4()),
            "email": email,
            "username": username,
            "nome": nome,
            "password_hash": generate_password_hash(password),
            "role": role,
            "criado_em": datetime.now().isoformat(),
            "ativo": True,
            "senha_temporaria_ativa": False,
        }
        usuarios.append(novo)
        self._salvar(usuarios)

        return {
            "id": novo["id"],
            "email": novo["email"],
            "username": novo["username"],
            "nome": novo["nome"],
            "role": novo["role"],
            "ativo": novo["ativo"],
            "criado_em": novo["criado_em"],
        }

    def definir_nova_senha(self, user_id: str, nova_senha: str) -> None:
        if not nova_senha or len(nova_senha) < 6:
            raise ValueError("Nova senha deve ter ao menos 6 caracteres")

        usuarios = self._carregar()
        for u in usuarios:
            if u.get("id") != user_id:
                continue

            u["password_hash"] = generate_password_hash(nova_senha)
            u["senha_temporaria_ativa"] = False
            u["senha_resetada_em"] = None
            u["senha_resetada_por"] = None
            u.pop("password_reset_token_hash", None)
            u.pop("password_reset_token_expira_em", None)
            u.pop("password_reset_requested_em", None)
            self._salvar(usuarios)
            return

        raise ValueError("Usuario nao encontrado")

    def gerar_token_reset(self, user_id: str, expires_in_seconds: int = 3600) -> str:
        if not user_id:
            raise ValueError("Usuario nao encontrado")

        token = secrets.token_urlsafe(32)
        usuarios = self._carregar()
        for u in usuarios:
            if u.get("id") == user_id:
                u["password_reset_token_hash"] = generate_password_hash(token)
                u["password_reset_token_expira_em"] = (datetime.now().timestamp() + max(300, int(expires_in_seconds)))
                u["password_reset_requested_em"] = datetime.now().isoformat()
                self._salvar(usuarios)
                return token

        raise ValueError("Usuario nao encontrado")

    def validar_token_reset(self, token: str) -> Optional[Dict]:
        token = (token or "").strip()
        if not token:
            return None

        now_ts = datetime.now().timestamp()
        for u in self._carregar():
            token_hash = u.get("password_reset_token_hash")
            expira_em = u.get("password_reset_token_expira_em")
            if not token_hash or not expira_em:
                continue
            try:
                if float(expira_em) < now_ts:
                    continue
            except (TypeError, ValueError):
                continue
            if check_password_hash(token_hash, token):
                return u
        return None

    def consumir_token_reset(self, user_id: str) -> None:
        usuarios = self._carregar()
        for u in usuarios:
            if u.get("id") == user_id:
                u.pop("password_reset_token_hash", None)
                u.pop("password_reset_token_expira_em", None)
                u.pop("password_reset_requested_em", None)
                self._salvar(usuarios)
                return
        raise ValueError("Usuario nao encontrado")

    def alterar_senha(self, user_id: str, senha_atual: str, nova_senha: str, senha_temporaria: bool = False) -> None:
        if not senha_atual:
            if not senha_temporaria:
                raise ValueError("Informe a senha atual")
        if not nova_senha or len(nova_senha) < 6:
            raise ValueError("Nova senha deve ter ao menos 6 caracteres")

        usuarios = self._carregar()
        for u in usuarios:
            if u.get("id") != user_id:
                continue

            if not senha_temporaria and not check_password_hash(u.get("password_hash", ""), senha_atual):
                raise ValueError("Senha atual incorreta")

            u["password_hash"] = generate_password_hash(nova_senha)
            u["senha_temporaria_ativa"] = False
            u["senha_resetada_em"] = None
            u["senha_resetada_por"] = None
            self._salvar(usuarios)
            return

        raise ValueError("Usuario nao encontrado")

    def _gerar_senha_temporaria(self, tamanho: int = 10) -> str:
        """Gera senha temporaria legivel para reset administrativo."""
        tamanho = max(8, int(tamanho))
        return "".join(secrets.choice(self._TEMP_PASSWORD_ALPHABET) for _ in range(tamanho))

    def gerar_senha_temporaria(self, tamanho: int = 10) -> str:
        """Expõe a geração de senha temporária sem alterar dados persistidos."""
        return self._gerar_senha_temporaria(tamanho)

    def resetar_senha_por_admin(self, user_id: str, executor_id: Optional[str] = None) -> Dict:
        """
        Reseta a senha de um usuario via painel administrativo.

        Returns:
            Dict com dados do usuario e a senha temporaria gerada.
        """
        usuarios = self._carregar()

        alvo = None
        for u in usuarios:
            if u.get("id") == user_id:
                alvo = u
                break

        if not alvo:
            raise ValueError("Usuario nao encontrado")

        senha_temporaria = self._gerar_senha_temporaria()
        alvo["password_hash"] = generate_password_hash(senha_temporaria)
        alvo["senha_temporaria_ativa"] = True
        alvo["senha_resetada_em"] = datetime.now().isoformat()
        alvo["senha_resetada_por"] = executor_id
        self._salvar(usuarios)

        return {
            "id": alvo.get("id"),
            "email": alvo.get("email"),
            "username": alvo.get("username"),
            "nome": alvo.get("nome"),
            "role": alvo.get("role", "usuario"),
            "senha_temporaria": senha_temporaria,
        }

    def definir_ativo(self, user_id: str, ativo: bool, executor_id: Optional[str] = None) -> Dict:
        usuarios = self._carregar()
        alvo = None
        for u in usuarios:
            if u.get("id") == user_id:
                alvo = u
                break

        if not alvo:
            raise ValueError("Usuario nao encontrado")

        if executor_id and user_id == executor_id and not ativo:
            raise ValueError("Voce nao pode desativar seu proprio usuario")

        if alvo.get("role") in ["super_admin", "admin"] and not ativo:
            privilegiados_ativos = [
                u for u in usuarios
                if u.get("role") in ["super_admin", "admin"] and u.get("ativo", True)
            ]
            if alvo.get("ativo", True) and len(privilegiados_ativos) <= 1:
                raise ValueError("Nao e possivel desativar o ultimo usuario com acesso total")

        alvo["ativo"] = bool(ativo)
        self._salvar(usuarios)

        return {
            "id": alvo.get("id"),
            "username": alvo.get("username"),
            "nome": alvo.get("nome"),
            "role": alvo.get("role", "usuario"),
            "ativo": alvo.get("ativo", True),
            "criado_em": alvo.get("criado_em"),
        }

    def atualizar_email(self, user_id: str, email: str, executor_id: Optional[str] = None) -> Dict:
        email = (email or "").strip().lower()
        if not email or "@" not in email:
            raise ValueError("Email deve ser valido")

        usuarios = self._carregar()
        alvo = None
        for u in usuarios:
            if u.get("id") == user_id:
                alvo = u
                break

        if not alvo:
            raise ValueError("Usuario nao encontrado")

        email_existente = next(
            (
                u for u in usuarios
                if (u.get("email") or "").strip().lower() == email and u.get("id") != user_id
            ),
            None,
        )
        if email_existente:
            raise ValueError("Email ja existe")

        alvo["email"] = email
        self._salvar(usuarios)

        return {
            "id": alvo.get("id"),
            "email": alvo.get("email"),
            "username": alvo.get("username"),
            "nome": alvo.get("nome"),
            "role": alvo.get("role", "usuario"),
            "ativo": alvo.get("ativo", True),
            "criado_em": alvo.get("criado_em"),
        }
    
    def deletar_usuario(self, user_id: str, executor_id: Optional[str] = None) -> bool:
        """
        Deleta um usuário do sistema. Depois dele ser deletado, ele perderá 
        suas credenciais e terá que criar uma nova conta.
        
        Args:
            user_id: ID do usuário a deletar
            executor_id: ID do usuário que está executando a ação (verificação de segurança)
            
        Raises:
            ValueError: Se não puder deletar (ex: último admin, tentando deletar a si mesmo)
            
        Returns:
            bool: True se deletado com sucesso
        """
        usuarios = self._carregar()
        
        # Verificar se o usuário existe
        alvo = None
        indice_alvo = -1
        for idx, u in enumerate(usuarios):
            if u.get("id") == user_id:
                alvo = u
                indice_alvo = idx
                break
        
        if not alvo:
            raise ValueError("Usuario nao encontrado")
        
        # Não permitir deletar a si mesmo (e administradores não podem deletar sua própria conta)
        if executor_id:
            if user_id == executor_id:
                raise ValueError("Voce nao pode deletar sua propria conta")
        else:
            if alvo.get("role") in ["super_admin", "admin"]:
                raise ValueError("Administradores nao podem deletar sua propria conta")
        
        # Verificar se é o último admin/super_admin
        if alvo.get("role") in ["super_admin", "admin"]:
            privilegiados_ativos = [
                u for u in usuarios
                if u.get("role") in ["super_admin", "admin"] and u.get("id") != user_id
            ]
            if len(privilegiados_ativos) == 0:
                raise ValueError("Nao e possivel deletar o ultimo usuario com acesso total")
        
        # Deletar o usuário
        usuarios.pop(indice_alvo)
        self._salvar(usuarios)
        
        # Deletar jogador(es) associado(s)
        try:
            from services.jogador_service import JogadorService
            jogador_service = JogadorService()
            linked_players = jogador_service.listar_por_usuario(user_id)
            for p in linked_players:
                jogador_service.deletar(p.id)
        except Exception as e:
            pass
            
        return True

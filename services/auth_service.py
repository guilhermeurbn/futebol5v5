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

        # Se a lista de usuários estiver vazia ou sem sementes, carregar do seeds/users.json
        seed_path = Path(__file__).resolve().parent.parent / "data" / "seeds" / "users.json"
        if seed_path.exists():
            try:
                with seed_path.open("r", encoding="utf-8") as sf:
                    seeds = json.load(sf)
                ids_existentes = {u.get("id") for u in usuarios}
                unames_existentes = {(u.get("username") or "").lower() for u in usuarios if isinstance(u, dict)}
                for s in seeds:
                    if isinstance(s, dict) and s.get("id") not in ids_existentes and (s.get("username") or "").lower() not in unames_existentes:
                        usuarios.append(s)
                        alterou = True
            except Exception:
                pass

        # Garantir conta admin
        if not any((u.get('username') or '').lower() == 'admin' for u in usuarios):
            usuarios.append({
                'id': str(uuid.uuid4()),
                'username': 'admin',
                'nome': 'Administrador',
                'password_hash': generate_password_hash('123456'),
                'role': 'admin',
                'criado_em': datetime.now().isoformat(),
                'ativo': True,
                'senha_temporaria_ativa': False,
            })
            alterou = True

        # Garantir conta juiz
        if not any((u.get('username') or '').lower() == 'juiz' for u in usuarios):
            usuarios.append({
                'id': str(uuid.uuid4()),
                'username': 'juiz',
                'nome': 'Juiz Oficial',
                'password_hash': generate_password_hash('123456'),
                'role': 'juiz',
                'criado_em': datetime.now().isoformat(),
                'ativo': True,
                'senha_temporaria_ativa': False,
            })
            alterou = True

        # Garantir conta guilherme
        if not any((u.get('username') or '').lower() == 'guilherme' for u in usuarios):
            usuarios.append({
                'id': str(uuid.uuid4()),
                'username': 'guilherme',
                'nome': 'Guilherme Urbano',
                'password_hash': generate_password_hash('123456'),
                'role': 'usuario',
                'criado_em': datetime.now().isoformat(),
                'ativo': True,
                'senha_temporaria_ativa': False,
            })
            alterou = True

        if alterou:
            self._salvar(usuarios)

    def _carregar(self) -> List[Dict]:
        if hasattr(self, 'arquivo') and self.arquivo and self.arquivo != "data/users.json":
            if os.path.exists(self.arquivo):
                try:
                    with open(self.arquivo, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            return data
                except Exception:
                    pass
            return []
        return load_json_data("users", [])

    def _salvar(self, dados: List[Dict]) -> None:
        if hasattr(self, 'arquivo') and self.arquivo and self.arquivo != "data/users.json":
            try:
                with open(self.arquivo, "w", encoding="utf-8") as f:
                    json.dump(dados, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return
        from services.db import save_json_data
        save_json_data("users", dados)

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

    def autenticar(self, identificador: str, password: str) -> Optional[Dict]:
        clean_id = (identificador or "").strip().lower()
        if not clean_id:
            return None

        # Tentar por username, email ou id
        usuario = self.obter_por_username(clean_id) or self.obter_por_email(clean_id) or self.obter_por_id(clean_id)
        if not usuario:
            # Tentar buscar por nome (case-insensitive)
            for u in self._carregar():
                if (u.get("nome") or "").strip().lower() == clean_id:
                    usuario = u
                    break

        if not usuario:
            return None
        if not usuario.get("ativo", True):
            return None

        p_raw = password or ""
        p_strip = p_raw.strip()
        hash_val = usuario.get("password_hash", "")

        if check_password_hash(hash_val, p_raw) or (p_strip and check_password_hash(hash_val, p_strip)):
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
        if nome and any((u.get("nome") or "").strip().lower() == nome.lower() for u in usuarios):
            raise ValueError("Ja existe um usuario cadastrado com este nome")

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
        nova_clean = (nova_senha or "").strip()
        if not nova_clean or len(nova_clean) < 6:
            raise ValueError("Nova senha deve ter ao menos 6 caracteres")

        usuarios = self._carregar()
        for u in usuarios:
            if u.get("id") != user_id:
                continue

            h_val = u.get("password_hash", "")
            s_raw = senha_atual or ""
            s_strip = s_raw.strip()

            if not senha_temporaria and not check_password_hash(h_val, s_raw) and not check_password_hash(h_val, s_strip):
                raise ValueError("Senha atual incorreta")

            u["password_hash"] = generate_password_hash(nova_clean)
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

        if alvo.get("role") in ['admin'] and not ativo:
            privilegiados_ativos = [
                u for u in usuarios
                if u.get("role") in ['admin'] and u.get("ativo", True)
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

    def atualizar_perfil_usuario(
        self,
        user_id: str,
        email: Optional[str] = None,
        username: Optional[str] = None,
        nome: Optional[str] = None,
        foto_url: Optional[str] = None
    ) -> Dict:
        """
        Atualiza dados cadastrais (email, username, nome) do próprio usuário.
        """
        usuarios = self._carregar()
        alvo = None
        for u in usuarios:
            if u.get("id") == user_id:
                alvo = u
                break

        if not alvo:
            raise ValueError("Usuário não encontrado")

        if email is not None:
            email_clean = email.strip().lower()
            if not email_clean or "@" not in email_clean:
                raise ValueError("E-mail deve ser válido")
            if any((u.get("email") or "").strip().lower() == email_clean and u.get("id") != user_id for u in usuarios):
                raise ValueError("Este e-mail já está em uso por outra conta.")
            alvo["email"] = email_clean

        if username is not None:
            uname_clean = username.strip().lower()
            if not uname_clean or len(uname_clean) < 3:
                raise ValueError("Nome de usuário deve ter ao menos 3 caracteres")
            if any((u.get("username") or "").strip().lower() == uname_clean and u.get("id") != user_id for u in usuarios):
                raise ValueError("Este nome de usuário já está em uso por outra conta.")
            alvo["username"] = uname_clean

        if nome is not None:
            nome_clean = nome.strip()
            if len(nome_clean) < 2:
                raise ValueError("Nome deve ter ao menos 2 caracteres")
            nome_partes = [p for p in nome_clean.split() if p]
            if len(nome_partes) < 2:
                raise ValueError("Por favor, insira o nome e sobrenome.")
            alvo["nome"] = nome_clean
            
            # Sincronizar nome do atleta vinculado e dados de partidas se existir
            try:
                from services.jogador_service import JogadorService, sincronizar_dados_e_partidas
                jog_svc = JogadorService()
                linked_players = jog_svc.listar_por_usuario(user_id)
                for p in linked_players:
                    jog_svc.atualizar(p.id, nome=nome_clean)
                sincronizar_dados_e_partidas()
            except Exception:
                pass

        if foto_url is not None:
            alvo["foto_url"] = foto_url
            # Sincronizar foto do atleta vinculado se existir
            try:
                from services.jogador_service import JogadorService
                jog_svc = JogadorService()
                linked_players = jog_svc.listar_por_usuario(user_id)
                for p in linked_players:
                    jog_svc.atualizar(p.id, foto_url=foto_url)
            except Exception:
                pass

        self._salvar(usuarios)

        try:
            from services.jogador_service import sincronizar_dados_e_partidas
            from services.jogador_stats_service import JogadorStatsService
            sincronizar_dados_e_partidas()
            JogadorStatsService.invalidar_cache_stats()
        except Exception:
            pass

        return alvo

    
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
            if alvo.get("role") in ['admin']:
                raise ValueError("Administradores nao podem deletar sua propria conta")
        
        # Verificar se é o último admin/admin
        if alvo.get("role") in ['admin']:
            privilegiados_ativos = [
                u for u in usuarios
                if u.get("role") in ['admin'] and u.get("id") != user_id
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
        except Exception:
            pass
            
        return True

    def vincular_conta_social(self, user_id: str, provider: str, email: str, social_id: str = "") -> Dict:
        """
        Vincia uma conta social (google ou apple) ao perfil de um usuário existente.
        """
        provider = (provider or "google").strip().lower()
        if provider not in ('google', 'apple'):
            raise ValueError("Provedor inválido. Escolha 'google' ou 'apple'.")
        email_clean = (email or "").strip().lower()
        if not email_clean or "@" not in email_clean:
            raise ValueError("E-mail social inválido.")

        usuarios = self._carregar()
        # Verificar se esse email social já está vinculado a OUTRO usuário
        email_outro = next(
            (
                u for u in usuarios
                if u.get("id") != user_id and (
                    (u.get("email") or "").strip().lower() == email_clean or
                    (u.get(f"{provider}_email") or "").strip().lower() == email_clean
                )
            ),
            None
        )
        if email_outro:
            raise ValueError(f"A conta {provider.title()} ({email_clean}) já está vinculada a outro usuário (@{email_outro.get('username')}).")

        alvo = None
        for u in usuarios:
            if u.get("id") == user_id:
                alvo = u
                break

        if not alvo:
            raise ValueError("Usuário não encontrado.")

        alvo[f"{provider}_email"] = email_clean
        if social_id:
            alvo[f"{provider}_id"] = social_id

        social_accounts = alvo.get("social_accounts") or {}
        social_accounts[provider] = {
            "email": email_clean,
            "social_id": social_id,
            "vinculado_em": datetime.now().isoformat()
        }
        alvo["social_accounts"] = social_accounts

        self._salvar(usuarios)
        return alvo

    def desvincular_conta_social(self, user_id: str, provider: str) -> Dict:
        """
        Desvincula uma conta social (google ou apple) do perfil do usuário.
        """
        provider = (provider or "google").strip().lower()
        usuarios = self._carregar()
        alvo = None
        for u in usuarios:
            if u.get("id") == user_id:
                alvo = u
                break

        if not alvo:
            raise ValueError("Usuário não encontrado.")

        alvo.pop(f"{provider}_email", None)
        alvo.pop(f"{provider}_id", None)
        social_accounts = alvo.get("social_accounts") or {}
        social_accounts.pop(provider, None)
        alvo["social_accounts"] = social_accounts

        self._salvar(usuarios)
        return alvo


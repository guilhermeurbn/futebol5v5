"""
Service de Gestão de Clubes do NaTrave 5v5
Implementa regras de validação tipadas com Pydantic, identificação sequencial de clubes (001, 002... 1000),
verificação de unicidade global de nomes e isolamento multi-tenant.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
import re
import unicodedata
from pydantic import BaseModel, Field, field_validator
from werkzeug.security import generate_password_hash, check_password_hash

from services.db import load_json_data, save_json_data


def formatar_id_clube(id_num: int) -> str:
    """
    Formata o ID do clube de acordo com a regra de identificação:
    - Se < 1000: formato com 3 dígitos preenchidos com zero (001, 002, ..., 999)
    - Se >= 1000: mantém os dígitos completos (1000, 1001, ...)
    """
    if id_num < 1000:
        return f"{id_num:03d}"
    return str(id_num)


def normalizar_texto(texto: str) -> str:
    """Normaliza texto removendo acentos e convertendo para minúsculas."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().strip()


def gerar_slug(nome: str) -> str:
    """Gera um slug limpo e único a partir do nome do clube."""
    texto_norm = normalizar_texto(nome)
    slug = re.sub(r'[^a-z0-9]+', '-', texto_norm).strip('-')
    return slug or "clube"


class ClubeSchema(BaseModel):
    """Schema Pydantic de Validação do Clube"""
    id_num: int = Field(gt=0, description="ID numérico sequencial do clube (ex: 1 -> 001)")
    nome: str = Field(min_length=2, max_length=60, description="Nome oficial e único do clube")
    slug: str = Field(min_length=2, max_length=60, description="Identificador único de URL")
    cor_tema: str = Field(default="neon-green", description="Tema de cores selecionado pelo Admin")
    admin_user_id: Optional[str] = Field(default=None, description="ID do usuário Admin/Organizador do clube")
    senha_juiz_hash: Optional[str] = Field(default=None, description="Hash da senha do Juiz deste clube")
    criado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ativo: bool = Field(default=True)

    @field_validator('nome')
    def validar_nome(cls, v: str) -> str:
        v_clean = v.strip()
        if len(v_clean) < 2:
            raise ValueError("O nome do clube deve ter pelo menos 2 caracteres.")
        return v_clean

    @property
    def codigo_formatado(self) -> str:
        return formatar_id_clube(self.id_num)

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d['codigo_formatado'] = self.codigo_formatado
        return d


class ClubeService:
    """Serviço de gerenciamento de clubes na plataforma NaTrave"""

    @classmethod
    def _carregar_clubes(cls) -> List[dict]:
        """Carrega a lista de clubes do armazenamento de dados"""
        clubes = load_json_data("clubes", [])
        if not isinstance(clubes, list):
            clubes = []
        return clubes

    @classmethod
    def _salvar_clubes(cls, clubes: List[dict]) -> None:
        """Salva a lista de clubes no armazenamento de dados"""
        save_json_data("clubes", clubes)

    @classmethod
    def garantir_clube_natrave_001(cls) -> dict:
        """
        Garante que o Clube nº 001 (NaTrave) exista no sistema.
        Preserva 100% dos dados legados e atribui a ele o ID 1 ("001") e slug "natrave".
        """
        clubes = cls._carregar_clubes()

        clube_001 = None
        for c in clubes:
            if c.get('id_num') == 1 or c.get('slug') == 'natrave':
                clube_001 = c
                break

        if not clube_001:
            novo_clube = ClubeSchema(
                id_num=1,
                nome="NaTrave",
                slug="natrave",
                cor_tema="neon-green",
                criado_em=datetime.now(timezone.utc).isoformat(),
                ativo=True
            )
            clube_001 = novo_clube.to_dict()
            clubes.insert(0, clube_001)
            cls._salvar_clubes(clubes)
        else:
            clube_001['id_num'] = 1
            clube_001['codigo_formatado'] = "001"
            if not clube_001.get('slug'):
                clube_001['slug'] = "natrave"

        return clube_001

    @classmethod
    def obter_todos_clubes(cls) -> List[dict]:
        """Retorna todos os clubes cadastrados, garantindo o Clube 001."""
        cls.garantir_clube_natrave_001()
        clubes = cls._carregar_clubes()
        for c in clubes:
            id_n = c.get('id_num') or c.get('id') or 1
            if isinstance(id_n, str) and id_n.isdigit():
                id_n = int(id_n)
            elif not isinstance(id_n, int):
                id_n = 1
            c['id_num'] = id_n
            c['codigo_formatado'] = formatar_id_clube(id_n)
        return clubes

    @classmethod
    def obter_clube_por_id(cls, id_num: int) -> Optional[dict]:
        """Obtém um clube pelo seu ID numérico (ex: 1 para Clube 001)."""
        clubes = cls.obter_todos_clubes()
        for c in clubes:
            if c.get('id_num') == id_num:
                return c
        return None

    @classmethod
    def obter_clube_por_codigo(cls, codigo: str) -> Optional[dict]:
        """Obtém um clube pelo código formatado (ex: "001", "002", "1000") ou pelo slug."""
        if not codigo:
            return None
        cod_clean = str(codigo).strip().lstrip('0') or '0'
        try:
            id_n = int(cod_clean)
            res = cls.obter_clube_por_id(id_n)
            if res:
                return res
        except ValueError:
            pass
        return cls.obter_clube_por_slug(codigo)

    @classmethod
    def obter_clube_por_slug(cls, slug: str) -> Optional[dict]:
        """Obtém um clube pelo slug de URL (ex: "natrave")."""
        if not slug:
            return None
        slug_norm = slug.strip().lower()
        clubes = cls.obter_todos_clubes()
        for c in clubes:
            if c.get('slug', '').lower() == slug_norm:
                return c
        return None

    @classmethod
    def verificar_nome_existente(cls, nome: str, ignorar_id: Optional[int] = None) -> bool:
        """Verifica se já existe um clube com o mesmo nome (validação insensível a acentos e maiúsculas/minúsculas)."""
        nome_norm = normalizar_texto(nome)
        if not nome_norm:
            return False
        clubes = cls.obter_todos_clubes()
        for c in clubes:
            if ignorar_id and c.get('id_num') == ignorar_id:
                continue
            if normalizar_texto(c.get('nome', '')) == nome_norm:
                return True
        return False

    @classmethod
    def verificar_slug_existente(cls, slug: str, ignorar_id: Optional[int] = None) -> bool:
        """Verifica se já existe um clube com o mesmo slug."""
        slug_norm = slug.strip().lower()
        if not slug_norm:
            return False
        clubes = cls.obter_todos_clubes()
        for c in clubes:
            if ignorar_id and c.get('id_num') == ignorar_id:
                continue
            if c.get('slug', '').lower() == slug_norm:
                return True
        return False

    @classmethod
    def proximo_id_disponivel(cls) -> int:
        """Calcula o próximo ID sequencial disponível."""
        clubes = cls.obter_todos_clubes()
        ids = [c.get('id_num', 0) for c in clubes if isinstance(c.get('id_num'), int)]
        return max(ids, default=0) + 1

    @classmethod
    def criar_clube(
        cls,
        nome: str,
        slug: Optional[str] = None,
        cor_tema: str = "neon-green",
        admin_user_id: Optional[str] = None,
        senha_juiz: Optional[str] = None
    ) -> dict:
        """
        Cria um novo clube aplicando validações tipadas, cálculo de ID sequencial (001, 002...),
        associação do ID do Admin e armazenamento seguro do hash da senha do Juiz.
        """
        clubes = cls._carregar_clubes()

        if cls.verificar_nome_existente(nome):
            raise ValueError(f"Já existe um clube cadastrado com o nome '{nome}'. O nome do clube deve ser único.")

        slug_final = gerar_slug(slug or nome)
        base_slug = slug_final
        counter = 1
        while cls.verificar_slug_existente(slug_final):
            slug_final = f"{base_slug}-{counter}"
            counter += 1

        novo_id = cls.proximo_id_disponivel()
        senha_juiz_hash = generate_password_hash(senha_juiz) if senha_juiz else None

        schema_clube = ClubeSchema(
            id_num=novo_id,
            nome=nome,
            slug=slug_final,
            cor_tema=cor_tema,
            admin_user_id=admin_user_id,
            senha_juiz_hash=senha_juiz_hash,
            criado_em=datetime.now(timezone.utc).isoformat(),
            ativo=True
        )

        clube_dict = schema_clube.to_dict()
        clubes.append(clube_dict)
        cls._salvar_clubes(clubes)

        return clube_dict

    @classmethod
    def validar_senha_juiz(cls, clube_ref: str, senha_digitada: str) -> Tuple[bool, Optional[dict]]:
        """
        Valida a senha do Juiz para o clube informado (por código formatado ou slug).
        Retorna (sucesso, clube_dict).
        """
        if not clube_ref or not senha_digitada:
            return False, None

        clube = cls.obter_clube_por_codigo(clube_ref) or cls.obter_clube_por_slug(clube_ref)
        if not clube:
            return False, None

        senha_hash = clube.get('senha_juiz_hash')
        if senha_hash:
            if check_password_hash(senha_hash, senha_digitada):
                return True, clube
            return False, None

        # Fallback legado para o clube 001 NaTrave ou sem hash
        if senha_digitada == "123456" or senha_digitada == "juiz123":
            return True, clube

        return False, None

    @classmethod
    def obter_clubes_do_usuario(cls, user_id: str) -> List[dict]:
        """
        Retorna a lista de todos os clubes onde a conta do usuário tem perfil ou associação.
        Garante que o clube 001 (NaTrave) esteja sempre presente.
        """
        clube_001 = cls.garantir_clube_natrave_001()
        if not user_id:
            return [clube_001]

        from services.jogador_service import JogadorService
        jog_svc = JogadorService()
        meus_j = jog_svc.listar_por_usuario(user_id)
        if not meus_j:
            j_by_id = jog_svc.obter_por_id(user_id)
            if j_by_id:
                meus_j = [j_by_id]

        codigos_set = {"001"}
        for j in meus_j:
            j_dict = j.to_dict() if hasattr(j, 'to_dict') else (j.__dict__ if hasattr(j, '__dict__') else (j if isinstance(j, dict) else {}))
            for c_cod in j_dict.get("clubes_codigos", []):
                if c_cod:
                    codigos_set.add(str(c_cod).strip())

        todos_clubes = cls.obter_todos_clubes()
        resultado = []
        for c in todos_clubes:
            c_fmt = c.get("codigo_formatado", "")
            c_slug = c.get("slug", "")
            c_code = c.get("code", "")
            if c_fmt in codigos_set or c_slug in codigos_set or c_code in codigos_set:
                resultado.append(c)

        return resultado if resultado else [clube_001]

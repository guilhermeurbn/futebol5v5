"""
Serviço de Jogadores - Gerenciamento de dados

Fallback:
- Se DATABASE_URL estiver definido: usa Postgres
- Senão: usa JSON local
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from models.jogadores import Jogador
from services.db import get_conn


class JogadorService:
    def __init__(self, arquivo: str = "jogadores.json"):
        self.arquivo = arquivo

        if not os.getenv("DATABASE_URL"):
            self._garantir_arquivo()
        else:
            self._garantir_tabela()

    # -------- JSON --------
    def _garantir_arquivo(self) -> None:
        if not os.path.exists(self.arquivo):
            self._salvar([])

    def _carregar_raw(self) -> List[dict]:
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _salvar(self, dados: List[dict]) -> None:
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    # -------- DB --------
    def _usar_db(self) -> bool:
        return bool(os.getenv("DATABASE_URL"))

    def _garantir_tabela(self) -> None:
        conn = get_conn()
        if conn is None:
            return
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    create table if not exists jogadores (
                      id uuid primary key,
                      nome text not null,
                      nivel int not null,
                      tipo text not null,
                      posicao text not null,
                      presente boolean not null default false,
                      criado_em timestamptz not null,
                      owner_user_id uuid null
                    );
                    """
                )
        conn.close()

    # -------- API --------
    def listar(self) -> List[Jogador]:
        if not self._usar_db():
            return [Jogador.do_dict(item) for item in self._carregar_raw()]

        self._garantir_tabela()
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, nome, nivel, tipo, posicao, presente, criado_em, owner_user_id
                from jogadores
                order by criado_em asc
                """
            )
            rows = cur.fetchall()
        conn.close()
        return [
            Jogador.do_dict(
                {
                    "id": str(r[0]),
                    "nome": r[1],
                    "nivel": r[2],
                    "tipo": r[3],
                    "posicao": r[4],
                    "presente": r[5],
                    "criado_em": r[6].isoformat(),
                    "owner_user_id": str(r[7]) if r[7] else None,
                }
            )
            for r in rows
        ]

    def listar_por_usuario(self, user_id: str) -> List[Jogador]:
        if not user_id:
            return []
        if not self._usar_db():
            return [j for j in self.listar() if j.owner_user_id == user_id]

        self._garantir_tabela()
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, nome, nivel, tipo, posicao, presente, criado_em, owner_user_id
                from jogadores
                where owner_user_id = %s
                order by criado_em asc
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        conn.close()
        return [
            Jogador.do_dict(
                {
                    "id": str(r[0]),
                    "nome": r[1],
                    "nivel": r[2],
                    "tipo": r[3],
                    "posicao": r[4],
                    "presente": r[5],
                    "criado_em": r[6].isoformat(),
                    "owner_user_id": str(r[7]) if r[7] else None,
                }
            )
            for r in rows
        ]

    def listar_para_dict(self) -> List[dict]:
        if not self._usar_db():
            return self._carregar_raw()
        return [j.para_dict() for j in self.listar()]

    def listar_dict_por_usuario(self, user_id: str) -> List[dict]:
        return [j.para_dict() for j in self.listar_por_usuario(user_id)]

    def obter_por_id(self, jogador_id: str, user_id: Optional[str] = None) -> Optional[Jogador]:
        if not self._usar_db():
            jogadores = self.listar()
            if user_id:
                return next((j for j in jogadores if j.id == jogador_id and j.owner_user_id == user_id), None)
            return next((j for j in jogadores if j.id == jogador_id), None)

        self._garantir_tabela()
        conn = get_conn()
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    """
                    select id, nome, nivel, tipo, posicao, presente, criado_em, owner_user_id
                    from jogadores
                    where id = %s and owner_user_id = %s
                    """,
                    (jogador_id, user_id),
                )
            else:
                cur.execute(
                    """
                    select id, nome, nivel, tipo, posicao, presente, criado_em, owner_user_id
                    from jogadores
                    where id = %s
                    """,
                    (jogador_id,),
                )
            r = cur.fetchone()
        conn.close()
        if not r:
            return None
        return Jogador.do_dict(
            {
                "id": str(r[0]),
                "nome": r[1],
                "nivel": r[2],
                "tipo": r[3],
                "posicao": r[4],
                "presente": r[5],
                "criado_em": r[6].isoformat(),
                "owner_user_id": str(r[7]) if r[7] else None,
            }
        )

    def criar(self, nome: str, nivel: int, tipo: str = "avulso", posicao: str = "linha", owner_user_id: Optional[str] = None) -> Jogador:
        if not self._usar_db():
            jogador = Jogador(nome=nome.strip(), nivel=nivel, tipo=tipo, posicao=posicao, owner_user_id=owner_user_id)
            dados = self._carregar_raw()
            dados.append(jogador.para_dict())
            self._salvar(dados)
            return jogador

        self._garantir_tabela()
        jogador_id = str(uuid.uuid4())
        criado_em = datetime.now(timezone.utc)

        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into jogadores (id, nome, nivel, tipo, posicao, presente, criado_em, owner_user_id)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (jogador_id, nome.strip(), int(nivel), tipo, posicao, False, criado_em, owner_user_id),
                )
        conn.close()

        return Jogador.do_dict(
            {
                "id": jogador_id,
                "nome": nome.strip(),
                "nivel": int(nivel),
                "tipo": tipo,
                "posicao": posicao,
                "presente": False,
                "criado_em": criado_em.isoformat(),
                "owner_user_id": owner_user_id,
            }
        )

    def atualizar(self, jogador_id: str, nome: Optional[str] = None, nivel: Optional[int] = None, tipo: Optional[str] = None, posicao: Optional[str] = None) -> Optional[Jogador]:
        if not self._usar_db():
            jogador_existente = self.obter_por_id(jogador_id)
            if not jogador_existente:
                return None

            novo_nome = nome.strip() if isinstance(nome, str) and nome.strip() else jogador_existente.nome
            novo_nivel = int(nivel) if nivel is not None else jogador_existente.nivel

            novo_tipo = jogador_existente.tipo
            if tipo is not None:
                if tipo not in ("fixo", "avulso"):
                    raise ValueError("Tipo deve ser 'fixo' ou 'avulso'")
                novo_tipo = tipo

            nova_posicao = jogador_existente.posicao
            if posicao is not None:
                if posicao not in ("linha", "goleiro"):
                    raise ValueError("Posição deve ser 'linha' ou 'goleiro'")
                nova_posicao = posicao

            jogador_atualizado = Jogador(
                nome=novo_nome,
                nivel=novo_nivel,
                tipo=novo_tipo,
                posicao=nova_posicao,
                presente=jogador_existente.presente,
                id=jogador_id,
                criado_em=jogador_existente.criado_em,
                owner_user_id=jogador_existente.owner_user_id,
            )

            dados = self._carregar_raw()
            dados = [jogador_atualizado.para_dict() if item["id"] == jogador_id else item for item in dados]
            self._salvar(dados)
            return jogador_atualizado

        atual = self.obter_por_id(jogador_id)
        if not atual:
            return None

        novo_nome = nome.strip() if isinstance(nome, str) and nome.strip() else atual.nome
        novo_nivel = int(nivel) if nivel is not None else atual.nivel

        novo_tipo = atual.tipo
        if tipo is not None:
            if tipo not in ("fixo", "avulso"):
                raise ValueError("Tipo deve ser 'fixo' ou 'avulso'")
            novo_tipo = tipo

        nova_posicao = atual.posicao
        if posicao is not None:
            if posicao not in ("linha", "goleiro"):
                raise ValueError("Posição deve ser 'linha' ou 'goleiro'")
            nova_posicao = posicao

        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update jogadores
                    set nome=%s, nivel=%s, tipo=%s, posicao=%s
                    where id=%s
                    """,
                    (novo_nome, novo_nivel, novo_tipo, nova_posicao, jogador_id),
                )
        conn.close()
        return self.obter_por_id(jogador_id)

    def deletar(self, jogador_id: str) -> bool:
        if not self._usar_db():
            dados = self._carregar_raw()
            dados_filtrados = [j for j in dados if j["id"] != jogador_id]
            if len(dados_filtrados) == len(dados):
                return False
            self._salvar(dados_filtrados)
            return True

        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("delete from jogadores where id=%s", (jogador_id,))
                deleted = cur.rowcount > 0
        conn.close()
        return deleted

    def contar(self) -> int:
        return len(self.listar())

    def listar_presentes(self) -> List[Jogador]:
        return [j for j in self.listar() if j.presente]

    def listar_por_tipo(self, tipo: str) -> List[Jogador]:
        if tipo not in ["fixo", "avulso"]:
            raise ValueError("Tipo deve ser 'fixo' ou 'avulso'")
        return [j for j in self.listar() if j.tipo == tipo]

    def marcar_presenca(self, jogador_ids: List[str]) -> bool:
        if not self._usar_db():
            dados = self._carregar_raw()
            ids_set = set(jogador_ids)
            for item in dados:
                item["presente"] = item["id"] in ids_set
            self._salvar(dados)
            return True

        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("update jogadores set presente = false")
                if jogador_ids:
                    cur.execute(
                        "update jogadores set presente = true where id = any(%s::uuid[])",
                        (jogador_ids,),
                    )
        conn.close()
        return True

    def limpar_presenca(self) -> bool:
        if not self._usar_db():
            dados = self._carregar_raw()
            for item in dados:
                item["presente"] = False
            self._salvar(dados)
            return True

        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("update jogadores set presente = false")
        conn.close()
        return True

    def contar_presentes(self) -> int:
        return len(self.listar_presentes())
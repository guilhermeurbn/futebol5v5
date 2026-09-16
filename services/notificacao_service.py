"""
Servico de notificacoes internas para administradores.
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from services.db import load_json_data, save_json_data


class NotificacaoService:
    """Armazena notificacoes administrativas em arquivo JSON."""

    _TIPOS_VALIDOS = {"info", "cadastro", "alerta", "sucesso", "erro", "warning"}

    def __init__(self, arquivo: str = "data/admin_notificacoes.json"):
        self.arquivo = arquivo
        self._garantir_arquivo()

    def _garantir_arquivo(self) -> None:
        if os.getenv("DATABASE_URL"):
            return
        if not os.path.exists(self.arquivo):
            self._salvar({"ultimo_id": 0, "notificacoes": [], "arquivadas": []})

    def _carregar(self) -> Dict:
        if os.getenv("DATABASE_URL"):
            dados = load_json_data("admin_notificacoes", {"ultimo_id": 0, "notificacoes": []})
            if not isinstance(dados, dict):
                return {"ultimo_id": 0, "notificacoes": [], "arquivadas": []}
            dados.setdefault("ultimo_id", 0)
            dados.setdefault("notificacoes", [])
            dados.setdefault("arquivadas", [])
            return dados
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if not isinstance(dados, dict):
                return {"ultimo_id": 0, "notificacoes": [], "arquivadas": []}
            dados.setdefault("ultimo_id", 0)
            dados.setdefault("notificacoes", [])
            dados.setdefault("arquivadas", [])
            return dados
        except (FileNotFoundError, json.JSONDecodeError):
            return {"ultimo_id": 0, "notificacoes": [], "arquivadas": []}

    def _salvar(self, dados: Dict) -> None:
        if os.getenv("DATABASE_URL"):
            save_json_data("admin_notificacoes", dados)
            return
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    def _obter_clube_codigo(self, clube_codigo: Optional[str] = None) -> str:
        if clube_codigo and str(clube_codigo).strip():
            c = str(clube_codigo).strip()
            return c.zfill(3) if c.isdigit() else c
        try:
            from flask import g, session
            if hasattr(g, 'clube_codigo') and g.clube_codigo:
                c = str(g.clube_codigo).strip()
                return c.zfill(3) if c.isdigit() else c
            if session.get('clube_codigo'):
                c = str(session.get('clube_codigo')).strip()
                return c.zfill(3) if c.isdigit() else c
        except Exception:
            pass
        return "001"

    def _normalizar_tipo(self, tipo: str) -> str:
        tipo_normalizado = (tipo or "info").strip().lower()
        return tipo_normalizado if tipo_normalizado in self._TIPOS_VALIDOS else "info"

    def criar_notificacao(self, titulo: str, mensagem: str, tipo: str = "info", clube_codigo: Optional[str] = None) -> Dict:
        dados = self._carregar()
        novo_id = int(dados.get("ultimo_id", 0)) + 1
        cod = self._obter_clube_codigo(clube_codigo)
        notificacao = {
            "id": novo_id,
            "clube_codigo": cod,
            "titulo": (titulo or "Notificacao").strip(),
            "mensagem": (mensagem or "").strip(),
            "tipo": self._normalizar_tipo(tipo),
            "lida": False,
            "criado_em": datetime.now().isoformat(),
        }
        dados["ultimo_id"] = novo_id
        dados.setdefault("notificacoes", []).append(notificacao)
        self._salvar(dados)
        return notificacao

    def listar_notificacoes(self, apenas_nao_lidas: bool = False, limite: int = 20, clube_codigo: Optional[str] = None) -> List[Dict]:
        cod = self._obter_clube_codigo(clube_codigo)
        dados = self._carregar()
        notificacoes = [n for n in dados.get("notificacoes", []) if n.get("clube_codigo", "001") == cod]
        notificacoes = list(reversed(notificacoes))
        if apenas_nao_lidas:
            notificacoes = [n for n in notificacoes if not n.get("lida", False)]
        retorno = []
        for n in notificacoes[:max(1, int(limite))]:
            item = dict(n)
            item["tipo"] = self._normalizar_tipo(item.get("tipo"))
            retorno.append(item)
        return retorno

    def listar_arquivadas(self, limite: int = 20, clube_codigo: Optional[str] = None) -> List[Dict]:
        cod = self._obter_clube_codigo(clube_codigo)
        dados = self._carregar()
        arquivadas = [n for n in dados.get("arquivadas", []) if n.get("clube_codigo", "001") == cod]
        arquivadas = list(reversed(arquivadas))
        retorno = []
        for n in arquivadas[:max(1, int(limite))]:
            item = dict(n)
            item["tipo"] = self._normalizar_tipo(item.get("tipo"))
            retorno.append(item)
        return retorno

    def contar_nao_lidas(self, clube_codigo: Optional[str] = None) -> int:
        cod = self._obter_clube_codigo(clube_codigo)
        dados = self._carregar()
        return sum(1 for n in dados.get("notificacoes", []) if n.get("clube_codigo", "001") == cod and not n.get("lida", False))

    def marcar_todas_como_lidas(self, clube_codigo: Optional[str] = None) -> None:
        cod = self._obter_clube_codigo(clube_codigo)
        dados = self._carregar()
        notificacoes_ativas = dados.get("notificacoes", [])
        if not notificacoes_ativas:
            return

        arquivadas = dados.setdefault("arquivadas", [])
        novas_ativas = []
        for n in notificacoes_ativas:
            if n.get("clube_codigo", "001") == cod:
                n["lida"] = True
                arquivadas.append(n)
            else:
                novas_ativas.append(n)
        dados["notificacoes"] = novas_ativas
        if arquivadas:
            self._salvar(dados)

    def marcar_como_lida(self, notif_id: str) -> bool:
        dados = self._carregar()
        notificacoes = dados.get("notificacoes", [])
        alvo = None
        novas = []
        for n in notificacoes:
            if n.get("id") == notif_id or str(n.get("id")) == str(notif_id):
                alvo = n
            else:
                novas.append(n)
        
        if alvo:
            alvo["lida"] = True
            arquivadas = dados.setdefault("arquivadas", [])
            arquivadas.append(alvo)
            dados["notificacoes"] = novas
            self._salvar(dados)
            return True
        return False

    def limpar_arquivadas(self) -> None:
        dados = self._carregar()
        dados["arquivadas"] = []
        self._salvar(dados)
"""
Servico de notificacoes internas para administradores.
"""
import json
import os
from datetime import datetime
from typing import Dict, List
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

    def _normalizar_tipo(self, tipo: str) -> str:
        tipo_normalizado = (tipo or "info").strip().lower()
        return tipo_normalizado if tipo_normalizado in self._TIPOS_VALIDOS else "info"

    def criar_notificacao(self, titulo: str, mensagem: str, tipo: str = "info") -> Dict:
        dados = self._carregar()
        novo_id = int(dados.get("ultimo_id", 0)) + 1
        notificacao = {
            "id": novo_id,
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

    def listar_notificacoes(self, apenas_nao_lidas: bool = False, limite: int = 20) -> List[Dict]:
        dados = self._carregar()
        notificacoes = list(reversed(dados.get("notificacoes", [])))
        if apenas_nao_lidas:
            notificacoes = [n for n in notificacoes if not n.get("lida", False)]
        retorno = []
        for n in notificacoes[:max(1, int(limite))]:
            item = dict(n)
            item["tipo"] = self._normalizar_tipo(item.get("tipo"))
            retorno.append(item)
        return retorno

    def listar_arquivadas(self, limite: int = 20) -> List[Dict]:
        dados = self._carregar()
        arquivadas = list(reversed(dados.get("arquivadas", [])))
        retorno = []
        for n in arquivadas[:max(1, int(limite))]:
            item = dict(n)
            item["tipo"] = self._normalizar_tipo(item.get("tipo"))
            retorno.append(item)
        return retorno

    def contar_nao_lidas(self) -> int:
        dados = self._carregar()
        return sum(1 for n in dados.get("notificacoes", []) if not n.get("lida", False))

    def marcar_todas_como_lidas(self) -> None:
        dados = self._carregar()
        notificacoes_ativas = dados.get("notificacoes", [])
        if not notificacoes_ativas:
            return

        arquivadas = dados.setdefault("arquivadas", [])
        for n in notificacoes_ativas:
            n["lida"] = True
        arquivadas.extend(notificacoes_ativas)
        dados["notificacoes"] = []
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
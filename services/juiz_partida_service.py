"""
Servico para orquestrar o fluxo unico da partida do juiz.
"""
import json
import os
from datetime import datetime
from typing import Dict, Optional
from services.db import load_json_data, save_json_data


class JuizPartidaService:
    """Mantem o estado persistido da partida atual do juiz."""

    def __init__(self, arquivo: str = "data/juiz_partida_atual.json"):
        self.arquivo = arquivo
        self._garantir_arquivo()

    def _estado_vazio(self) -> Dict:
        return {
            "status": "idle",
            "partida_atual": None,
            "ultima_partida_encerrada": None,
        }

    def _garantir_arquivo(self) -> None:
        if os.getenv("DATABASE_URL"):
            return
        if not os.path.exists(self.arquivo):
            self._salvar_raw_todos({"001": self._estado_vazio()})

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

    def _carregar_todos(self) -> Dict:
        if os.getenv("DATABASE_URL"):
            dados = load_json_data("juiz_partida_atual", {})
        else:
            try:
                with open(self.arquivo, "r", encoding="utf-8") as f:
                    dados = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                dados = {}
        if not isinstance(dados, dict):
            dados = {}
        if "status" in dados or "partida_atual" in dados:
            dados = {"001": dados}
        return dados

    def _carregar(self, clube_codigo: Optional[str] = None) -> Dict:
        cod = self._obter_clube_codigo(clube_codigo)
        todos = self._carregar_todos()
        estado = todos.get(cod)
        if not isinstance(estado, dict):
            estado = self._estado_vazio()
        estado.setdefault("status", "idle")
        estado.setdefault("partida_atual", None)
        estado.setdefault("ultima_partida_encerrada", None)
        return estado

    def _salvar(self, dados: Dict, clube_codigo: Optional[str] = None) -> None:
        cod = self._obter_clube_codigo(clube_codigo)
        todos = self._carregar_todos()
        todos[cod] = dados
        if os.getenv("DATABASE_URL"):
            save_json_data("juiz_partida_atual", todos)
            return
        os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(todos, f, indent=2, ensure_ascii=False)

    def obter_estado(self, clube_codigo: Optional[str] = None) -> Dict:
        return self._carregar(clube_codigo)

    def iniciar_partida(self, criado_por: Optional[str] = None) -> Dict:
        dados = self._carregar()
        dados["status"] = "selecionando"
        dados["partida_atual"] = {
            "status": "selecionando",
            "criado_por": criado_por,
            "criado_em": datetime.now().isoformat(),
            "quantidade_jogadores": None,
            "jogador_ids": [],
            "sorteio_id": None,
            "resultado_registrado": False,
            "resultado_partida_id": None,
            "votacao_partida_id": None,
            "votacao_aberta": False,
        }
        self._salvar(dados)
        return dados

    def registrar_selecao(self, quantidade_jogadores: int, jogador_ids) -> Dict:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        partida["status"] = "selecionando"
        partida["quantidade_jogadores"] = int(quantidade_jogadores)
        partida["jogador_ids"] = list(jogador_ids or [])
        dados["status"] = "selecionando"
        dados["partida_atual"] = partida
        self._salvar(dados)
        return dados

    def salvar_rascunho_sorteio(self, times_json: list, somas: list, diferenca: float) -> Dict:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        partida["status"] = "sorteada"
        partida["rascunho_sorteio"] = {
            "times": times_json,
            "somas": somas,
            "diferenca": diferenca,
            "num_times": len(times_json),
            "total_jogadores": sum(len(t.get('jogadores', [])) for t in times_json),
            "criado_em": datetime.now().isoformat()
        }
        partida["sorteio_id"] = None
        partida["resultado_registrado"] = False
        partida["resultado_partida_id"] = None
        partida["votacao_partida_id"] = None
        partida["votacao_aberta"] = False
        dados["status"] = "sorteada"
        dados["partida_atual"] = partida
        self._salvar(dados)
        return dados

    def obter_rascunho(self) -> Optional[Dict]:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        return partida.get("rascunho_sorteio")

    def atualizar_rascunho_times(self, times_json: list) -> Optional[Dict]:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        rascunho = partida.get("rascunho_sorteio")
        if not rascunho:
            return None

        pontuacoes = []
        total_jogadores = 0
        for time in times_json:
            jogadores = time.get('jogadores', []) or []
            soma_time = round(sum(float(j.get('nivel', 0) or 0) for j in jogadores), 2)
            pontuacoes.append(soma_time)
            total_jogadores += len(jogadores)

        diferenca = 0
        if pontuacoes:
            diferenca = round(max(pontuacoes) - min(pontuacoes), 2)

        rascunho['times'] = times_json
        rascunho['somas'] = pontuacoes
        rascunho['diferenca'] = diferenca
        rascunho['total_jogadores'] = total_jogadores
        rascunho['atualizado_em'] = datetime.now().isoformat()

        partida['rascunho_sorteio'] = rascunho
        dados['partida_atual'] = partida
        self._salvar(dados)
        return rascunho

    def limpar_rascunho(self) -> Dict:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        partida.pop("rascunho_sorteio", None)
        dados["partida_atual"] = partida
        self._salvar(dados)
        return dados

    def registrar_sorteio(self, sorteio_id: int) -> Dict:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        partida["status"] = "sorteada"
        partida["sorteio_id"] = int(sorteio_id)
        partida.pop("rascunho_sorteio", None)
        partida["resultado_registrado"] = False
        partida["resultado_partida_id"] = None
        partida["votacao_partida_id"] = None
        partida["votacao_aberta"] = False
        dados["status"] = "sorteada"
        dados["partida_atual"] = partida
        self._salvar(dados)
        return dados

    def salvar_rascunho_resultado(self, sorteio_id: int, rascunho: Dict) -> Dict:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        partida["sorteio_id"] = int(sorteio_id)
        if isinstance(rascunho, dict):
            rascunho["atualizado_em"] = datetime.now().isoformat()
        partida["rascunho_resultado"] = rascunho
        dados["partida_atual"] = partida
        self._salvar(dados)
        return dados

    def obter_rascunho_resultado(self, sorteio_id: Optional[int] = None) -> Optional[Dict]:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        if sorteio_id and int(partida.get("sorteio_id", 0) or 0) != int(sorteio_id):
            return None
        return partida.get("rascunho_resultado")

    def limpar_rascunho_resultado(self, sorteio_id: Optional[int] = None) -> Dict:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        partida.pop("rascunho_resultado", None)
        dados["partida_atual"] = partida
        self._salvar(dados)
        return dados

    def marcar_resultado_registrado(self, sorteio_id: int, resultado_partida_id: Optional[int] = None) -> Dict:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        partida["status"] = "resultado_registrado"
        partida["sorteio_id"] = int(sorteio_id)
        partida["resultado_registrado"] = True
        partida["resultado_partida_id"] = resultado_partida_id
        partida.pop("rascunho_resultado", None)
        dados["status"] = "resultado_registrado"
        dados["partida_atual"] = partida
        self._salvar(dados)
        return dados

    def marcar_votacao_aberta(self, sorteio_id: int, votacao_partida_id: int) -> Dict:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        partida["status"] = "votacao_aberta"
        partida["sorteio_id"] = int(sorteio_id)
        partida["votacao_partida_id"] = int(votacao_partida_id)
        partida["votacao_aberta"] = True
        dados["status"] = "votacao_aberta"
        dados["partida_atual"] = partida
        self._salvar(dados)
        return dados

    def finalizar_partida(self, resumo: Optional[Dict] = None) -> Dict:
        dados = self._carregar()
        dados["status"] = "idle"
        dados["partida_atual"] = None
        if resumo:
            dados["ultima_partida_encerrada"] = resumo
        self._salvar(dados)
        return dados

    def reabrir_partida(self, sorteio_id: int) -> Dict:
        dados = self._carregar()
        partida = dados.get("partida_atual")
        if not partida or int(partida.get("sorteio_id", 0) or 0) != int(sorteio_id):
            ultima = dados.get("ultima_partida_encerrada") or {}
            partida = {
                "id": f"sorteio_{sorteio_id}",
                "sorteio_id": int(sorteio_id),
                "status": "votacao_aberta",
                "resultado_registrado": True,
                "votacao_partida_id": None,
                "votacao_aberta": True
            }
        else:
            partida["status"] = "votacao_aberta"
            partida["votacao_aberta"] = True

        dados["status"] = "votacao_aberta"
        dados["partida_atual"] = partida
        dados["ultima_partida_encerrada"] = None
        self._salvar(dados)
        return dados

    def limpar_ultima_partida_encerrada(self) -> Dict:
        dados = self._carregar()
        dados["ultima_partida_encerrada"] = None
        self._salvar(dados)
        return dados

    def cancelar_selecao(self) -> Dict:
        dados = self._carregar()
        if dados.get("status") == "selecionando":
            dados["status"] = "idle"
            dados["partida_atual"] = None
            self._salvar(dados)
        return dados

    def resetar(self) -> Dict:
        dados = self._estado_vazio()
        self._salvar(dados)
        return dados

"""
Servico para orquestrar o fluxo unico da partida do juiz.
"""
import json
import os
from datetime import datetime
from typing import Dict, Optional


class JuizPartidaService:
    """Mantem o estado persistido da partida atual do juiz."""

    def __init__(self, arquivo: str = "juiz_partida_atual.json"):
        self.arquivo = arquivo
        self._garantir_arquivo()

    def _estado_vazio(self) -> Dict:
        return {
            "status": "idle",
            "partida_atual": None,
            "ultima_partida_encerrada": None,
        }

    def _garantir_arquivo(self) -> None:
        if not os.path.exists(self.arquivo):
            self._salvar(self._estado_vazio())

    def _carregar(self) -> Dict:
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if not isinstance(dados, dict):
                return self._estado_vazio()
            dados.setdefault("status", "idle")
            dados.setdefault("partida_atual", None)
            dados.setdefault("ultima_partida_encerrada", None)
            return dados
        except (FileNotFoundError, json.JSONDecodeError):
            return self._estado_vazio()

    def _salvar(self, dados: Dict) -> None:
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    def obter_estado(self) -> Dict:
        return self._carregar()

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

    def registrar_sorteio(self, sorteio_id: int) -> Dict:
        dados = self._carregar()
        partida = dados.get("partida_atual") or {}
        partida["status"] = "sorteada"
        partida["sorteio_id"] = int(sorteio_id)
        partida["resultado_registrado"] = False
        partida["resultado_partida_id"] = None
        partida["votacao_partida_id"] = None
        partida["votacao_aberta"] = False
        dados["status"] = "sorteada"
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

    def limpar_ultima_partida_encerrada(self) -> Dict:
        dados = self._carregar()
        dados["ultima_partida_encerrada"] = None
        self._salvar(dados)
        return dados

    def resetar(self) -> Dict:
        dados = self._estado_vazio()
        self._salvar(dados)
        return dados

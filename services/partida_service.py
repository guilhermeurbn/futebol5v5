"""
Serviço de Partidas e Resultados Competitivos
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from services.db import load_json_data, save_json_data


class PartidaService:
    """Serviço para gerenciar partidas e resultados competitivos"""
    
    def __init__(self, arquivo: str = "data/partidas.json"):
        """
        Inicializa o serviço
        
        Args:
            arquivo: Caminho do arquivo JSON
        """
        self.arquivo = arquivo
        self._garantir_arquivo()
    
    def _garantir_arquivo(self) -> None:
        """Garante que o arquivo existe"""
        if os.getenv("DATABASE_URL"):
            return
        if not os.path.exists(self.arquivo):
            self._salvar([])
    
    def _carregar_raw(self) -> List[dict]:
        """Carrega dados de partidas"""
        return load_json_data("partidas", [])
    
    def _salvar(self, dados: List[dict]) -> None:
        """Salva dados de partidas e invalida estatísticas"""
        save_json_data("partidas", dados)
        from services.jogador_stats_service import JogadorStatsService
        JogadorStatsService.invalidar_cache_stats()

    def _garantir_stats_time(self, placar: Dict, time_numero: int) -> None:
        """Garante estrutura padrão de estatísticas para um time."""
        chave = f"time_{time_numero}"
        if chave not in placar:
            placar[chave] = {"vitórias": 0, "empates": 0, "derrotas": 0}

    def _diferenca_placar(self, gols_times: List[int]) -> int:
        """Calcula a maior diferença de gols entre quaisquer dois times."""
        if len(gols_times) < 2:
            return 0
        diferencas = []
        for i, gols_a in enumerate(gols_times):
            for gols_b in gols_times[i + 1:]:
                diferencas.append(abs(gols_a - gols_b))
        return max(diferencas, default=0)
    
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

    def registrar_resultado(self, sorteio_id: int, time_vencedor: Optional[int],
                           gols_times: List[int], notas: str = "",
                           times_desempenho: Optional[List[Dict]] = None,
                           card_campeao_url: Optional[str] = None,
                           clube_codigo: Optional[str] = None) -> Dict:
        """
        Registra o resultado de uma partida
        """
        partidas = self._carregar_raw()
        cod = self._obter_clube_codigo(clube_codigo)
        
        existente = next((p for p in partidas if int(p.get("sorteio_id", 0) or 0) == int(sorteio_id)), None)
        if existente:
            existente["time_vencedor"] = time_vencedor
            existente["gols_times"] = gols_times
            existente["notas"] = notas
            existente["times_desempenho"] = times_desempenho or []
            if not existente.get("clube_codigo"):
                existente["clube_codigo"] = cod
            if card_campeao_url:
                existente["card_campeao_url"] = card_campeao_url
            existente["atualizado_em"] = datetime.now().isoformat()
            partida = existente
        else:
            ultimo_id = max((int(p.get("id", 0) or 0) for p in partidas), default=0)
            partida = {
                "id": ultimo_id + 1,
                "sorteio_id": sorteio_id,
                "clube_codigo": cod,
                "data": datetime.now().isoformat(),
                "time_vencedor": time_vencedor,
                "gols_times": gols_times,
                "notas": notas,
                "times_desempenho": times_desempenho or [],
                "card_campeao_url": card_campeao_url or ""
            }
            partidas.append(partida)

        self._salvar(partidas)
        return partida
    
    def obter_partidas_sorteio(self, sorteio_id: int) -> List[Dict]:
        """Obtém todas as partidas de um sorteio"""
        partidas = self._carregar_raw()
        return [p for p in partidas if p.get('sorteio_id') == sorteio_id]

    def atualizar_foto_campeao(self, sorteio_id: int, card_campeao_url: str, clube_codigo: Optional[str] = None) -> Dict:
        """Atualiza a foto/card do time campeão de um sorteio existente ou cria registro."""
        partidas = self._carregar_raw()
        sorteio_id_int = int(sorteio_id)
        cod = self._obter_clube_codigo(clube_codigo)
        existente = next((p for p in partidas if int(p.get("sorteio_id", 0) or 0) == sorteio_id_int), None)
        
        if existente:
            existente["card_campeao_url"] = card_campeao_url
            existente["atualizado_em"] = datetime.now().isoformat()
            if not existente.get("clube_codigo"):
                existente["clube_codigo"] = cod
            self._salvar(partidas)
            return existente
        else:
            ultimo_id = max((int(p.get("id", 0) or 0) for p in partidas), default=0)
            partida = {
                "id": ultimo_id + 1,
                "sorteio_id": sorteio_id_int,
                "clube_codigo": cod,
                "data": datetime.now().isoformat(),
                "time_vencedor": None,
                "gols_times": [],
                "notas": "Atualizado pelo Admin",
                "times_desempenho": [],
                "card_campeao_url": card_campeao_url
            }
            partidas.append(partida)
            self._salvar(partidas)
            return partida
    
    def listar_partidas(self, limite: int = 10, clube_codigo: Optional[str] = None) -> List[Dict]:
        """Lista as últimas partidas filtradas pelo clube ativo/fornecido"""
        cod = self._obter_clube_codigo(clube_codigo)
        partidas = [p for p in self._carregar_raw() if p.get("clube_codigo", "001") == cod]
        return sorted(partidas, key=lambda x: x.get('data', ''), reverse=True)[:limite]

    def deletar_partida_do_sorteio(self, sorteio_id: int) -> bool:
        """Deleta partidas/resultados vinculados a um sorteio_id"""
        partidas = self._carregar_raw()
        sorteio_id_int = int(sorteio_id)
        filtradas = [
            p for p in partidas
            if int(p.get('sorteio_id', 0) or 0) != sorteio_id_int and int(p.get('id', 0) or 0) != sorteio_id_int
        ]
        if len(filtradas) != len(partidas):
            self._salvar(filtradas)
            return True
        return False

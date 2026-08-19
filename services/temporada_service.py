import json
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "temporadas.json")


class TemporadaService:
    """
    Gerencia as temporadas de competição de ranking do NaTrave 5v5.
    Calcula datas de início/fim, contagem regressiva, progresso e prêmios.
    """

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = data_file or DATA_FILE
        self.dados = self._carregar_dados()

    def _carregar_dados(self) -> Dict[str, Any]:
        from services.db import load_json_data, save_json_data
        padrao = {
            "temporada_ativa": {
                "id": 1,
                "nome": "Temporada #1 - Edição de Prêmios 🏆",
                "data_inicio": "2026-07-01T00:00:00",
                "data_fim": "2026-10-04T23:59:59",
                "descricao_premio": "🏆 1º Lugar: Prêmio Especial da Temporada NaTrave!",
                "ativa": True
            },
            "historico_temporadas": []
        }
        dados = load_json_data("temporadas", padrao)
        if not dados or not isinstance(dados, dict) or "temporada_ativa" not in dados:
            save_json_data("temporadas", padrao)
            return padrao

        # Garantir que a primeira temporada ativa em produção inclua todas as partidas desde Julho
        temp_ativa = dados.get("temporada_ativa", {})
        historico_temp = dados.get("historico_temporadas", [])
        if not historico_temp and temp_ativa.get("data_inicio", "") > "2026-07-01T00:00:00":
            temp_ativa["data_inicio"] = "2026-07-01T00:00:00"
            save_json_data("temporadas", dados)

        return dados

    def _salvar_dados(self, dados: Optional[Dict[str, Any]] = None):
        from services.db import save_json_data
        if dados is None:
            dados = self.dados
        save_json_data("temporadas", dados)

    def obter_temporada_ativa(self, total_partidas_periodo: int = 0) -> Dict[str, Any]:
        from services.time_utils import obter_agora_local
        temp = self.dados.get("temporada_ativa", {})
        if not temp:
            return {}

        dt_inicio = datetime.fromisoformat(temp["data_inicio"])
        dt_fim = datetime.fromisoformat(temp["data_fim"])
        agora = obter_agora_local()
        tipo_duracao = temp.get("tipo_duracao", "meses")
        limite_partidas = temp.get("limite_partidas")

        dias_totais = max(1, (dt_fim - dt_inicio).days)
        
        if tipo_duracao == "partidas" and limite_partidas:
            dias_restantes = max(0, (dt_fim - agora).days)
            dias_para_inicio = 0
            progresso_pct = min(100.0, round((total_partidas_periodo / limite_partidas) * 100, 1))
            if total_partidas_periodo >= limite_partidas:
                status_tempo = "encerrada"
            else:
                status_tempo = "em_andamento"
        else:
            if agora < dt_inicio:
                status_tempo = "futura"
                dias_para_inicio = max(0, (dt_inicio - agora).days)
                dias_restantes = dias_totais
                progresso_pct = 0.0
            elif agora > dt_fim:
                status_tempo = "encerrada"
                dias_para_inicio = 0
                dias_restantes = 0
                progresso_pct = 100.0
            else:
                status_tempo = "em_andamento"
                dias_para_inicio = 0
                dias_passados = (agora - dt_inicio).days
                dias_restantes = max(0, (dt_fim - agora).days)
                progresso_pct = round((dias_passados / dias_totais) * 100, 1)

        res = dict(temp)
        res.update({
            "status_tempo": status_tempo,
            "dias_totais": dias_totais,
            "dias_restantes": dias_restantes,
            "dias_para_inicio": dias_para_inicio if status_tempo == "futura" else 0,
            "progresso_pct": progresso_pct,
            "partidas_jogadas": total_partidas_periodo,
            "data_inicio_fmt": dt_inicio.strftime("%d/%m/%Y"),
            "data_fim_fmt": dt_fim.strftime("%d/%m/%Y"),
        })
        return res

    def abrir_nova_competicao(
        self,
        nome: str,
        tipo_duracao: str = "partidas",
        valor_duracao: int = 10,
        descricao_premio: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Arquiva a competição atual e abre uma nova competição zerada no fuso horário local da Europa (Europe/Lisbon).
        Partidas de competições anteriores ficam no histórico arquivado.
        """
        from services.time_utils import obter_agora_local
        agora = obter_agora_local()

        # Arquivar a temporada ativa anterior se existir
        temp_atual = self.dados.get("temporada_ativa")
        if temp_atual:
            temp_atual["ativa"] = False
            temp_atual["encerrada_em"] = agora.isoformat()
            self.dados.setdefault("historico_temporadas", []).append(temp_atual)

        # Início da nova competição no começo do dia atual no fuso horário da Europa
        dt_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        if tipo_duracao == "meses":
            dias = max(1, valor_duracao * 30)
            dt_fim = (agora + timedelta(days=dias)).replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
            limite_partidas = None
        else:  # "partidas"
            dt_fim = (agora + timedelta(days=365)).replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
            limite_partidas = max(1, valor_duracao)

        novo_id = len(self.dados.get("historico_temporadas", [])) + 1

        nova_temporada = {
            "id": novo_id,
            "nome": nome or f"Competição #{novo_id}",
            "tipo_duracao": tipo_duracao,
            "valor_duracao": valor_duracao,
            "limite_partidas": limite_partidas,
            "data_inicio": dt_inicio,
            "data_fim": dt_fim,
            "descricao_premio": descricao_premio or "",
            "criada_em": agora.isoformat(),
            "ativa": True
        }

        self.dados["temporada_ativa"] = nova_temporada
        self._salvar_dados()
        return self.obter_temporada_ativa()

    def atualizar_temporada(self, nome: str, data_inicio: str, data_fim: str, descricao_premio: str):
        temp = self.dados.setdefault("temporada_ativa", {})
        temp["nome"] = nome
        temp["data_inicio"] = data_inicio
        temp["data_fim"] = data_fim
        temp["descricao_premio"] = descricao_premio
        temp["ativa"] = True
        self._salvar_dados()

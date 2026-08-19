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
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        return json.loads(content)
            except Exception as e:
                logger.error(f"Erro ao carregar temporadas.json: {str(e)}")
        
        # Configuração padrão da Temporada #1 (Julho a Outubro)
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
        self._salvar_dados(padrao)
        return padrao

    def _salvar_dados(self, dados: Optional[Dict[str, Any]] = None):
        if dados is None:
            dados = self.dados
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar temporadas.json: {str(e)}")

    def obter_temporada_ativa(self, total_partidas_periodo: int = 0) -> Dict[str, Any]:
        temp = self.dados.get("temporada_ativa", {})
        if not temp:
            return {}

        dt_inicio = datetime.fromisoformat(temp["data_inicio"])
        dt_fim = datetime.fromisoformat(temp["data_fim"])
        agora = datetime.now()
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
        Arquiva a competição atual e abre uma nova competição zerada a partir de agora.
        """
        agora = datetime.now()

        # Arquivar a temporada ativa anterior se existir
        temp_atual = self.dados.get("temporada_ativa")
        if temp_atual:
            temp_atual["ativa"] = False
            temp_atual["encerrada_em"] = agora.isoformat()
            self.dados.setdefault("historico_temporadas", []).append(temp_atual)

        # Incluir todas as partidas anteriores registradas no perfil para a competição
        dt_inicio = "2020-01-01T00:00:00"

        if tipo_duracao == "meses":
            dias = max(1, valor_duracao * 30)
            dt_fim = (agora + timedelta(days=dias)).isoformat()
            limite_partidas = None
        else:  # "partidas"
            dt_fim = (agora + timedelta(days=365)).isoformat()
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

import json
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "temporadas.json")


class TemporadaService:
    """
    Gerencia as temporadas de competição de ranking do NaTrave 5v5 com suporte multi-clube.
    Calcula datas de início/fim, contagem regressiva, progresso e prêmios.
    O clube original '001' mantém seu histórico e temporada legada. Novos clubes iniciam zerados.
    """

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = data_file or DATA_FILE

    def _obter_clube_codigo(self, clube_codigo: Optional[str] = None) -> str:
        if clube_codigo and str(clube_codigo).strip():
            c = str(clube_codigo).strip()
            return c.zfill(3) if c.isdigit() else c
        try:
            from flask import g, session, has_request_context
            if has_request_context():
                if hasattr(g, 'clube_codigo') and g.clube_codigo:
                    c = str(g.clube_codigo).strip()
                    return c.zfill(3) if c.isdigit() else c
                if session.get('clube_codigo'):
                    c = str(session.get('clube_codigo')).strip()
                    return c.zfill(3) if c.isdigit() else c
        except Exception:
            pass
        return "001"

    def _carregar_dados_arquivo_teste(self, cod: str) -> Dict[str, Any]:
        padrao_001 = {
            "temporada_ativa": {
                "id": 1,
                "nome": "Temporada #1 - Edição de Prêmios",
                "data_inicio": "2026-07-01T00:00:00",
                "data_fim": "2026-10-04T23:59:59",
                "descricao_premio": "🏆 1º Lugar: Prêmio Especial da Temporada NaTrave!",
                "ativa": True
            },
            "historico_temporadas": []
        }
        padrao_novo = {
            "temporada_ativa": None,
            "historico_temporadas": []
        }

        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    conteudo = json.load(f)
            except Exception:
                conteudo = {}
        else:
            conteudo = {}

        if not isinstance(conteudo, dict):
            conteudo = {}

        if "temporada_ativa" in conteudo or "historico_temporadas" in conteudo:
            conteudo = {"001": conteudo}

        if cod == "001":
            if "001" not in conteudo:
                conteudo["001"] = padrao_001
                try:
                    with open(self.data_file, 'w', encoding='utf-8') as f:
                        json.dump(conteudo, f, indent=2)
                except Exception:
                    pass
            return conteudo["001"]
        else:
            if cod not in conteudo:
                conteudo[cod] = padrao_novo
            return conteudo[cod]

    def _carregar_dados(self, clube_codigo: Optional[str] = None) -> Dict[str, Any]:
        cod = self._obter_clube_codigo(clube_codigo)

        if self.data_file and self.data_file != DATA_FILE:
            return self._carregar_dados_arquivo_teste(cod)

        from services.db import load_json_data, save_json_data

        padrao_001 = {
            "temporada_ativa": {
                "id": 1,
                "nome": "Temporada #1 - Edição de Prêmios",
                "data_inicio": "2026-07-01T00:00:00",
                "data_fim": "2026-10-04T23:59:59",
                "descricao_premio": "🏆 1º Lugar: Prêmio Especial da Temporada NaTrave!",
                "ativa": True
            },
            "historico_temporadas": []
        }
        padrao_novo = {
            "temporada_ativa": None,
            "historico_temporadas": []
        }

        default_dados = padrao_001 if cod == "001" else padrao_novo
        dados = load_json_data("temporadas", default_dados, clube_codigo=cod)

        if not isinstance(dados, dict):
            dados = default_dados

        # Para o clube 001, manter consistência com início em Julho
        if cod == "001":
            if not dados.get("temporada_ativa"):
                dados["temporada_ativa"] = padrao_001["temporada_ativa"]
            temp_ativa = dados.get("temporada_ativa", {})
            historico_temp = dados.get("historico_temporadas", [])
            if not historico_temp and temp_ativa.get("data_inicio", "") > "2026-07-01T00:00:00":
                temp_ativa["data_inicio"] = "2026-07-01T00:00:00"
                save_json_data("temporadas", dados, clube_codigo=cod)

        return dados

    def _salvar_dados(self, dados: Dict[str, Any], clube_codigo: Optional[str] = None):
        cod = self._obter_clube_codigo(clube_codigo)

        if self.data_file and self.data_file != DATA_FILE:
            conteudo = {}
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'r', encoding='utf-8') as f:
                        conteudo = json.load(f)
                except Exception:
                    conteudo = {}
            if not isinstance(conteudo, dict):
                conteudo = {}
            if "temporada_ativa" in conteudo or "historico_temporadas" in conteudo:
                conteudo = {"001": conteudo}
            conteudo[cod] = dados
            try:
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(conteudo, f, indent=2)
            except Exception:
                pass
            return

        from services.db import save_json_data
        save_json_data("temporadas", dados, clube_codigo=cod)

    @property
    def dados(self) -> Dict[str, Any]:
        """Acesso retrocompatível aos dados do clube ativo."""
        return self._carregar_dados()

    def obter_temporada_ativa(self, total_partidas_periodo: int = 0, clube_codigo: Optional[str] = None) -> Dict[str, Any]:
        from services.time_utils import obter_agora_local
        cod = self._obter_clube_codigo(clube_codigo)
        dados_clube = self._carregar_dados(cod)
        temp = dados_clube.get("temporada_ativa")
        if not temp or not isinstance(temp, dict) or not temp.get("ativa"):
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
            "data_inicio_input": dt_inicio.strftime("%Y-%m-%d"),
            "data_fim_input": dt_fim.strftime("%Y-%m-%d"),
        })
        return res

    def abrir_nova_competicao(
        self,
        nome: str,
        tipo_duracao: str = "partidas",
        valor_duracao: int = 10,
        descricao_premio: Optional[str] = None,
        clube_codigo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Arquiva a competição atual do clube e abre uma nova competição zerada no fuso horário local da Europa (Europe/Lisbon).
        Partidas de competições anteriores ficam no histórico arquivado do clube.
        """
        from services.time_utils import obter_agora_local
        agora = obter_agora_local()
        cod = self._obter_clube_codigo(clube_codigo)
        dados_clube = self._carregar_dados(cod)

        # Arquivar a temporada ativa anterior se existir
        temp_atual = dados_clube.get("temporada_ativa")
        if temp_atual and isinstance(temp_atual, dict):
            temp_atual["ativa"] = False
            temp_atual["encerrada_em"] = agora.isoformat()
            dados_clube.setdefault("historico_temporadas", []).append(temp_atual)

        # Início da nova competição no começo do dia atual no fuso horário da Europa
        dt_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        if tipo_duracao == "meses":
            dias = max(1, valor_duracao * 30)
            dt_fim = (agora + timedelta(days=dias)).replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
            limite_partidas = None
        else:  # "partidas"
            dt_fim = (agora + timedelta(days=365)).replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
            limite_partidas = max(1, valor_duracao)

        novo_id = len(dados_clube.get("historico_temporadas", [])) + 1

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

        dados_clube["temporada_ativa"] = nova_temporada
        self._salvar_dados(dados_clube, clube_codigo=cod)
        return self.obter_temporada_ativa(clube_codigo=cod)

    def atualizar_temporada(
        self,
        nome: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        descricao_premio: Optional[str] = None,
        clube_codigo: Optional[str] = None
    ) -> Dict[str, Any]:
        cod = self._obter_clube_codigo(clube_codigo)
        dados_clube = self._carregar_dados(cod)
        temp = dados_clube.get("temporada_ativa")
        if not temp or not isinstance(temp, dict):
            temp = {"id": 1, "ativa": True}
            dados_clube["temporada_ativa"] = temp

        if nome:
            temp["nome"] = nome
        if data_inicio:
            if len(data_inicio) == 10 and "-" in data_inicio:
                data_inicio = f"{data_inicio}T00:00:00"
            temp["data_inicio"] = data_inicio
        if data_fim:
            if len(data_fim) == 10 and "-" in data_fim:
                data_fim = f"{data_fim}T23:59:59"
            temp["data_fim"] = data_fim
        if descricao_premio is not None:
            temp["descricao_premio"] = descricao_premio
        temp["ativa"] = True
        self._salvar_dados(dados_clube, clube_codigo=cod)
        return self.obter_temporada_ativa(clube_codigo=cod)

    def excluir_competicao_ativa(self, clube_codigo: Optional[str] = None) -> bool:
        """
        Exclui / zera a competição ativa do clube, permitindo iniciar uma nova competição do zero.
        """
        cod = self._obter_clube_codigo(clube_codigo)
        dados_clube = self._carregar_dados(cod)
        dados_clube["temporada_ativa"] = None
        self._salvar_dados(dados_clube, clube_codigo=cod)
        return True

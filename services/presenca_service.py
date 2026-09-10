import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from services.auth_service import AuthService
from services.jogador_service import JogadorService
from services.db import load_json_data, save_json_data

logger = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "presencas.json")


class PresencaService:
    """
    Gerencia a confirmação de presença pré-jogo dos atletas (Roster RSVP).
    Persiste no banco de dados PostgreSQL (app_json_store) em produção e em data/presencas.json em localhost.
    """

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = data_file or DATA_FILE
        self.auth_service = AuthService()
        self.jogador_service = JogadorService()

    @property
    def dados(self) -> Dict[str, Any]:
        return self._carregar_dados()

    @staticmethod
    def proxima_terca_feira() -> str:
        """Retorna a data formatada da próxima terça-feira (ex: 'Terça-feira, 04/08/2026')."""
        hoje = datetime.now()
        dias_ate_terca = (1 - hoje.weekday()) % 7
        data_terca = hoje + timedelta(days=dias_ate_terca)
        return f"Terça-feira, {data_terca.strftime('%d/%m/%Y')}"

    def _carregar_dados(self) -> Dict[str, Any]:
        padrao = {
            "respostas": {},  # user_id: { status, nome, atualizado_em }
            "status_lista": "fechada",  # "aberta" ou "fechada"
            "titulo": f"Próxima Partida • {self.proxima_terca_feira()}",
            "aberta_em": datetime.now().isoformat()
        }
        dados = load_json_data("presencas", padrao)
        if not isinstance(dados, dict):
            return padrao
        dados.setdefault("respostas", {})
        dados.setdefault("status_lista", "fechada")
        dados.setdefault("titulo", f"Próxima Partida • {self.proxima_terca_feira()}")
        dados.setdefault("aberta_em", datetime.now().isoformat())
        return dados

    def _salvar_dados(self, dados: Optional[Dict[str, Any]] = None):
        if dados is None:
            dados = self.dados
        save_json_data("presencas", dados)

    def registrar_resposta(self, user_id: str, status: str) -> Dict[str, Any]:
        status = (status or "").strip().lower()
        if status not in ["confirmado", "ausente", "duvida"]:
            raise ValueError("Status inválido. Use 'confirmado', 'ausente' ou 'duvida'.")

        usuario = self.auth_service.obter_por_id(user_id)
        if not usuario:
            raise ValueError("Usuário não encontrado.")

        nome = usuario.get("nome") or usuario.get("username") or "Jogador"
        
        dados = self._carregar_dados()
        respostas = dados.setdefault("respostas", {})
        respostas[user_id] = {
            "user_id": user_id,
            "nome": nome,
            "status": status,
            "atualizado_em": datetime.now().isoformat()
        }
        self._salvar_dados(dados)
        return respostas[user_id]

    def obter_resposta(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.dados.get("respostas", {}).get(user_id)

    def abrir_lista(self, titulo: Optional[str] = None) -> Dict[str, Any]:
        """Abre a lista de presença pré-jogo para a próxima terça-feira e zera as respostas anteriores."""
        dados = self._carregar_dados()
        dados["status_lista"] = "aberta"
        dados["titulo"] = titulo or f"Próxima Partida • {self.proxima_terca_feira()}"
        dados["data_jogo"] = self.proxima_terca_feira()
        dados["aberta_em"] = datetime.now().isoformat()
        dados["respostas"] = {}
        self._salvar_dados(dados)

        try:
            from services.email_service import EmailService
            EmailService().notify_presenca_aberta(data_rodada=dados["titulo"])
        except Exception as _exc:
            logger.warning(f"Falha ao disparar e-mail de presença aberta: {_exc}")

        return dados

    def fechar_lista(self) -> Dict[str, Any]:
        """Encerra a lista de presença pré-jogo."""
        dados = self._carregar_dados()
        dados["status_lista"] = "fechada"
        self._salvar_dados(dados)
        return dados

    def is_aberta(self) -> bool:
        """Retorna True se a lista de presença estiver aberta pelo Juiz/Admin."""
        return self.dados.get("status_lista", "aberta") == "aberta"

    def obter_resumo(self) -> Dict[str, Any]:
        dados = self._carregar_dados()
        respostas = dados.get("respostas", {})
        confirmados = [item for item in respostas.values() if item.get("status") == "confirmado"]
        ausentes = [item for item in respostas.values() if item.get("status") == "ausente"]
        duvidas = [item for item in respostas.values() if item.get("status") == "duvida"]

        return {
            "status_lista": dados.get("status_lista", "aberta"),
            "titulo": dados.get("titulo", "Próxima Pelada"),
            "confirmados": confirmados,
            "ausentes": ausentes,
            "duvidas": duvidas,
            "total_confirmados": len(confirmados),
            "total_ausentes": len(ausentes),
            "total_duvidas": len(duvidas),
            "total_respostas": len(respostas),
        }

    def obter_nomes_confirmados(self) -> List[str]:
        """Retorna os nomes dos atletas que confirmaram presença para pré-seleção no painel do Juiz."""
        resumo = self.obter_resumo()
        return [item.get("nome") for item in resumo["confirmados"] if item.get("nome")]

    def limpar_respostas(self):
        """Limpa as respostas de presença para a próxima rodada."""
        dados = self._carregar_dados()
        dados["respostas"] = {}
        self._salvar_dados(dados)

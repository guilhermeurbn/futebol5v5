import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from services.auth_service import AuthService
from services.jogador_service import JogadorService

logger = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "presencas.json")


class PresencaService:
    """
    Gerencia a confirmação de presença pré-jogo dos atletas (Roster RSVP).
    Salva escolhas (confirmado/ausente/duvida) em data/presencas.json.
    """

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = data_file or DATA_FILE
        self.dados = self._carregar_dados()
        self.auth_service = AuthService()
        self.jogador_service = JogadorService()

    @staticmethod
    def proxima_terca_feira() -> str:
        """Retorna a data formatada da próxima terça-feira (ex: 'Terça-feira, 04/08/2026')."""
        hoje = datetime.now()
        dias_ate_terca = (1 - hoje.weekday()) % 7
        data_terca = hoje + timedelta(days=dias_ate_terca)
        return f"Terça-feira, {data_terca.strftime('%d/%m/%Y')}"

    def _carregar_dados(self) -> Dict[str, Any]:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar presencas.json: {str(e)}")
        
        padrao = {
            "respostas": {},  # user_id: { status, nome, atualizado_em }
            "status_lista": "fechada",  # "aberta" ou "fechada"
            "titulo": f"Próxima Partida • {self.proxima_terca_feira()}",
            "aberta_em": datetime.now().isoformat()
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
            logger.error(f"Erro ao salvar presencas.json: {str(e)}")

    def registrar_resposta(self, user_id: str, status: str) -> Dict[str, Any]:
        status = (status or "").strip().lower()
        if status not in ["confirmado", "ausente", "duvida"]:
            raise ValueError("Status inválido. Use 'confirmado', 'ausente' ou 'duvida'.")

        usuario = self.auth_service.obter_por_id(user_id)
        if not usuario:
            raise ValueError("Usuário não encontrado.")

        nome = usuario.get("nome") or usuario.get("username") or "Jogador"
        
        respostas = self.dados.setdefault("respostas", {})
        respostas[user_id] = {
            "user_id": user_id,
            "nome": nome,
            "status": status,
            "atualizado_em": datetime.now().isoformat()
        }
        self._salvar_dados()
        return respostas[user_id]

    def obter_resposta(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.dados.get("respostas", {}).get(user_id)

    def abrir_lista(self, titulo: Optional[str] = None) -> Dict[str, Any]:
        """Abre a lista de presença pré-jogo para a próxima terça-feira e zera as respostas anteriores."""
        self.dados["status_lista"] = "aberta"
        self.dados["titulo"] = titulo or f"Próxima Partida • {self.proxima_terca_feira()}"
        self.dados["data_jogo"] = self.proxima_terca_feira()
        self.dados["aberta_em"] = datetime.now().isoformat()
        self.dados["respostas"] = {}
        self._salvar_dados()
        return self.dados

    def fechar_lista(self) -> Dict[str, Any]:
        """Encerra a lista de presença pré-jogo."""
        self.dados["status_lista"] = "fechada"
        self._salvar_dados()
        return self.dados

    def is_aberta(self) -> bool:
        """Retorna True se a lista de presença estiver aberta pelo Juiz/Admin."""
        return self.dados.get("status_lista", "aberta") == "aberta"

    def obter_resumo(self) -> Dict[str, Any]:
        respostas = self.dados.get("respostas", {})
        confirmados = [item for item in respostas.values() if item.get("status") == "confirmado"]
        ausentes = [item for item in respostas.values() if item.get("status") == "ausente"]
        duvidas = [item for item in respostas.values() if item.get("status") == "duvida"]

        return {
            "status_lista": self.dados.get("status_lista", "aberta"),
            "titulo": self.dados.get("titulo", "Próxima Pelada"),
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
        self.dados["respostas"] = {}
        self._salvar_dados()

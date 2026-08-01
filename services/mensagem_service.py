"""
Serviço de mensagens diretas entre jogadores estilo Chat/WhatsApp.
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple


class MensagemService:
    def __init__(self, arquivo: str = "data/mensagens.json"):
        self.arquivo = arquivo
        self._garantir_arquivo()

    def _garantir_arquivo(self) -> None:
        if os.getenv("DATABASE_URL"):
            return
        if not os.path.exists(self.arquivo):
            self._salvar({"ultimo_id": 0, "mensagens": []})

    def _carregar(self) -> Dict:
        if os.getenv("DATABASE_URL"):
            dados = load_json_data("mensagens", {"ultimo_id": 0, "mensagens": []})
            if not isinstance(dados, dict):
                return {"ultimo_id": 0, "mensagens": []}
            dados.setdefault("ultimo_id", 0)
            dados.setdefault("mensagens", [])
            return dados
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if not isinstance(dados, dict):
                return {"ultimo_id": 0, "mensagens": []}
            dados.setdefault("ultimo_id", 0)
            dados.setdefault("mensagens", [])
            return dados
        except (FileNotFoundError, json.JSONDecodeError):
            return {"ultimo_id": 0, "mensagens": []}

    def _salvar(self, dados: Dict) -> None:
        if os.getenv("DATABASE_URL"):
            save_json_data("mensagens", dados)
            return
        os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    def enviar_mensagem(
        self,
        remetente_id: str,
        remetente_nome: str,
        destinatario_id: str,
        destinatario_nome: str,
        conteudo: str
    ) -> Dict:
        dados = self._carregar()
        novo_id = int(dados.get("ultimo_id", 0)) + 1
        msg = {
            "id": novo_id,
            "remetente_id": str(remetente_id),
            "remetente_nome": (remetente_nome or "Jogador").strip(),
            "destinatario_id": str(destinatario_id),
            "destinatario_nome": (destinatario_nome or "Jogador").strip(),
            "conteudo": (conteudo or "").strip(),
            "criado_em": datetime.now().isoformat(),
            "lida": False,
        }
        dados["ultimo_id"] = novo_id
        dados.setdefault("mensagens", []).append(msg)
        self._salvar(dados)
        return msg

    def obter_conversa_cronologica(self, user1_id: str, user2_id: str, limite: int = 100) -> List[Dict]:
        """Retorna histórico completo da conversa ordenado do mais antigo para o mais recente."""
        dados = self._carregar()
        u1, u2 = str(user1_id), str(user2_id)
        msgs = [
            m for m in dados.get("mensagens", [])
            if (str(m.get("remetente_id")) == u1 and str(m.get("destinatario_id")) == u2) or
               (str(m.get("remetente_id")) == u2 and str(m.get("destinatario_id")) == u1)
        ]
        msgs.sort(key=lambda x: x.get("criado_em", ""))
        return msgs[-limite:]

    def listar_mensagens_entre_usuarios(self, user1_id: str, user2_id: str, limite: int = 100) -> List[Dict]:
        return self.obter_conversa_cronologica(user1_id, user2_id, limite)

    def listar_mensagens_recebidas(self, user_id: str, limite: int = 100) -> List[Dict]:
        dados = self._carregar()
        uid = str(user_id)
        msgs = [
            m for m in dados.get("mensagens", [])
            if str(m.get("destinatario_id")) == uid or str(m.get("remetente_id")) == uid
        ]
        msgs.sort(key=lambda x: x.get("criado_em", ""), reverse=True)
        return msgs[:limite]

    def obter_mensagens_separadas(self, user_id: str) -> Tuple[List[Dict], List[Dict]]:
        """Retorna (mensagens_nao_lidas, mensagens_lidas)."""
        dados = self._carregar()
        uid = str(user_id)
        nao_lidas = []
        lidas = []
        for m in reversed(dados.get("mensagens", [])):
            if str(m.get("destinatario_id")) == uid:
                if not m.get("lida", False):
                    nao_lidas.append(m)
                else:
                    lidas.append(m)
            elif str(m.get("remetente_id")) == uid:
                lidas.append(m)
        return nao_lidas, lidas

    def tem_mensagens_nao_lidas(self, user_id: str) -> bool:
        """Verifica se existe qualquer mensagem não lida destinada a este usuário."""
        dados = self._carregar()
        uid = str(user_id)
        return any(
            not m.get("lida", False) and str(m.get("destinatario_id")) == uid
            for m in dados.get("mensagens", [])
        )

    def marcar_mensagem_individual_como_lida(self, msg_id: int, user_id: str) -> bool:
        """Marca uma mensagem específica como lida pelo destinatário."""
        dados = self._carregar()
        uid = str(user_id)
        for m in dados.get("mensagens", []):
            if int(m.get("id", 0)) == int(msg_id) and str(m.get("destinatario_id")) == uid:
                m["lida"] = True
                self._salvar(dados)
                return True
        return False

    def marcar_como_lidas(self, destinatario_id: str, remetente_id: str = None) -> int:
        """Marca mensagens não lidas como lidas."""
        dados = self._carregar()
        dest_uid = str(destinatario_id)
        rem_uid = str(remetente_id) if remetente_id else None
        alterados = 0

        for m in dados.get("mensagens", []):
            if str(m.get("destinatario_id")) == dest_uid and not m.get("lida", False):
                if rem_uid is None or str(m.get("remetente_id")) == rem_uid:
                    m["lida"] = True
                    alterados += 1

        if alterados > 0:
            self._salvar(dados)
        return alterados

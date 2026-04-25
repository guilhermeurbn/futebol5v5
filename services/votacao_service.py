"""
Servico de votacao por partida.
Usuarios se autoclassificam; admin apura ranking ao encerrar.
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional


class VotacaoService:
    """Gerencia ciclo de votacao por partida."""

    def __init__(self, arquivo: str = "votacoes_partidas.json"):
        self.arquivo = arquivo
        self._garantir_arquivo()

    def _garantir_arquivo(self) -> None:
        if not os.path.exists(self.arquivo):
            self._salvar({"ultimo_id": 0, "partidas": []})

    def _carregar(self) -> Dict:
        try:
            with open(self.arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if not isinstance(dados, dict):
                return {"ultimo_id": 0, "partidas": []}
            dados.setdefault("ultimo_id", 0)
            dados.setdefault("partidas", [])
            return dados
        except (FileNotFoundError, json.JSONDecodeError):
            return {"ultimo_id": 0, "partidas": []}

    def _salvar(self, dados: Dict) -> None:
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    def _find_partida(self, partida_id: int) -> Optional[Dict]:
        dados = self._carregar()
        for p in dados.get("partidas", []):
            if p.get("id") == partida_id:
                return p
        return None

    def listar(self) -> List[Dict]:
        dados = self._carregar()
        return list(reversed(dados.get("partidas", [])))

    def obter_ativa(self) -> Optional[Dict]:
        dados = self._carregar()
        partidas = dados.get("partidas", [])
        for p in reversed(partidas):
            if p.get("status") == "aberta":
                return p
        return None

    def obter_ativa_para_usuario(self, user_id: str) -> Optional[Dict]:
        if not user_id:
            return None
        partida = self.obter_ativa()
        if not partida:
            return None
        for part in partida.get("participantes", []):
            if part.get("user_id") == user_id:
                return partida
        return None

    def criar_partida(
        self,
        times_json: List[Dict],
        usuarios: List[Dict],
        criado_por: str,
        titulo: str = ""
    ) -> Dict:
        dados = self._carregar()

        for p in dados.get("partidas", []):
            if p.get("status") == "aberta":
                raise ValueError("Ja existe uma partida aberta")

        ultimo_id = int(dados.get("ultimo_id", 0)) + 1
        participantes = []
        user_map = {u.get("id"): u for u in usuarios if u.get("id")}

        for time in times_json:
            numero = time.get("numero")
            for j in time.get("jogadores", []):
                user_id = j.get("owner_user_id")
                usuario = user_map.get(user_id) if user_id else None
                participantes.append({
                    "user_id": user_id,
                    "username": (usuario or {}).get("username", ""),
                    "nome_usuario": (usuario or {}).get("nome", ""),
                    "jogador_nome": j.get("nome", ""),
                    "time_numero": numero,
                    "externo": usuario is None
                })

        if not participantes:
            raise ValueError("Nenhum participante encontrado no sorteio")

        partida = {
            "id": ultimo_id,
            "titulo": (titulo or f"Partida {ultimo_id}").strip(),
            "status": "aberta",
            "criado_em": datetime.now().isoformat(),
            "criado_por": criado_por,
            "encerrado_em": None,
            "encerrado_por": None,
            "times": times_json,
            "participantes": participantes,
            "votos": [],
            "ranking": None
        }

        dados["ultimo_id"] = ultimo_id
        dados.setdefault("partidas", []).append(partida)
        self._salvar(dados)
        return partida

    def _normalizar_nota(self, valor: float) -> float:
        nota = max(0.0, min(10.0, float(valor)))
        return round(nota * 2) / 2

    def _participantes_permitidos(self, partida: Dict) -> Dict[str, Dict]:
        """Mapa de participantes válidos por nome para validar os votos."""
        permitidos = {}
        for participante in partida.get("participantes", []):
            nome = (participante.get("jogador_nome") or "").strip()
            if nome:
                permitidos[nome] = participante
        return permitidos

    def salvar_voto(
        self,
        partida_id: int,
        user_id: str,
        votos_obrigatorios: List[Dict],
        votos_extras: Optional[List[Dict]] = None
    ) -> Dict:
        dados = self._carregar()
        alvo = None
        for p in dados.get("partidas", []):
            if p.get("id") == partida_id:
                alvo = p
                break

        if not alvo:
            raise ValueError("Partida nao encontrada")
        if alvo.get("status") != "aberta":
            raise ValueError("Partida ja encerrada")

        obrigatorios = votos_obrigatorios or []
        extras = votos_extras or []
        permitidos = self._participantes_permitidos(alvo)

        if len(obrigatorios) < 3 or len(obrigatorios) > 5:
            raise ValueError("Voce deve votar obrigatoriamente entre 3 e 5 jogadores")

        nomes = set()
        todos = []
        for item in obrigatorios:
            nome = (item.get("jogador_nome") or "").strip()
            if not nome:
                continue
            if nome not in permitidos:
                raise ValueError(f"Jogador invalido na votacao: {nome}")
            if nome in nomes:
                raise ValueError("Jogador repetido na votacao")
            nomes.add(nome)
            todos.append({
                "jogador_nome": nome,
                "time_numero": permitidos[nome].get("time_numero"),
                "nota": self._normalizar_nota(item.get("nota", 0)),
                "obrigatorio": True
            })

        for item in extras:
            nome = (item.get("jogador_nome") or "").strip()
            if not nome or nome in nomes:
                continue
            if nome not in permitidos:
                raise ValueError(f"Jogador invalido na votacao: {nome}")
            nomes.add(nome)
            todos.append({
                "jogador_nome": nome,
                "time_numero": permitidos[nome].get("time_numero"),
                "nota": self._normalizar_nota(item.get("nota", 0)),
                "obrigatorio": False
            })

        if len([v for v in todos if v.get("obrigatorio")]) < 3:
            raise ValueError("Voce deve votar obrigatoriamente em pelo menos 3 jogadores")

        voto = {
            "user_id": user_id,
            "votos": todos,
            "atualizado_em": datetime.now().isoformat()
        }

        votos = alvo.get("votos", [])
        atualizado = False
        for idx, existente in enumerate(votos):
            if existente.get("user_id") == user_id:
                votos[idx] = voto
                atualizado = True
                break

        if not atualizado:
            votos.append(voto)

        alvo["votos"] = votos
        self._salvar(dados)
        return voto

    def obter_voto_usuario(self, partida_id: int, user_id: str) -> Optional[Dict]:
        partida = self._find_partida(partida_id)
        if not partida:
            return None
        for voto in partida.get("votos", []):
            if voto.get("user_id") == user_id:
                return voto
        return None

    def encerrar_e_apurar(self, partida_id: int, encerrado_por: str) -> Dict:
        dados = self._carregar()
        alvo = None
        for p in dados.get("partidas", []):
            if p.get("id") == partida_id:
                alvo = p
                break

        if not alvo:
            raise ValueError("Partida nao encontrada")
        if alvo.get("status") != "aberta":
            return alvo

        ranking = self._apurar_ranking(alvo)
        alvo["ranking"] = ranking
        alvo["status"] = "encerrada"
        alvo["encerrado_em"] = datetime.now().isoformat()
        alvo["encerrado_por"] = encerrado_por
        self._salvar(dados)
        return alvo

    def _apurar_ranking(self, partida: Dict) -> Dict:
        votos = partida.get("votos", [])
        jogadores = {}
        times = {}

        for voto in votos:
            for voto_jogador in voto.get("votos", []):
                nome = voto_jogador.get("jogador_nome", "Jogador")
                time = voto_jogador.get("time_numero")
                nota = self._normalizar_nota(voto_jogador.get("nota", 0))

                stats = jogadores.setdefault(nome, {
                    "jogador_nome": nome,
                    "time_numero": time,
                    "nota_total": 0.0,
                    "votos": 0,
                    "pontos": 0.0
                })

                stats["nota_total"] += nota
                stats["votos"] += 1
                stats["pontos"] += nota

                t = times.setdefault(time, {
                    "time_numero": time,
                    "nota_total": 0.0,
                    "votos": 0
                })
                t["nota_total"] += nota
                t["votos"] += 1

        ranking_jogadores = sorted(jogadores.values(), key=lambda x: (x["pontos"], x["votos"]), reverse=True)
        ranking_times = sorted(times.values(), key=lambda x: (x["nota_total"], x["votos"]), reverse=True)

        melhor_jogador = ranking_jogadores[0] if ranking_jogadores else None
        melhor_time = ranking_times[0] if ranking_times else None

        for item in ranking_jogadores:
            item["nota_media"] = round(item["nota_total"] / item["votos"], 2) if item["votos"] else 0

        for item in ranking_times:
            item["nota_media"] = round(item["nota_total"] / item["votos"], 2) if item["votos"] else 0

        return {
            "total_votos": len(votos),
            "ranking_times": ranking_times,
            "ranking_jogadores": ranking_jogadores,
            "melhor_jogador": melhor_jogador,
            "melhor_time": melhor_time
        }

    def ranking_jogadores_geral(self, limite: int = 50) -> Dict:
        """Retorna classificação geral de jogadores usando partidas encerradas."""
        partidas = self.listar()
        encerradas = [p for p in partidas if p.get("status") == "encerrada"]

        acumulado = {}
        total_votos = 0

        for partida in encerradas:
            votos = partida.get("votos", [])
            total_votos += len(votos)
            for voto in votos:
                for voto_jogador in voto.get("votos", []):
                    nome = voto_jogador.get("jogador_nome", "Jogador")
                    nota = self._normalizar_nota(voto_jogador.get("nota", 0))
                    item = acumulado.setdefault(nome, {
                        "jogador_nome": nome,
                        "jogos": 0,
                        "nota_total": 0.0,
                        "pontos": 0.0
                    })
                    item["jogos"] += 1
                    item["nota_total"] += nota
                    item["pontos"] += nota

        ranking = sorted(acumulado.values(), key=lambda x: (x["pontos"], x["jogos"]), reverse=True)
        ranking = ranking[:max(1, int(limite))]

        for item in ranking:
            jogos = item.get("jogos", 0)
            item["nota_media"] = round(item["nota_total"] / jogos, 2) if jogos else 0

        return {
            "ranking": ranking,
            "total_partidas": len(encerradas),
            "total_votos": total_votos,
            "total_jogadores": len(acumulado)
        }

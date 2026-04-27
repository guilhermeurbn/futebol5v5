"""
Servico de votacao por rodada.
Liga sorteio, resultado da partida e apuracao dos votos.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from services.db import load_json_data, save_json_data


class VotacaoService:
    """Gerencia o ciclo de votacao e apuracao de uma rodada."""

    def __init__(self, arquivo: str = "votacoes_partidas.json"):
        self.arquivo = arquivo
        self._garantir_arquivo()

    def _garantir_arquivo(self) -> None:
        if os.getenv("DATABASE_URL"):
            return
        if not os.path.exists(self.arquivo):
            self._salvar({"ultimo_id": 0, "partidas": []})

    def _carregar(self) -> Dict:
        if os.getenv("DATABASE_URL"):
            dados = load_json_data("votacoes_partidas", {"ultimo_id": 0, "partidas": []})
            if not isinstance(dados, dict):
                return {"ultimo_id": 0, "partidas": []}
            dados.setdefault("ultimo_id", 0)
            dados.setdefault("partidas", [])
            return dados
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
        if os.getenv("DATABASE_URL"):
            save_json_data("votacoes_partidas", dados)
            return
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    def _agora(self) -> datetime:
        return datetime.now()

    def _parse_iso(self, valor: Optional[str]) -> Optional[datetime]:
        if not valor:
            return None
        try:
            return datetime.fromisoformat(valor)
        except (TypeError, ValueError):
            return None

    def _status_votacao(self, partida: Dict) -> str:
        if partida.get("status") != "aberta":
            return partida.get("status", "encerrada")

        fecha_em = self._parse_iso(partida.get("fecha_em"))
        if fecha_em and fecha_em <= self._agora():
            return "expirada"
        return "aberta"

    def _resultado_por_time(self, resultado_partida: Dict, time_numero: int) -> str:
        for item in resultado_partida.get("times_desempenho", []) or []:
            if int(item.get("time_numero", 0) or 0) != int(time_numero):
                continue
            if int(item.get("vitorias", 0) or 0) > 0:
                return "vitoria"
            if int(item.get("derrotas", 0) or 0) > 0:
                return "derrota"
            return "empate"

        time_vencedor = resultado_partida.get("time_vencedor")
        if not time_vencedor:
            return "empate"
        if int(time_vencedor) == int(time_numero):
            return "vitoria"
        return "derrota"

    def _resumo_times_resultado(self, resultado_partida: Optional[Dict]) -> List[Dict]:
        if not resultado_partida:
            return []

        gols_times = resultado_partida.get("gols_times", []) or []
        desempenho = resultado_partida.get("times_desempenho", []) or []
        resumo = []

        for idx, gols in enumerate(gols_times, start=1):
            item_desempenho = next(
                (t for t in desempenho if int(t.get("time_numero", 0) or 0) == idx),
                {}
            )
            resumo.append({
                "time_numero": idx,
                "gols": int(gols or 0),
                "vitorias": int(item_desempenho.get("vitorias", 0) or 0),
                "empates": int(item_desempenho.get("empates", 0) or 0),
                "derrotas": int(item_desempenho.get("derrotas", 0) or 0),
                "resultado": self._resultado_por_time(resultado_partida, idx),
            })

        return resumo

    def _find_partida_em_dados(self, dados: Dict, partida_id: int) -> Optional[Dict]:
        for p in dados.get("partidas", []):
            if p.get("id") == partida_id:
                return p
        return None

    def _find_partida(self, partida_id: int) -> Optional[Dict]:
        dados = self._carregar()
        self._encerrar_expiradas_em_dados(dados)
        return self._find_partida_em_dados(dados, partida_id)

    def _encerrar_partida_obj(self, partida: Dict, encerrado_por: str, motivo: str = "manual") -> Dict:
        if partida.get("status") != "aberta":
            return partida

        ranking = self._apurar_ranking(partida)
        partida["ranking"] = ranking
        partida["status"] = "encerrada"
        partida["encerrado_em"] = self._agora().isoformat()
        partida["encerrado_por"] = encerrado_por
        partida["encerramento_motivo"] = motivo
        partida["resultado_resumido"] = self._resumo_times_resultado(partida.get("resultado_partida"))
        return partida

    def _encerrar_expiradas_em_dados(self, dados: Dict) -> bool:
        alterou = False
        agora = self._agora()
        for partida in dados.get("partidas", []):
            if partida.get("status") != "aberta":
                continue
            fecha_em = self._parse_iso(partida.get("fecha_em"))
            if fecha_em and fecha_em <= agora:
                self._encerrar_partida_obj(partida, "sistema", motivo="automatico")
                alterou = True
        if alterou:
            self._salvar(dados)
        return alterou

    def listar(self) -> List[Dict]:
        dados = self._carregar()
        self._encerrar_expiradas_em_dados(dados)
        return list(reversed(dados.get("partidas", [])))

    def obter_ativa(self) -> Optional[Dict]:
        dados = self._carregar()
        self._encerrar_expiradas_em_dados(dados)
        partidas = dados.get("partidas", [])
        for p in reversed(partidas):
            if p.get("status") == "aberta":
                return p
        return None

    def obter_por_sorteio(self, sorteio_id: int) -> Optional[Dict]:
        if not sorteio_id:
            return None
        dados = self._carregar()
        self._encerrar_expiradas_em_dados(dados)
        correspondentes = [p for p in dados.get("partidas", []) if int(p.get("sorteio_id", 0) or 0) == int(sorteio_id)]
        if not correspondentes:
            return None
        correspondentes.sort(key=lambda p: p.get("id", 0), reverse=True)
        return correspondentes[0]

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

    def obter_pendencia_usuario(self, user_id: str) -> Optional[Dict]:
        partida = self.obter_ativa_para_usuario(user_id)
        if not partida:
            return None
        if self.obter_voto_usuario(partida.get("id"), user_id):
            return None
        return partida

    def criar_partida(
        self,
        times_json: List[Dict],
        usuarios: List[Dict],
        criado_por: str,
        titulo: str = "",
        sorteio_id: Optional[int] = None,
        resultado_partida: Optional[Dict] = None,
        duracao_horas: int = 8,
    ) -> Dict:
        dados = self._carregar()
        self._encerrar_expiradas_em_dados(dados)

        for p in dados.get("partidas", []):
            if p.get("status") == "aberta":
                raise ValueError("Ja existe uma partida aberta")

        if sorteio_id:
            ja_existente = next(
                (p for p in dados.get("partidas", []) if int(p.get("sorteio_id", 0) or 0) == int(sorteio_id)),
                None
            )
            if ja_existente:
                raise ValueError("Ja existe uma rodada de votacao para este sorteio")

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
                    "externo": usuario is None,
                })

        if not participantes:
            raise ValueError("Nenhum participante encontrado no sorteio")

        aberta_em = self._agora()
        fecha_em = aberta_em + timedelta(hours=max(1, int(duracao_horas or 8)))

        partida = {
            "id": ultimo_id,
            "sorteio_id": sorteio_id,
            "titulo": (titulo or f"Rodada {ultimo_id}").strip(),
            "status": "aberta",
            "criado_em": aberta_em.isoformat(),
            "aberta_em": aberta_em.isoformat(),
            "fecha_em": fecha_em.isoformat(),
            "duracao_horas": max(1, int(duracao_horas or 8)),
            "criado_por": criado_por,
            "encerrado_em": None,
            "encerrado_por": None,
            "encerramento_motivo": None,
            "times": times_json,
            "participantes": participantes,
            "votos": [],
            "ranking": None,
            "resultado_partida": resultado_partida or None,
            "resultado_resumido": self._resumo_times_resultado(resultado_partida),
        }

        dados["ultimo_id"] = ultimo_id
        dados.setdefault("partidas", []).append(partida)
        self._salvar(dados)
        return partida

    def atualizar_resultado_da_rodada(self, sorteio_id: int, resultado_partida: Dict) -> Optional[Dict]:
        if not sorteio_id:
            return None

        dados = self._carregar()
        self._encerrar_expiradas_em_dados(dados)
        alvo = next(
            (p for p in dados.get("partidas", []) if int(p.get("sorteio_id", 0) or 0) == int(sorteio_id)),
            None
        )
        if not alvo:
            return None

        alvo["resultado_partida"] = resultado_partida
        alvo["resultado_resumido"] = self._resumo_times_resultado(resultado_partida)
        self._salvar(dados)
        return alvo

    def _normalizar_nota(self, valor: float) -> float:
        nota = max(0.0, min(10.0, float(valor)))
        return round(nota * 2) / 2

    def _participantes_permitidos(self, partida: Dict) -> Dict[str, Dict]:
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
        votos_extras: Optional[List[Dict]] = None,
    ) -> Dict:
        dados = self._carregar()
        self._encerrar_expiradas_em_dados(dados)
        alvo = self._find_partida_em_dados(dados, partida_id)

        if not alvo:
            raise ValueError("Partida nao encontrada")
        if alvo.get("status") != "aberta":
            raise ValueError("Partida ja encerrada")
        if not user_id:
            raise ValueError("Usuario invalido para votar")

        participante_user_ids = {
            p.get("user_id")
            for p in alvo.get("participantes", [])
            if p.get("user_id")
        }
        if user_id not in participante_user_ids:
            raise ValueError("Apenas participantes da partida podem votar")

        obrigatorios = votos_obrigatorios or []
        extras = votos_extras or []
        permitidos = self._participantes_permitidos(alvo)

        if len(obrigatorios) < 5 or len(obrigatorios) > 5:
            raise ValueError("Voce deve votar em exatamente 5 jogadores obrigatorios")

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
                "obrigatorio": True,
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
                "obrigatorio": False,
            })

        if len([v for v in todos if v.get("obrigatorio")]) < 5:
            raise ValueError("Voce deve votar em pelo menos 5 jogadores")

        voto_existente = self.obter_voto_usuario(partida_id, user_id)
        if voto_existente:
            raise ValueError("Voce ja votou nesta partida")

        voto = {
            "user_id": user_id,
            "votos": todos,
            "atualizado_em": self._agora().isoformat(),
        }

        votos = alvo.get("votos", [])
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

    def obter_partida(self, partida_id: int) -> Optional[Dict]:
        return self._find_partida(partida_id)

    def encerrar_e_apurar(self, partida_id: int, encerrado_por: str) -> Dict:
        dados = self._carregar()
        self._encerrar_expiradas_em_dados(dados)
        alvo = self._find_partida_em_dados(dados, partida_id)

        if not alvo:
            raise ValueError("Partida nao encontrada")
        if alvo.get("status") != "aberta":
            return alvo

        self._encerrar_partida_obj(alvo, encerrado_por, motivo="manual")
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
                    "pontos": 0.0,
                })

                stats["nota_total"] += nota
                stats["votos"] += 1
                stats["pontos"] += nota

                t = times.setdefault(time, {
                    "time_numero": time,
                    "nota_total": 0.0,
                    "votos": 0,
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

        pendentes = []
        votos_ids = {v.get("user_id") for v in votos if v.get("user_id")}
        for participante in partida.get("participantes", []):
            user_id = participante.get("user_id")
            if user_id and user_id not in votos_ids:
                pendentes.append(participante)

        return {
            "total_votos": len(votos),
            "ranking_times": ranking_times,
            "ranking_jogadores": ranking_jogadores,
            "melhor_jogador": melhor_jogador,
            "melhor_time": melhor_time,
            "participantes_pendentes": pendentes,
        }

    def ranking_jogadores_geral(self, limite: int = 50) -> Dict:
        """Retorna classificacao geral de jogadores usando rodadas encerradas."""
        partidas = self.listar()
        encerradas = [p for p in partidas if p.get("status") == "encerrada"]

        acumulado = {}
        total_votos = 0

        for partida in encerradas:
            votos = partida.get("votos", [])
            total_votos += len(votos)

            participantes = {p.get("jogador_nome"): p for p in partida.get("participantes", []) if p.get("jogador_nome")}
            resultado = partida.get("resultado_partida") or {}
            detalhes_resultado = {
                item.get("nome"): item
                for item in resultado.get("jogadores_detalhes", []) or []
                if item.get("nome")
            }
            melhor_jogador = ((partida.get("ranking") or {}).get("melhor_jogador") or {}).get("jogador_nome")

            for nome, participante in participantes.items():
                item = acumulado.setdefault(nome, {
                    "jogador_nome": nome,
                    "jogos": 0,
                    "nota_total": 0.0,
                    "pontos": 0.0,
                    "avaliacoes": 0,
                    "gols": 0,
                    "assistencias": 0,
                    "vitorias": 0,
                    "destaques": 0,
                })
                item["jogos"] += 1

                detalhe = detalhes_resultado.get(nome, {})
                item["gols"] += int(detalhe.get("gols", 0) or 0)
                item["assistencias"] += int(detalhe.get("assistencias", 0) or 0)

                time_numero = participante.get("time_numero")
                if resultado and self._resultado_por_time(resultado, time_numero) == "vitoria":
                    item["vitorias"] += 1

                if melhor_jogador and melhor_jogador == nome:
                    item["destaques"] += 1

            for voto in votos:
                for voto_jogador in voto.get("votos", []):
                    nome = voto_jogador.get("jogador_nome", "Jogador")
                    nota = self._normalizar_nota(voto_jogador.get("nota", 0))
                    item = acumulado.setdefault(nome, {
                        "jogador_nome": nome,
                        "jogos": 0,
                        "nota_total": 0.0,
                        "pontos": 0.0,
                        "avaliacoes": 0,
                        "gols": 0,
                        "assistencias": 0,
                        "vitorias": 0,
                        "destaques": 0,
                    })
                    item["avaliacoes"] += 1
                    item["nota_total"] += nota
                    item["pontos"] += nota

        ranking = sorted(
            acumulado.values(),
            key=lambda x: (x["pontos"], x["destaques"], x["vitorias"]),
            reverse=True
        )
        ranking = ranking[:max(1, int(limite))]

        for item in ranking:
            avaliacoes = item.get("avaliacoes", 0)
            item["nota_media"] = round(item["nota_total"] / avaliacoes, 2) if avaliacoes else 0

        return {
            "ranking": ranking,
            "total_partidas": len(encerradas),
            "total_votos": total_votos,
            "total_jogadores": len(acumulado),
        }

    def encerrar_expiradas(self) -> None:
        dados = self._carregar()
        self._encerrar_expiradas_em_dados(dados)

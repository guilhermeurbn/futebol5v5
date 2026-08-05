"""
Servico de votacao por rodada.
Liga sorteio, resultado da partida e apuracao dos votos.
"""
import json
import os
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from services.jogador_service import JogadorService
from services.db import load_json_data, save_json_data
from services.voto_confiabilidade_service import VotoConfiabilidadeService


class VotacaoService:
    """Gerencia o ciclo de votacao e apuracao de uma rodada."""

    def __init__(self, arquivo: str = "data/votacoes_partidas.json"):
        self.arquivo = arquivo
        self.confiabilidade_service = VotoConfiabilidadeService()
        self.jogador_service = JogadorService()
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

        # ── Evolução de nível pós-votação ────────────────────────────────
        try:
            from services.nivel_evolution_service import aplicar_evolucao_pos_votacao
            from services.jogador_service import JogadorService
            _jogador_svc = JogadorService()
            evolucao = aplicar_evolucao_pos_votacao(
                ranking_jogadores=ranking.get("ranking_jogadores", []),
                jogador_service=_jogador_svc,
                sorteio_id=partida.get("sorteio_id"),
            )
            partida["evolucao_nivel"] = evolucao
        except Exception as _exc:
            import logging
            logging.getLogger(__name__).warning(
                "Evolução de nível ignorada: %s", _exc, exc_info=True
            )

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

    def _participantes_aptos(self, partida: Dict) -> set:
        return {
            participante.get("user_id")
            for participante in partida.get("participantes", [])
            if participante.get("user_id")
        }

    def _todos_participantes_votaram(self, partida: Dict) -> bool:
        aptos = self._participantes_aptos(partida)
        if not aptos:
            return False
        votantes = {
            voto.get("user_id")
            for voto in partida.get("votos", [])
            if voto.get("user_id")
        }
        return aptos.issubset(votantes)

    def _chave_identidade(self, valor: Optional[str]) -> str:
        texto = unicodedata.normalize("NFKD", (valor or "").strip().lower())
        return "".join(char for char in texto if not unicodedata.combining(char))

    def _usuarios_por_identidade(self, usuarios: List[Dict]) -> Dict[str, Optional[Dict]]:
        candidatos = {}
        for usuario in usuarios:
            if usuario.get("role", "usuario") != "usuario" or not usuario.get("ativo", True):
                continue
            for valor in (usuario.get("nome"), usuario.get("username")):
                chave = self._chave_identidade(valor)
                if not chave:
                    continue
                if chave in candidatos and candidatos[chave] != usuario:
                    candidatos[chave] = None
                else:
                    candidatos[chave] = usuario
        return candidatos

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
        duracao_horas: int = 12,
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
        usuarios_por_identidade = self._usuarios_por_identidade(usuarios)

        for time in times_json:
            numero = time.get("numero")
            for j in time.get("jogadores", []):
                user_id = j.get("owner_user_id")
                usuario = user_map.get(user_id) if user_id else None
                if not usuario:
                    usuario = usuarios_por_identidade.get(
                        self._chave_identidade(j.get("nome"))
                    )
                    user_id = usuario.get("id") if usuario else None
                participantes.append({
                    "user_id": user_id if usuario else None,
                    "username": (usuario or {}).get("username", ""),
                    "nome_usuario": (usuario or {}).get("nome", ""),
                    "jogador_nome": j.get("nome", ""),
                    "time_numero": numero,
                    "externo": usuario is None,
                })

        if not participantes:
            raise ValueError("Nenhum participante encontrado no sorteio")

        aberta_em = self._agora()
        duracao_horas = max(1, int(duracao_horas or 12))
        fecha_em = aberta_em + timedelta(hours=duracao_horas)

        partida = {
            "id": ultimo_id,
            "sorteio_id": sorteio_id,
            "titulo": (titulo or f"Rodada {ultimo_id}").strip(),
            "status": "aberta",
            "criado_em": aberta_em.isoformat(),
            "aberta_em": aberta_em.isoformat(),
            "fecha_em": fecha_em.isoformat(),
            "duracao_horas": duracao_horas,
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
        nota = float(valor)
        if nota <= 0.0:
            return 0.0
        nota = max(0.5, min(10.0, nota))
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
        if self._todos_participantes_votaram(alvo):
            self._encerrar_partida_obj(alvo, "sistema", motivo="todos_votaram")
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

        # Avaliar confiabilidade dos votos
        avaliacao_confiabilidade = self.confiabilidade_service.avaliar_pesos_partida(votos, partida.get("participantes"))
        mapa_pesos = avaliacao_confiabilidade.get("mapa_pesos", {})

        for voto in votos:
            eval_id = str(voto.get("user_id") or voto.get("username") or "anonimo")
            for voto_jogador in voto.get("votos", []):
                nome = voto_jogador.get("jogador_nome", "Jogador")
                time = voto_jogador.get("time_numero")
                nota = self._normalizar_nota(voto_jogador.get("nota", 0))

                peso = float(mapa_pesos.get(eval_id, {}).get(nome, 1.0))
                nota_ponderada = nota * peso

                stats = jogadores.setdefault(nome, {
                    "jogador_nome": nome,
                    "time_numero": time,
                    "nota_total": 0.0,
                    "soma_pesos": 0.0,
                    "votos": 0,
                    "pontos": 0.0,
                    "notas_lista": [],
                })

                stats["nota_total"] += nota_ponderada
                stats["soma_pesos"] += peso
                stats["votos"] += 1
                stats["pontos"] += nota_ponderada
                stats["notas_lista"].append(nota)

                t = times.setdefault(time, {
                    "time_numero": time,
                    "nota_total": 0.0,
                    "soma_pesos": 0.0,
                    "votos": 0,
                })
                t["nota_total"] += nota_ponderada
                t["soma_pesos"] += peso
                t["votos"] += 1

        for participante in partida.get("participantes", []):
            nome = participante.get("nome") or participante.get("jogador_nome")
            time = participante.get("time_numero")
            if nome and nome not in jogadores:
                jogadores[nome] = {
                    "jogador_nome": nome,
                    "time_numero": time,
                    "nota_total": 0.0,
                    "soma_pesos": 0.0,
                    "votos": 0,
                    "pontos": 0.0,
                    "notas_lista": [],
                }

        for item in jogadores.values():
            if item.get("soma_pesos") and item["soma_pesos"] > 0:
                item["nota_media"] = round(item["nota_total"] / item["soma_pesos"], 2)
                item["confiabilidade_media"] = round(item["soma_pesos"] / item["votos"], 4)
            else:
                item["nota_media"] = round(item["nota_total"] / item["votos"], 2) if item["votos"] else 0
                item["confiabilidade_media"] = 1.0

        for item in times.values():
            if item.get("soma_pesos") and item["soma_pesos"] > 0:
                item["nota_media"] = round(item["nota_total"] / item["soma_pesos"], 2)
            else:
                item["nota_media"] = round(item["nota_total"] / item["votos"], 2) if item["votos"] else 0

        ranking_jogadores = sorted(
            jogadores.values(),
            key=lambda x: (x.get("nota_media", 0), x.get("pontos", 0), x.get("votos", 0)),
            reverse=True
        )
        ranking_times = sorted(
            times.values(),
            key=lambda x: (x.get("nota_media", 0), x.get("nota_total", 0), x.get("votos", 0)),
            reverse=True
        )

        melhor_jogador = ranking_jogadores[0] if ranking_jogadores else None
        melhor_time = ranking_times[0] if ranking_times else None

        pendentes = []
        votos_ids = {v.get("user_id") for v in votos if v.get("user_id")}
        for participante in partida.get("participantes", []):
            user_id = participante.get("user_id")
            if user_id and user_id not in votos_ids:
                pendentes.append(participante)

        total_jogadores = len(ranking_jogadores)
        votados = [item for item in ranking_jogadores if item.get("votos", 0) > 0 or item.get("nota_media", 0) > 0]
        if votados:
            soma_medias = sum(item["nota_media"] for item in votados)
            media_geral = round(soma_medias / len(votados), 2)
        else:
            media_geral = 0.0

        if partida.get("status") == "encerrada":
            self.confiabilidade_service.atualizar_historico(avaliacao_confiabilidade)

        return {
            "total_votos": len(votos),
            "total_jogadores": total_jogadores,
            "media_geral": media_geral,
            "confiabilidade_media_rodada": avaliacao_confiabilidade.get("confiabilidade_media_rodada", 1.0),
            "ranking_times": ranking_times,
            "ranking_jogadores": ranking_jogadores,
            "melhor_jogador": melhor_jogador,
            "melhor_time": melhor_time,
            "participantes_pendentes": pendentes,
        }

    def ranking_jogadores_geral(self, limite: int = 50, data_inicio: Optional[str] = None, data_fim: Optional[str] = None) -> Dict:
        """Retorna classificacao de jogadores usando rodadas encerradas no intervalo especificado."""
        partidas = self.listar()
        encerradas = [p for p in partidas if p.get("status") == "encerrada"]

        if data_inicio and data_fim:
            try:
                dt_ini = datetime.fromisoformat(data_inicio)
                dt_fim = datetime.fromisoformat(data_fim)
                filtradas = []
                for p in encerradas:
                    data_str = p.get("data") or p.get("encerrado_em") or p.get("criado_em")
                    if data_str:
                        try:
                            p_dt = datetime.fromisoformat(data_str)
                            if dt_ini <= p_dt <= dt_fim:
                                filtradas.append(p)
                        except Exception:
                            pass
                encerradas = filtradas
            except Exception as e:
                logger.error(f"Erro ao filtrar partidas por data no ranking: {str(e)}")

        acumulado: Dict[str, Dict] = {}
        total_votos = 0

        for partida in encerradas:
            votos = partida.get("votos", [])
            total_votos += len(votos)

            # Ranking apurado da rodada
            ranking_rodada = (partida.get("ranking") or {}).get("ranking_jogadores") or []
            ranking_rodada_dict = {
                item.get("jogador_nome"): item
                for item in ranking_rodada
                if item.get("jogador_nome")
            }

            participantes = {
                p.get("jogador_nome"): p
                for p in partida.get("participantes", [])
                if p.get("jogador_nome")
            }
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
                    "soma_medias_rodadas": 0.0,
                    "nota_total": 0.0,
                    "pontos": 0.0,
                    "avaliacoes": 0,
                    "gols": 0,
                    "vitorias": 0,
                    "derrotas": 0,
                    "empates": 0,
                    "destaques": 0,
                })
                item["jogos"] += 1

                # Soma a média obtida nesta rodada
                rk_info = ranking_rodada_dict.get(nome)
                if rk_info:
                    nota_rodada = float(rk_info.get("nota_media", 0) or 0)
                    item["soma_medias_rodadas"] += nota_rodada
                    item["avaliacoes"] += 1

                resultado_time = self._resultado_por_time(resultado, participante.get("time_numero")) if resultado else "empate"
                detalhe = detalhes_resultado.get(nome, {})
                item["gols"] += int(detalhe.get("gols", 0) or 0)

                if resultado_time == "vitoria":
                    item["vitorias"] += 1
                elif resultado_time == "derrota":
                    item["derrotas"] += 1
                else:
                    item["empates"] += 1

                if melhor_jogador and melhor_jogador == nome:
                    item["destaques"] += 1

        if not (data_inicio and data_fim):
            for jogador in self.jogador_service.listar_para_dict():
                nome = (jogador.get("nome") or "").strip()
                if not nome:
                    continue
                acumulado.setdefault(nome, {
                    "jogador_nome": nome,
                    "jogos": 0,
                    "soma_medias_rodadas": 0.0,
                    "nota_total": 0.0,
                    "pontos": 0.0,
                    "avaliacoes": 0,
                    "gols": 0,
                    "vitorias": 0,
                    "derrotas": 0,
                    "empates": 0,
                    "destaques": 0,
                })

        for item in acumulado.values():
            jogos = item.get("jogos", 0)
            avaliacoes = item.get("avaliacoes", 0)
            soma_medias = item.get("soma_medias_rodadas", 0.0)
            
            # Pontos é a soma das médias dos rankings das rodadas
            item["pontos"] = round(soma_medias, 2)
            item["nota_total"] = round(soma_medias, 2)
            item["nota_media"] = round(soma_medias / avaliacoes, 2) if avaliacoes else (round(soma_medias / jogos, 2) if jogos else 0.0)

        ranking = sorted(
            acumulado.values(),
            key=lambda x: (
                -float(x.get("pontos", 0) or 0),
                -float(x.get("nota_media", 0) or 0),
                -int(x.get("jogos", 0) or 0),
                -int(x.get("vitorias", 0) or 0),
                -int(x.get("destaques", 0) or 0),
                str(x.get("jogador_nome", "")).lower(),
            ),
        )
        ranking = ranking[:max(1, int(limite))]

        return {
            "ranking": ranking,
            "total_partidas": len(encerradas),
            "total_votos": total_votos,
            "total_jogadores": len(acumulado),
        }

    def encerrar_expiradas(self) -> None:
        dados = self._carregar()
        self._encerrar_expiradas_em_dados(dados)

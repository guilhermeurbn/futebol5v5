import json
import math
import os
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "confiabilidade_votos.json")


class VotoConfiabilidadeService:
    """
    Serviço Inteligente de Confiabilidade dos Votos para NaTrave 5v5.
    Calcula pesos de confiabilidade W(u, p) in [0.05, 1.00] para cada voto,
    prevenindo manipulação (favoritismo/sabotagem) sem bloquear ou descartar votos.
    """

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = data_file or DATA_FILE
        self.dados = self._carregar_dados()

    def _carregar_dados(self) -> Dict[str, Any]:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar confiabilidade_votos.json: {str(e)}")
        return {
            "evaluators": {},
            "relationships": {},
            "target_baselines": {}
        }

    def _salvar_dados(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar confiabilidade_votos.json: {str(e)}")

    def _obter_rel_avaliador(self, evaluator_id: str) -> float:
        ev = self.dados["evaluators"].get(str(evaluator_id), {})
        return float(ev.get("reliability", 1.0))

    def _obter_bias_relacionamento(self, evaluator_id: str, target_name: str) -> float:
        key = f"{evaluator_id}:{target_name}"
        rel = self.dados["relationships"].get(key, {})
        match_count = int(rel.get("match_count", 0))
        if match_count < 2:
            return 0.0
        avg_offset = float(rel.get("cumulative_offset", 0.0)) / match_count
        return avg_offset

    def _obter_baseline_jogador(self, target_name: str) -> Optional[float]:
        base = self.dados["target_baselines"].get(target_name, {})
        count = int(base.get("count", 0))
        if count >= 2:
            return float(base.get("historical_avg", 7.5))
        return None

    def calcular_fator_desvio_pares(self, nota: float, notas_outros: List[float]) -> float:
        """Fator 1: Diferença em relação aos demais votos (F_peer)"""
        if not notas_outros:
            return 1.0
        media_outros = sum(notas_outros) / len(notas_outros)
        desvio = abs(nota - media_outros)

        if desvio <= 1.2:
            return 1.0

        variancia = sum((x - media_outros) ** 2 for x in notas_outros) / len(notas_outros)
        std_dev = math.sqrt(variancia)

        escala = max(std_dev, 1.5)
        fator = math.exp(-((desvio - 1.2) ** 2) / (2 * (escala ** 2)))
        return max(0.15, min(1.0, round(fator, 4)))

    def calcular_fator_distribuicao(self, submissao_voto: List[Dict[str, Any]]) -> float:
        """Fator 3: Anomalias na distribuição interna da submissão do avaliador (F_dist)"""
        if not submissao_voto or len(submissao_voto) < 3:
            return 1.0

        notas = [float(v.get("nota", 0)) for v in submissao_voto]

        if len(set(notas)) == 1:
            return 0.35

        notas_ordenadas = sorted(notas)
        menor = notas_ordenadas[0]
        maior = notas_ordenadas[-1]

        if (maior - menor) >= 7.0:
            baixas = sum(1 for n in notas if n <= 3.0)
            altas = sum(1 for n in notas if n >= 8.5)
            total = len(notas)
            if (baixas >= total - 1 and altas == 1) or (altas >= total - 1 and baixas == 1):
                return 0.25

        return 1.0

    def calcular_fator_relacionamento(self, evaluator_id: str, target_name: str, desvio_atual: float) -> float:
        """Fator 4: Padrões de relacionamento e perseguição/favoritismo sistemático (F_rel)"""
        avg_offset = self._obter_bias_relacionamento(evaluator_id, target_name)
        abs_offset = abs(avg_offset)
        if abs_offset > 1.8:
            fator = 1.0 - (0.25 * (abs_offset - 1.5))
            return max(0.20, min(1.0, round(fator, 4)))
        return 1.0

    def calcular_fator_baseline_jogador(self, nota: float, target_name: str, media_pares: float) -> float:
        """Fator 5: Histórico do jogador avaliado (F_target_hist)"""
        baseline = self._obter_baseline_jogador(target_name)
        if baseline is None:
            return 1.0

        desvio_consenso = abs(media_pares - baseline)
        desvio_voto_baseline = abs(nota - baseline)
        desvio_voto_consenso = abs(nota - media_pares)

        if desvio_voto_baseline > 3.5 and desvio_consenso <= 1.5 and desvio_voto_consenso > 3.0:
            fator = math.exp(-(desvio_voto_consenso ** 2) / 8.0)
            return max(0.20, min(1.0, round(fator, 4)))

        return 1.0

    def avaliar_pesos_partida(self, partida_votos: List[Dict[str, Any]], participantes: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Calcula os pesos de confiabilidade de TODOS os votos de uma partida.
        Retorna estrutura detalhada com pesos por voto, média ponderada e relatório.
        """
        if not partida_votos:
            return {"pesos_votos": [], "confiabilidade_media_rodada": 1.0, "mapa_pesos": {}}

        notas_por_jogador: Dict[str, List[Dict[str, Any]]] = {}
        for voto_submissao in partida_votos:
            evaluator_id = str(voto_submissao.get("user_id") or voto_submissao.get("username") or "anonimo")
            submissao_items = voto_submissao.get("votos", [])
            fator_distrib = self.calcular_fator_distribuicao(submissao_items)

            for item in submissao_items:
                target_name = item.get("jogador_nome", "Jogador")
                nota = float(item.get("nota", 0))
                notas_por_jogador.setdefault(target_name, []).append({
                    "evaluator_id": evaluator_id,
                    "nota": nota,
                    "time_numero": item.get("time_numero"),
                    "fator_distrib": fator_distrib,
                })

        pesos_calculados = []
        mapa_pesos: Dict[str, Dict[str, float]] = {}
        soma_pesos_rodada = 0.0
        qtd_votos_total = 0

        for target_name, lista_votos in notas_por_jogador.items():
            for voto_item in lista_votos:
                eval_id = voto_item["evaluator_id"]
                nota = voto_item["nota"]
                f_dist = voto_item["fator_distrib"]

                outras_notas = [v["nota"] for v in lista_votos if v["evaluator_id"] != eval_id]
                media_outros = (sum(outras_notas) / len(outras_notas)) if outras_notas else nota

                f_peer = self.calcular_fator_desvio_pares(nota, outras_notas)
                f_eval_hist = self._obter_rel_avaliador(eval_id)
                f_rel = self.calcular_fator_relacionamento(eval_id, target_name, abs(nota - media_outros))
                f_target_hist = self.calcular_fator_baseline_jogador(nota, target_name, media_outros)

                peso_bruto = f_peer * f_eval_hist * f_dist * f_rel * f_target_hist
                peso_final = max(0.05, min(1.0, round(peso_bruto, 4)))

                soma_pesos_rodada += peso_final
                qtd_votos_total += 1

                mapa_pesos.setdefault(eval_id, {})[target_name] = peso_final

                pesos_calculados.append({
                    "evaluator_id": eval_id,
                    "target_name": target_name,
                    "nota": nota,
                    "peso": peso_final,
                    "fatores": {
                        "f_peer": f_peer,
                        "f_eval_hist": f_eval_hist,
                        "f_dist": f_dist,
                        "f_rel": f_rel,
                        "f_target_hist": f_target_hist,
                    },
                    "media_peers": round(media_outros, 2),
                })

        confiabilidade_media = round(soma_pesos_rodada / qtd_votos_total, 4) if qtd_votos_total else 1.0

        return {
            "pesos_votos": pesos_calculados,
            "confiabilidade_media_rodada": confiabilidade_media,
            "total_votos_processados": qtd_votos_total,
            "mapa_pesos": mapa_pesos,
        }

    def atualizar_historico(self, resultado_avaliado: Dict[str, Any]):
        """
        Atualiza o histórico persistente de confiabilidade dos avaliadores,
        relacionamentos e baselines após o encerramento da rodada.
        """
        pesos_votos = resultado_avaliado.get("pesos_votos", [])
        if not pesos_votos:
            return

        acertos_evaluators: Dict[str, List[float]] = {}
        rel_offsets: Dict[str, List[float]] = {}
        target_scores: Dict[str, List[float]] = {}

        for item in pesos_votos:
            eval_id = item["evaluator_id"]
            target = item["target_name"]
            nota = item["nota"]
            media_peers = item["media_peers"]
            f_peer = item["fatores"]["f_peer"]

            acertos_evaluators.setdefault(eval_id, []).append(f_peer)

            offset = nota - media_peers
            rel_key = f"{eval_id}:{target}"
            rel_offsets.setdefault(rel_key, []).append(offset)

            target_scores.setdefault(target, []).append(nota)

        for eval_id, f_peers in acertos_evaluators.items():
            perf_rodada = sum(f_peers) / len(f_peers)
            ev = self.dados["evaluators"].setdefault(str(eval_id), {
                "reliability": 1.0,
                "total_votos": 0,
            })
            r_old = float(ev.get("reliability", 1.0))
            r_new = round(0.85 * r_old + 0.15 * perf_rodada, 4)
            ev["reliability"] = max(0.20, min(1.0, r_new))
            ev["total_votos"] = int(ev.get("total_votos", 0)) + len(f_peers)

        for rel_key, offsets in rel_offsets.items():
            rel = self.dados["relationships"].setdefault(rel_key, {
                "match_count": 0,
                "cumulative_offset": 0.0,
            })
            rel["match_count"] = int(rel.get("match_count", 0)) + 1
            rel["cumulative_offset"] = float(rel.get("cumulative_offset", 0.0)) + sum(offsets)

        for target, notas in target_scores.items():
            base = self.dados["target_baselines"].setdefault(target, {
                "sum_scores": 0.0,
                "count": 0,
                "historical_avg": 7.5,
            })
            base["sum_scores"] = float(base.get("sum_scores", 0.0)) + sum(notas)
            base["count"] = int(base.get("count", 0)) + len(notas)
            base["historical_avg"] = round(base["sum_scores"] / base["count"], 2)

        self._salvar_dados()

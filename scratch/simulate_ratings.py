import json
import random
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
partidas_path = repo_root / "data" / "partidas.json"
historico_path = repo_root / "data" / "historico.json"
jogadores_path = repo_root / "data" / "jogadores.json"

with open(jogadores_path, "r", encoding="utf-8") as f:
    jogadores = json.load(f)

with open(partidas_path, "r", encoding="utf-8") as f:
    partidas = json.load(f)

with open(historico_path, "r", encoding="utf-8") as f:
    historico = json.load(f)

sample_ratings = [8.4, 6.7, 7.3, 8.0, 5.8, 7.5, 6.2, 8.8, 6.0, 7.7]

for i, p in enumerate(partidas):
    jogadores_detalhes = []
    ranking_jogadores = []
    
    for idx, j in enumerate(jogadores):
        r_idx = (i * 3 + idx * 7) % len(sample_ratings)
        nota = sample_ratings[r_idx]
        
        team_num = 1 if (idx % 2 == 0) else 2
        gols = random.choice([0, 0, 1, 2]) if team_num == 1 else random.choice([0, 0, 1])
        assist = random.choice([0, 1]) if gols > 0 else 0
        
        detalhe = {
            "nome": j["nome"],
            "jogador_id": j["id"],
            "user_id": j.get("owner_user_id"),
            "time_numero": team_num,
            "gols": gols,
            "assistencias": assist,
            "nota_media": nota,
            "nota_partida": nota
        }
        jogadores_detalhes.append(detalhe)
        
        ranking_jogadores.append({
            "jogador_nome": j["nome"],
            "jogador_id": j["id"],
            "user_id": j.get("owner_user_id"),
            "nota_media": nota,
            "gols": gols,
            "assistencias": assist
        })
        
    p["jogadores_detalhes"] = jogadores_detalhes
    p["ranking"] = {
        "ranking_jogadores": ranking_jogadores
    }

for i, h in enumerate(historico):
    ranking_jogadores = []
    for idx, j in enumerate(jogadores):
        r_idx = (i * 5 + idx * 3) % len(sample_ratings)
        nota = sample_ratings[r_idx]
        ranking_jogadores.append({
            "jogador_nome": j["nome"],
            "jogador_id": j["id"],
            "user_id": j.get("owner_user_id"),
            "nota_media": nota,
            "gols": random.choice([0, 1]),
            "assistencias": 0
        })
    h["ranking"] = {
        "ranking_jogadores": ranking_jogadores
    }

with open(partidas_path, "w", encoding="utf-8") as f:
    json.dump(partidas, f, ensure_ascii=False, indent=2)

with open(historico_path, "w", encoding="utf-8") as f:
    json.dump(historico, f, ensure_ascii=False, indent=2)

print(f"Simulação concluída com sucesso para {len(partidas)} partidas e {len(historico)} históricos!")

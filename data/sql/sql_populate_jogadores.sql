-- Copie e execute este SQL no Postgres Query Console do Railway

UPDATE app_json_store 
SET payload = '[
  {
    "nome": "Guilherme",
    "nivel": 7,
    "tipo": "fixo",
    "posicao": "linha",
    "presente": false,
    "id": "28bca010-ae01-4aff-b6f5-3e60cb104a6f",
    "criado_em": "2026-04-23T23:20:00.000002",
    "owner_user_id": "d0ba86dc-0e10-423d-a2a4-14e5ab1de033"
  }
]'::jsonb,
updated_at = NOW()
WHERE namespace = 'jogadores';

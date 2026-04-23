# AI Handoff - futebol5v5 (NaTrave)

## 1) Projeto: o que faz
Aplicacao web Flask para organizar jogos de futebol 5v5:
- cadastro de jogadores
- selecao de presentes (10/15/20)
- sorteio balanceado em 2/3/4 times
- historico e estatisticas
- campeonato (resultado de partidas)
- favoritos de times
- undo/redo de sorteios
- QR/link de compartilhamento
- exportacao CSV, TXT (copia), PDF
- sugestoes inteligentes
- ranking de times

## 2) Stack e dependencias
- Python + Flask
- Persistencia em JSON local (sem banco SQL)
- Frontend: Jinja2 + CSS + JS
- Extras: reportlab (PDF), qrcode[pil]

Arquivo de dependencias: requirements.txt

## 3) Como rodar
1. Criar/ativar venv
2. Instalar deps: pip install -r requirements.txt
3. Rodar: python run.py (preferido) ou python app.py
4. URL: http://localhost:5000

## 4) Estrutura principal
- app.py: factory Flask + registro de blueprint + /manifest.json
- routes/jogador_routes.py: quase toda logica HTTP (paginas + APIs)
- services/: regras de negocio
- models/jogadores.py: modelo Jogador
- templates/: paginas
- static/style.css: tema e UI
- manifest.json + static/service-worker.js: PWA

## 5) Arquivos de dados (runtime)
- jogadores.json: base principal de jogadores
- historico.json: sorteios realizados
- partidas.json: partidas registradas
- favoritos.json: times favoritos
- sorteios_stack.json: pilha undo/redo

Observacao: historico.json e sorteios_stack.json mudam constantemente em uso/testes.

## 6) Fluxo principal de sorteio
1. Usuario seleciona presentes em /selecionar
2. Presenca salva via POST /api/presenca
3. Sorteio via /sortear (pagina) ou /api/times (API)
4. Resultado salvo em:
   - historico.json
   - sessao (session['ultimo_sorteio'])
   - stack de undo/redo (sorteios_stack.json)
5. Tela de resultado: templates/times.html

## 7) Regras importantes de negocio
### 7.1 Quantidade valida
- somente 10, 15 ou 20 presentes (multiplo de 5)

### 7.2 Balanceamento
- service: services/balanceamento.py
- usa distribuicao por niveis + simulated annealing
- goleiro conta como jogador normal no total de 5 por time

### 7.3 Anti-repeticao (fix recente)
- routes/jogador_routes.py
- funcao _sortear_diferente_do_anterior(...)
- compara assinatura do sorteio novo com assinaturas recentes do stack + sessao
- tenta varias vezes; se repetir, aplica fallback de variacao forcada

## 8) Exportacao e compartilhamento
### 8.1 CSV
- GET /export/sorteio/csv

### 8.2 TXT para copiar (fix recente)
- botao da tela: "Copiar TXT"
- frontend chama GET /api/export/sorteio/txt
- copia para clipboard para colar no WhatsApp
- GET /export/sorteio/txt retorna texto inline (sem download forcado)

### 8.3 PDF
- GET /export/sorteio/pdf
- gerado por services/export_service.py (reportlab)

### 8.4 QR
- GET /api/qrcode/link-compartilhamento/<sorteio_id>
- pagina /compartilhado

## 9) Endpoints (mapa rapido)
### 9.1 Jogadores e presenca
- GET /api/jogadores
- POST /api/jogadores
- GET /api/jogadores/<jogador_id>
- PUT /api/jogadores/<jogador_id>
- DELETE /api/jogadores/<jogador_id>
- POST /api/presenca
- POST /api/presenca/limpar

### 9.2 Sorteio e historico
- GET /sortear
- GET /api/times
- GET /historico
- GET /sorteio/<sorteio_id>
- GET /api/historico

### 9.3 Estatisticas
- GET /estatisticas
- GET /stats (alias)
- GET /api/estatisticas
- GET /api/stats/players
- GET /api/stats/times
- GET /api/stats/geral
- GET /api/stats/combos
- GET /api/stats/comparacao/<player1>/<player2>
- GET /stats/players
- GET /stats/times
- GET /stats/combos
- GET /charts

### 9.4 Export
- GET /export/sorteio/csv
- GET /export/sorteio/txt
- GET /api/export/sorteio/txt
- GET /export/sorteio/pdf
- GET /export/historico/csv
- GET /export/estatisticas/csv
- POST /api/export/sorteio

### 9.5 Partidas/campeonato/favoritos
- GET /resultado_partida/<sorteio_id>
- POST /api/partida/registrar
- GET /campeonato
- GET /api/campeonato
- POST /api/favoritar-time
- GET /favoritos
- GET /api/favoritos
- DELETE /api/favorito/<fav_id>/remover
- POST /api/favorito/<fav_id>/renomear
- POST /api/favorito/<fav_id>/usar

### 9.6 Undo/Redo
- POST /api/sorteio/undo
- POST /api/sorteio/redo
- GET /api/sorteio/status
- POST /api/sorteio/adicionar-stack

### 9.7 Sugestoes e ranking
- POST /api/sugestoes/nivel
- POST /api/sugestoes/diversidade
- POST /api/sugestoes/vencedores
- POST /api/sugestoes/duplas
- POST /api/sugestoes/combinadas
- GET /ranking
- GET /api/ranking/geral
- GET /api/ranking/periodo/<dias>
- GET /api/ranking/stats

## 10) Servicos e papeis
- jogador_service.py: CRUD + presenca
- balanceamento.py: sorteio balanceado
- historico_service.py: historico + estatisticas base
- stats_service.py: agregacoes de stats
- export_service.py: CSV/TXT/PDF
- partida_service.py: resultados de partidas
- favorito_service.py: favoritos
- undoredo_service.py: pilha de sorteios
- qrcode_service.py: QR/share
- sugestoes_service.py: sugestoes inteligentes
- ranking_service.py: ranking de times

## 11) Frontend chave
- templates/index.html: home
- templates/selecionar.html: selecionar presentes
- templates/times.html: resultado, copiar TXT, export, QR, undo/redo
- templates/historico.html, estatisticas.html, campeonato.html, favoritos.html, ranking.html
- templates/_brand_header.html: header/logo compartilhado

## 12) Estado atual (importante)
- tema visual escuro e branding centralizado
- TXT por copia (nao download) implementado
- anti-repeticao de sorteios implementado para "novo sorteio"
- rota /stats alias de /estatisticas implementada

## 13) Riscos e pontos de atencao
- dados em JSON local: sem lock transacional, cuidado com concorrencia
- historico/stack podem crescer (manter politicas de limpeza)
- testes automatizados sao limitados (existem scripts de teste, nao suite completa)

## 14) Como outra IA deve trabalhar aqui
Checklist rapido antes de alterar:
1. Ler este arquivo + routes/jogador_routes.py + services/balanceamento.py + templates/times.html
2. Confirmar fluxo alvo (pagina /sortear ou API /api/times)
3. Rodar smoke test basico das rotas principais
4. Evitar quebrar compatibilidade dos JSONs existentes
5. Se alterar sorteio/export, validar:
   - /api/times
   - /sortear
   - /api/export/sorteio/txt
   - /export/sorteio/csv
   - /export/sorteio/pdf

## 15) Smoke test minimo sugerido
- GET /
- GET /selecionar
- POST /api/presenca com 15 ids
- GET /api/times
- GET /api/sorteio/status
- GET /api/export/sorteio/txt

Se todos retornarem 200/JSON valido, fluxo principal esta ok.

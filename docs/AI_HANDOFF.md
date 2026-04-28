# AI Handoff - NaTrave

## 1) O que e este projeto

Aplicacao web Flask para organizar jogos de futebol 5v5 com:

- autenticacao e perfis de acesso
- reset administrativo de senha
- cadastro de jogadores
- selecao de presentes
- sorteio equilibrado em 2, 3 ou 4 times
- historico de sorteios
- registro de resultado da partida
- votacao por rodada com prazo de 8 horas
- voto obrigatorio para participantes da rodada
- ranking de jogadores
- exportacao e compartilhamento
- suporte offline basico

Hoje o sistema e um painel operacional do jogo inteiro, nao apenas um sorteador.

## 2) Stack

- Python 3
- Flask
- Jinja2
- JSON local como persistencia principal
- ReportLab para PDF
- `qrcode[pil]` para QR code
- HTML + CSS + JavaScript vanilla
- Service Worker + fila local para comportamento offline

Dependencias: [requirements.txt](requirements.txt)

## 3) Como rodar

1. Criar e ativar ambiente virtual
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Rodar:

```bash
python run.py
```

Ou:

```bash
python app.py
```

Notas:

- `run.py` tenta uma porta livre entre `5000`, `5001`, `5002`, `5003`, `5004`, `8000` e `8001`
- `app.py` usa `PORT` ou cai em `10000`

## 4) Contas padrao

Geradas automaticamente por [services/auth_service.py](services/auth_service.py):

- `adminjogos` / `adminjogos123`
- `admin` / `admin123`

Trocar em qualquer ambiente serio.

## 5) Estrutura importante

- [app.py](app.py): factory Flask, config, `secret_key`, blueprint e `/manifest.json`
- [routes/jogador_routes.py](routes/jogador_routes.py): centro da aplicacao HTTP
- [services/](services): regras de negocio e persistencia em JSON
- [models/jogadores.py](models/jogadores.py): modelo `Jogador`
- [templates/](templates): frontend server-rendered
- [static/style.css](static/style.css): tema visual
- [static/offline-judge.js](static/offline-judge.js): fila offline e preview local
- [static/service-worker.js](static/service-worker.js): cache/PWA

## 6) Arquivos de dados em runtime

- `jogadores.json`
- `users.json`
- `historico.json`
- `partidas.json`
- `votacoes_partidas.json`
- `favoritos.json`
- `sorteios_stack.json`
- `admin_notificacoes.json`

Observacao:

- esses arquivos sao parte do estado do produto
- nao quebrar compatibilidade de formato sem migracao
- `historico.json` e `sorteios_stack.json` mudam com frequencia durante uso e testes

## 7) Perfis de acesso

- `super_admin`: acesso total
- `admin`: administracao geral
- `juiz`: fluxo operacional do jogo
- `usuario`: perfil proprio e votacao quando participante

As regras principais estao em [routes/jogador_routes.py](routes/jogador_routes.py), especialmente:

- `before_request`
- `login_required`
- `admin_required`
- `admin_or_juiz_required`

## 8) Fluxos principais

### 8.1 Sorteio

Fluxo:

1. Selecionar presentes em `/selecionar` ou `/jogar`
2. Salvar via `POST /api/presenca`
3. Sortear via `/sortear` ou `/api/times`
4. Salvar resultado em:
   - `historico.json`
   - `session['ultimo_sorteio']`
   - `sorteios_stack.json`

Arquivos chave:

- [routes/jogador_routes.py](routes/jogador_routes.py)
- [services/balanceamento.py](services/balanceamento.py)
- [services/historico_service.py](services/historico_service.py)
- [services/undoredo_service.py](services/undoredo_service.py)
- [templates/selecionar.html](templates/selecionar.html)
- [templates/times.html](templates/times.html)

### 8.2 Resultado da partida

Fluxo:

1. Abrir `/resultado_partida/<sorteio_id>`
2. Informar vencedor, gols e estatisticas por jogador
3. Enviar para `POST /api/partida/registrar`
4. Persistir em `partidas.json`

Arquivos chave:

- [services/partida_service.py](services/partida_service.py)
- [services/jogador_stats_service.py](services/jogador_stats_service.py)
- [templates/resultado_partida.html](templates/resultado_partida.html)

### 8.3 Votacao

Fluxo:

1. Admin ou juiz abre votacao usando o ultimo sorteio
2. A rodada recebe prazo automatico de 8 horas
3. Participantes ficam com voto pendente e sao redirecionados para `/votacao`
4. Participantes votam em pelo menos 5 jogadores
5. Admin ou juiz pode encerrar antes, ou o sistema encerra ao expirar
6. Ranking da rodada fica salvo em `votacoes_partidas.json`

Arquivos chave:

- [services/votacao_service.py](services/votacao_service.py)
- [templates/votacao_usuario.html](templates/votacao_usuario.html)
- [templates/votacao_admin.html](templates/votacao_admin.html)

### 8.4 Ranking

O ranking atualmente exposto na UI e ranking de jogadores baseado nas votacoes encerradas.

Arquivos chave:

- [services/votacao_service.py](services/votacao_service.py)
- [templates/ranking.html](templates/ranking.html)

Observacao:

- existe [services/ranking_service.py](services/ranking_service.py), mas ele representa ranking de times e hoje nao e o motor principal da pagina `/ranking`

## 9) Regras de negocio que nao podem ser esquecidas

### 9.1 Quantidade valida de presentes

Somente:

- `10`
- `15`
- `20`

### 9.2 Tamanho dos times

- sempre `5` jogadores por time

### 9.3 Balanceamento

Em [services/balanceamento.py](services/balanceamento.py):

- goleiro conta como jogador normal
- goleiros sao distribuidos primeiro
- jogadores de linha completam os times
- simulated annealing refina o equilibrio

### 9.4 Anti-repeticao de sorteio

Em [routes/jogador_routes.py](routes/jogador_routes.py):

- `_sortear_diferente_do_anterior`
- compara assinaturas de sorteios recentes
- usa pilha de undo/redo e sessao como referencia
- tenta varias vezes e ainda aplica uma variacao forcada se necessario

## 10) Endpoints mais importantes

### 10.1 Autenticacao e perfil

- `GET /login`
- `POST /login`
- `POST /logout`
- `GET /cadastro`
- `POST /cadastro`
- `GET /perfil`

### 10.2 Jogadores e presenca

- `GET /api/jogadores`
- `POST /api/jogadores`
- `GET /api/jogadores/<jogador_id>`
- `PUT /api/jogadores/<jogador_id>`
- `DELETE /api/jogadores/<jogador_id>`
- `POST /api/presenca`
- `POST /api/presenca/limpar`

### 10.3 Sorteio e historico

- `GET /sortear`
- `GET /api/times`
- `GET /historico`
- `GET /sorteio/<sorteio_id>`
- `GET /api/historico`
- `POST /api/sorteio/undo`
- `POST /api/sorteio/redo`
- `GET /api/sorteio/status`

### 10.4 Resultado, votacao e ranking

- `GET /resultado_partida/<sorteio_id>`
- `POST /api/partida/registrar`
- `GET /votacao`
- `POST /votacao/salvar`
- `GET /admin/votacao`
- `POST /admin/votacao/criar`
- `POST /admin/votacao/<partida_id>/encerrar`
- `GET /ranking`
- `GET /api/ranking/geral`

### 10.5 Exportacao e compartilhamento

- `GET /export/sorteio/csv`
- `GET /export/sorteio/txt`
- `GET /api/export/sorteio/txt`
- `GET /export/sorteio/pdf`
- `GET /api/qrcode/link-compartilhamento/<sorteio_id>`
- `GET /compartilhado`

## 11) Frontend que mais importa

- [templates/index.html](templates/index.html): home de administracao de jogadores
- [templates/selecionar.html](templates/selecionar.html): selecao de presentes
- [templates/times.html](templates/times.html): resultado do sorteio
- [templates/resultado_partida.html](templates/resultado_partida.html): registro de resultado
- [templates/votacao_usuario.html](templates/votacao_usuario.html): voto do participante
- [templates/votacao_admin.html](templates/votacao_admin.html): abertura e encerramento da votacao
- [templates/ranking.html](templates/ranking.html): ranking de jogadores
- [templates/perfil.html](templates/perfil.html): perfil do usuario e senha
- [templates/_brand_header.html](templates/_brand_header.html): header compartilhado

## 12) PWA e offline

Arquivos:

- [manifest.json](manifest.json)
- [static/service-worker.js](static/service-worker.js)
- [static/offline-judge.js](static/offline-judge.js)

Capacidades:

- cache de paginas e assets
- fallback offline
- fila local para algumas submisses
- preview local de sorteio

## 13) Inconsistencias e dividas tecnicas importantes

- [routes/jogador_routes.py](routes/jogador_routes.py) esta muito grande e centraliza orquestracao demais
- existem rotas e templates legados que ainda permanecem por compatibilidade
- [services/ranking_service.py](services/ranking_service.py) existe, mas ele representa ranking de times e hoje nao e o motor principal da pagina `/ranking`
- [templates/ranking.html](templates/ranking.html) espera campos como `gols`, `assistencias`, `vitorias` e `destaques`, mas `ranking_jogadores_geral()` hoje nao devolve tudo isso
- [templates/selecionar.html](templates/selecionar.html) inclui `offline-judge.js` duas vezes
- a persistencia em JSON nao oferece controle transacional

## 14) Como outra IA deve trabalhar aqui

Checklist rapido:

1. Ler este arquivo
2. Ler [README.md](README.md)
3. Ler [routes/jogador_routes.py](routes/jogador_routes.py)
4. Ler o servico central do fluxo em questao antes de editar
5. Confirmar se a mudanca afeta JSON persistido
6. Confirmar se a mudanca afeta pagina HTML, endpoint JSON ou ambos

Mapeamento rapido por tipo de tarefa:

- sorteio: `balanceamento.py`, `jogador_routes.py`, `selecionar.html`, `times.html`
- autenticacao/permissoes: `auth_service.py`, `jogador_routes.py`
- resultado da partida: `partida_service.py`, `jogador_stats_service.py`, `resultado_partida.html`
- votacao/ranking: `votacao_service.py`, `votacao_admin.html`, `votacao_usuario.html`, `ranking.html`
- offline/PWA: `offline-judge.js`, `service-worker.js`

## 15) Smoke test minimo sugerido

Se for alterar o fluxo principal, validar pelo menos:

- `GET /login`
- `GET /`
- `GET /selecionar` ou `GET /jogar`
- `POST /api/presenca` com quantidade valida
- `GET /api/times`
- `GET /api/sorteio/status`
- `GET /api/export/sorteio/txt`

Se mexer em votacao:

- abrir votacao via `/admin/votacao`
- votar em `/votacao`
- encerrar rodada
- abrir `/ranking`

## 16) Testes existentes

- [test_multiplos_times.py](test_multiplos_times.py): cobre cenarios de 10, 15 e 20 jogadores
- [test_goleiros.py](test_goleiros.py): exercita distribuicao com goleiros

Notas:

- a cobertura automatica ainda e limitada
- parte dos testes funciona mais como smoke script do que como suite formal

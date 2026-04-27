# NaTrave

Aplicacao web Flask para organizar jogos de futebol 5v5 com cadastro de jogadores, selecao de presentes, sorteio equilibrado, registro de resultados, votacao por partida e ranking.

Hoje o projeto funciona mais como um painel completo de gestao do jogo do que apenas como um "gerador de times".

## Visao Geral

O NaTrave cobre o fluxo completo de uma pelada organizada:

1. Cadastro e autenticacao de usuarios
2. Vinculo automatico de um jogador ao usuario cadastrado
3. Selecao de 10, 15 ou 20 presentes
4. Sorteio de 2, 3 ou 4 times de 5 jogadores
5. Registro de resultado da partida
6. Abertura da votacao da rodada pelo juiz ou admin
7. Voto obrigatorio dos participantes da rodada
8. Encerramento manual ou automatico em 8 horas
9. Apuracao de ranking por notas
10. Historico, exportacao e compartilhamento

## Funcionalidades Atuais

- Autenticacao com perfis `super_admin`, `admin`, `juiz` e `usuario`
- Reset simples de senha por `admin` com senha temporaria
- Cadastro de jogadores com nome, nivel, tipo e posicao
- Fluxo dedicado para o `juiz` em `/jogar`
- Selecao de presenca com validacao de 10, 15 ou 20 jogadores
- Sorteio equilibrado com suporte a goleiros
- Anti-repeticao de sorteios recentes
- Historico completo de sorteios
- Undo/redo dos sorteios recentes
- Registro de resultados com gols, assistencias e cartoes
- Votacao por rodada com prazo de 8 horas
- Voto obrigatorio para participantes enquanto a rodada estiver aberta
- Ranking geral de jogadores com base nas votacoes encerradas
- Exportacao de sorteio em CSV, TXT e PDF
- Compartilhamento por link e QR code
- Favoritos de times
- Suporte offline com fila local e cache via Service Worker

## Regras de Negocio Principais

### Quantidade de jogadores

O sistema aceita apenas:

- `10` jogadores -> `2` times
- `15` jogadores -> `3` times
- `20` jogadores -> `4` times

Cada time tem exatamente `5` jogadores.

### Balanceamento

O algoritmo atual fica em [services/balanceamento.py](services/balanceamento.py).

Resumo do comportamento:

- goleiros contam como jogadores normais no total de 5 por time
- goleiros sao distribuidos primeiro
- jogadores de linha sao distribuidos para completar os times
- o equilibrio final e refinado com simulated annealing
- o sistema tenta evitar repetir composicoes muito recentes

### Perfis de acesso

- `super_admin`: acesso total
- `admin`: gestao completa do sistema e dos usuarios
- `juiz`: acesso ao fluxo operacional do jogo e da votacao da rodada
- `usuario`: acesso ao proprio perfil e a votacao quando participa de uma partida

## Stack

- Python 3
- Flask
- Jinja2
- Persistencia em JSON local
- ReportLab para PDF
- `qrcode[pil]` para compartilhamento via QR code
- HTML, CSS e JavaScript vanilla no frontend
- Service Worker para experiencia offline

## Estrutura do Projeto

```text
futebol5v5/
├── app.py
├── run.py
├── config.py
├── routes/
│   └── jogador_routes.py
├── services/
│   ├── auth_service.py
│   ├── balanceamento.py
│   ├── export_service.py
│   ├── favorito_service.py
│   ├── historico_service.py
│   ├── jogador_service.py
│   ├── jogador_stats_service.py
│   ├── notificacao_service.py
│   ├── partida_service.py
│   ├── qrcode_service.py
│   ├── ranking_service.py
│   ├── stats_service.py
│   ├── sugestoes_service.py
│   ├── undoredo_service.py
│   └── votacao_service.py
├── models/
│   └── jogadores.py
├── templates/
├── static/
├── jogadores.json
├── historico.json
├── partidas.json
├── users.json
└── votacoes_partidas.json
```

## Arquitetura Real

- `app.py`: factory Flask, configuracao base, secret key e registro do blueprint
- `routes/jogador_routes.py`: concentrador das rotas HTTP, permissao, paginas e APIs
- `services/`: camada de regra de negocio e persistencia em JSON
- `models/jogadores.py`: dataclass principal de jogador
- `templates/`: paginas server-rendered com Jinja
- `static/`: CSS, JavaScript e recursos PWA

Observacao importante: o arquivo `routes/jogador_routes.py` concentra boa parte da orquestracao do sistema. A arquitetura continua em camadas, mas a camada de rotas hoje esta mais densa do que a documentacao antiga sugeria.

## Como Rodar

### 1. Criar ambiente virtual

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Iniciar a aplicacao

Modo recomendado:

```bash
python run.py
```

Modo direto:

```bash
python app.py
```

### 4. Acessar no navegador

O `run.py` tenta subir em uma porta disponivel entre `5000`, `5001`, `5002`, `5003`, `5004`, `8000` e `8001`.

No `app.py`, sem `run.py`, a aplicacao usa a variavel `PORT` ou cai em `10000`.

## Contas e Autenticacao

O sistema garante contas padrao em [services/auth_service.py](services/auth_service.py):

- `adminjogos` / `adminjogos123`
- `admin` / `admin123`

Use apenas para ambiente local ou desenvolvimento. Em producao, troque credenciais e defina `SECRET_KEY`.

## Arquivos de Dados

O projeto usa JSON local como persistencia:

- `jogadores.json`: jogadores cadastrados
- `users.json`: usuarios e senhas hash
- `historico.json`: sorteios realizados
- `partidas.json`: resultados de partidas
- `votacoes_partidas.json`: votacoes abertas e encerradas
- `favoritos.json`: times favoritados
- `sorteios_stack.json`: pilha de undo/redo
- `admin_notificacoes.json`: notificacoes administrativas

## Fluxos Principais

### Fluxo do juiz

1. Entrar em `/jogar`
2. Selecionar 10, 15 ou 20 jogadores
3. Salvar presenca
4. Sortear os times
5. Registrar o resultado da partida
6. Abrir e encerrar a votacao da rodada

### Fluxo do usuario

1. Criar conta ou entrar
2. Aceder ao proprio perfil
3. Participar da votacao quando estiver numa partida aberta
4. Consultar historico e ranking

## Endpoints Principais

### Autenticacao e perfil

- `GET /login`
- `POST /login`
- `POST /logout`
- `GET /cadastro`
- `POST /cadastro`
- `GET /perfil`

### Jogadores

- `GET /api/jogadores`
- `POST /api/jogadores`
- `GET /api/jogadores/<jogador_id>`
- `PUT /api/jogadores/<jogador_id>`
- `DELETE /api/jogadores/<jogador_id>`

### Presenca e sorteio

- `POST /api/presenca`
- `POST /api/presenca/limpar`
- `GET /sortear`
- `GET /api/times`
- `POST /api/sorteio/undo`
- `POST /api/sorteio/redo`
- `GET /api/sorteio/status`

### Historico e compartilhamento

- `GET /historico`
- `GET /sorteio/<sorteio_id>`
- `GET /api/historico`
- `GET /api/qrcode/link-compartilhamento/<sorteio_id>`
- `GET /compartilhado`

### Resultado e votacao

- `GET /resultado_partida/<sorteio_id>`
- `POST /api/partida/registrar`
- `GET /votacao`
- `POST /votacao/salvar`
- `GET /admin/votacao`
- `POST /admin/votacao/criar`
- `POST /admin/votacao/<partida_id>/encerrar`

### Exportacao

- `GET /export/sorteio/csv`
- `GET /export/sorteio/txt`
- `GET /api/export/sorteio/txt`
- `GET /export/sorteio/pdf`
- `GET /export/historico/csv`
- `GET /export/estatisticas/csv`

### Ranking

- `GET /ranking`
- `GET /api/ranking/geral`

Observacao: alguns endpoints antigos continuam no codigo por compatibilidade, mas parte deles esta desativada ou hoje redireciona para a home.

## Testes

Existem dois scripts principais de validacao manual:

```bash
python test_multiplos_times.py
python test_goleiros.py
```

Notas sobre o estado atual:

- `test_multiplos_times.py` valida cenarios com 10, 15 e 20 jogadores
- `test_goleiros.py` exercita o algoritmo com goleiros
- a cobertura automatica ainda e limitada
- parte dos testes tem perfil mais de script de smoke test do que de suite formal

## Offline e PWA

O projeto inclui:

- `manifest.json`
- `static/service-worker.js`
- `static/offline-judge.js`

Capacidades atuais:

- cache de paginas e assets principais
- fallback basico quando offline
- fila local para submissao posterior de algumas operacoes
- preview local de sorteio no fluxo offline

## Limitacoes Conhecidas

- persistencia em JSON local, sem garantias de concorrencia
- crescimento continuo dos arquivos de historico
- parte da documentacao auxiliar antiga ainda pode estar desatualizada
- algumas rotas legadas seguem no codigo por compatibilidade
- a suite de testes ainda nao cobre o sistema inteiro

## Documentacao Relacionada

- [ARQUITETURA.md](ARQUITETURA.md)
- [AI_HANDOFF.md](AI_HANDOFF.md)
- [HOSPEDAGEM_E_OFFLINE.md](HOSPEDAGEM_E_OFFLINE.md)
- [SELECAO_JOGADORES.md](SELECAO_JOGADORES.md)

## Proximo Passo Recomendado

Depois deste `README`, o melhor alinhamento e atualizar o `ARQUITETURA.md` para refletir a estrutura atual do sistema, especialmente autenticacao, fluxo do juiz, votacao e offline.

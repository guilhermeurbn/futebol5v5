# Arquitetura do Projeto

## Resumo

O NaTrave e uma aplicacao Flask com renderizacao server-side, regras de negocio em servicos e persistencia em JSON local.

A arquitetura continua organizada em camadas, mas o projeto evoluiu para um sistema maior do que o CRUD inicial. Hoje ele inclui autenticacao, perfis de acesso, fluxo do juiz, sorteio balanceado, historico, resultado de partidas, votacao, ranking, exportacao, QR code e suporte offline.

## Estrutura Atual

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
└── *.json
```

## Camadas

### 1. Aplicacao

Arquivo: [app.py](app.py)

Responsabilidades:

- criar a app Flask via factory
- carregar configuracao
- configurar `secret_key`
- registrar o blueprint principal
- servir o `manifest.json`

### 2. Rotas

Arquivo central: [routes/jogador_routes.py](routes/jogador_routes.py)

Responsabilidades:

- paginas HTML
- endpoints JSON
- controle de sessao
- controle de permissao por perfil
- orquestracao entre os servicos

Observacao importante:

Esse arquivo hoje concentra muita responsabilidade. Ele funciona como um controlador principal do sistema e ja nao representa apenas "rotas de jogador".

### 3. Modelos

Arquivo: [models/jogadores.py](models/jogadores.py)

Hoje existe um modelo explicito principal:

- `Jogador`: dataclass com validacao de nome, nivel, tipo, posicao e metadados

Outras estruturas de dominio sao persistidas diretamente como dicionarios JSON, sem dataclasses dedicadas.

### 4. Servicos

Os servicos concentram regra de negocio e acesso aos arquivos JSON.

- `auth_service.py`: usuarios, login, senha e perfis
- `jogador_service.py`: CRUD de jogadores e presenca
- `balanceamento.py`: algoritmo de sorteio equilibrado
- `historico_service.py`: historico de sorteios
- `partida_service.py`: resultados de partidas e placar geral
- `votacao_service.py`: abertura, votos e apuracao
- `jogador_stats_service.py`: estatisticas detalhadas por jogador
- `stats_service.py`: estatisticas agregadas de sorteios
- `export_service.py`: CSV, TXT e PDF
- `favorito_service.py`: favoritos de times
- `undoredo_service.py`: pilha de sorteios
- `qrcode_service.py`: links e QR codes
- `sugestoes_service.py`: sugestoes de jogadores
- `ranking_service.py`: ranking de times legado/auxiliar
- `notificacao_service.py`: notificacoes administrativas

### 5. Frontend

Camadas:

- `templates/`: HTML com Jinja
- `static/style.css`: design system visual
- `static/offline-judge.js`: fila offline e preview local
- `static/service-worker.js`: cache e suporte PWA

O frontend e majoritariamente server-rendered, com JavaScript pontual para interacoes como:

- salvar presenca
- sortear
- undo/redo
- exportar/copiar texto
- gerar QR code
- submeter resultado da partida
- carregar sugestoes

### 6. Persistencia

O sistema usa arquivos JSON locais como fonte de verdade.

Arquivos principais:

- `jogadores.json`
- `users.json`
- `historico.json`
- `partidas.json`
- `votacoes_partidas.json`
- `favoritos.json`
- `sorteios_stack.json`
- `admin_notificacoes.json`

## Fluxos Principais

### Fluxo de autenticacao

```text
Formulario de login/cadastro
    ↓
AuthService
    ↓
users.json
    ↓
session Flask
```

### Fluxo de sorteio

```text
Selecao de presentes
    ↓
JogadorService.marcar_presenca
    ↓
/sortear ou /api/times
    ↓
BalanceadorTimes
    ↓
HistoricoService + session['ultimo_sorteio'] + UndoRedoService
```

### Fluxo de resultado e votacao

```text
Resultado da partida
    ↓
PartidaService.registrar_resultado
    ↓
JogadorStatsService.registrar_desempenho_jogador
    ↓
VotacaoService.criar_partida
    ↓
VotacaoService.salvar_voto
    ↓
VotacaoService.encerrar_e_apurar
```

## Perfis e Permissoes

Os perfis atuais sao:

- `super_admin`
- `admin`
- `juiz`
- `usuario`

Regras gerais:

- `admin` e `super_admin` tem acesso total
- `juiz` tem acesso ao fluxo operacional do jogo
- `usuario` participa da votacao e ve seu proprio contexto

As regras sao aplicadas principalmente em:

- `before_request` do blueprint
- decorators `login_required`, `admin_required` e `admin_or_juiz_required`

## Algoritmo de Balanceamento

Arquivo: [services/balanceamento.py](services/balanceamento.py)

Comportamento atual:

- cada time tem 5 jogadores
- goleiro conta como jogador normal no total
- a quantidade total precisa ser multipla de 5
- goleiros sao distribuidos primeiro
- os jogadores de linha completam os times
- simulated annealing e usado para reduzir a diferenca de nivel entre os times
- ha logica adicional para evitar repetir sorteios recentes

Isso substitui a descricao antiga de "snake draft simples" como representacao completa do sistema.

## PWA e Offline

Arquivos:

- `manifest.json`
- `static/service-worker.js`
- `static/offline-judge.js`

Capacidades:

- cache de assets e paginas principais
- fallback offline para algumas navegacoes
- fila local para requests quando a rede falha
- preview local de sorteio em modo offline

## Decisoes Arquiteturais Importantes

### Persistencia em JSON

Vantagens:

- simplicidade
- setup local rapido
- facil inspecao manual dos dados

Tradeoffs:

- sem controle transacional
- risco de concorrencia
- crescimento continuo dos arquivos
- acoplamento entre formato persistido e o codigo

### Blueprint unico

Vantagem:

- ponto central facil de encontrar

Tradeoff:

- concentracao excessiva de responsabilidades
- arquivo grande
- manutencao mais dificil com o crescimento do produto

## Estado Atual da Arquitetura

Pontos fortes:

- fluxo funcional ponta a ponta
- separacao razoavel entre regras e apresentacao
- baixo custo operacional
- suporte offline relevante para o contexto do produto

Pontos de atencao:

- `routes/jogador_routes.py` esta grande demais
- nem todas as entidades de dominio possuem modelos dedicados
- existe codigo legado e endpoints mantidos por compatibilidade
- algumas documentacoes auxiliares antigas podem divergir do codigo atual

## Direcao de Evolucao Recomendada

1. dividir `routes/jogador_routes.py` por contexto funcional
2. criar modelos/DTOs para votacao, partida e favoritos
3. isolar melhor persistencia de dominio para reduzir acoplamento com JSON cru
4. ampliar testes automatizados dos fluxos HTTP principais
5. revisar rotas legadas e templates nao mais usados

# 🎨 Proposta de Redesenho: Painel do Juiz (Judge Panel)

## 📋 Visão Geral

Transformar o painel do juiz em uma experiência **premium, minimalista e objetivo**, com 3 seções principais navegáveis via tabs/buttons no header. O layout elimina ruído visual, mantém a linguagem de design dos cards premium de jogadores e prioriza a velocidade do fluxo de trabalho.

---

## 🏗️ Análise da Arquitetura Atual

### Problemas Identificados

1. **Header desorganizado**: O header atual mistura hero com steps em um painel único (`.judge-hero`)
2. **Sem navegação clara entre seções**: usuário precisa usar breadcrumbs ou forms implícitos
3. **Muita informação na home**:
   - Hero + steps (redundante)
   - Última partida com grid de stats
   - Grid completo de jogadores (distrai do objetivo)
4. **Templates desconexos**: cada página (juiz_criar_partida.html, times.html, resultado_partida.html) tem seu próprio header/estrutura
5. **CSS classes inconsistentes**:
   - `.judge-hero`, `.judge-step-card`, `.judge-selection-hero` (nomes muito específicos)
   - Falta um padrão unificado para o painel
6. **Falta de contexto visual**: usuário não sabe em qual seção está enquanto navega

### Oportunidades

- ✅ Já existe `.player-card--premium` com estilos de gradiente/backdrop-filter
- ✅ Design system robusto em style.css (cores, sombras, tipografia)
- ✅ Flask + Jinja2 permite reutilização fácil de componentes
- ✅ Responsive design já implementado

---

## 🎯 Novo Padrão: 3 Seções Principais

### Estrutura Conceitual

```
┌─────────────────────────────────────────┐
│  HEADER PREMIUM (Minimalista)           │
│  Logo | 3 TABS (Criar | Compartilhar | Votações)
├─────────────────────────────────────────┤
│                                         │
│  [SEÇÃO ATIVA]                          │
│  - Conteúdo focado                      │
│  - Sem distrações                       │
│  - Ações claras                         │
│                                         │
└─────────────────────────────────────────┘
```

---

## 📄 Layout Proposto por Página

### 1. **JUIZ HOME** → `juiz_home.html` (Nova Estrutura)

#### Objetivo
- Hub de acesso às 3 ações principais
- Exibir contexto rápido da última partida (opcional/compacto)
- Grid de jogadores (se necessário mostrar disponibilidade)

#### Layout Recomendado

```
┌─────────────────────────────────────────┐
│         HEADER PREMIUM (MINIMALISTA)    │
│    Logo "Painel do Juiz" (sem subtitle) │
│    [BTN: Criar] [BTN: Compartilhar] [BTN: Votações]
├─────────────────────────────────────────┤
│                                         │
│  ╔══════════════════════════════════╗   │
│  ║  🎯 AÇÕES PRINCIPAIS             ║   │
│  ╠══════════════════════════════════╣   │
│  ║                                  ║   │
│  ║  ┌──────────┐ ┌──────────┐      ║   │
│  ║  │ Criar    │ │Compartir │      ║   │
│  ║  │Partida   │ │Times     │      ║   │
│  ║  │ 🎲      │ │ 👥      │      ║   │
│  ║  └──────────┘ └──────────┘      ║   │
│  ║       ┌──────────┐               ║   │
│  ║       │ Votações │               ║   │
│  ║       │ 🗳️      │               ║   │
│  ║       └──────────┘               ║   │
│  ║                                  ║   │
│  ╚══════════════════════════════════╝   │
│                                         │
│  ╔══════════════════════════════════╗   │
│  ║   📊 ÚLTIMA RODADA (COMPACTO)     ║   │
│  ║  Partida #42 | Time A: 12 x 8    ║   │
│  ║  Melhor Jogador: João Silva      ║   │
│  ╚══════════════════════════════════╝   │
│                                         │
│  ╔══════════════════════════════════╗   │
│  ║  👥 ELENCO DISPONÍVEL            ║   │
│  ║  [ Grid de player cards ]         ║   │
│  ╚══════════════════════════════════╝   │
│                                         │
└─────────────────────────────────────────┘
```

#### Elementos Estruturais

| Componente | Tipo | Status | Nota |
|-----------|------|--------|------|
| Header com logo | Simples | MANTER | Centralizado, sem subtitle |
| Tab/Button Bar | Navegação | CRIAR | 3 buttons grandes (não tabs tradicionais) |
| Hero Actions | CTA Grid | SIMPLIFICAR | 3 cards grandes com ícones + labels |
| Last Match Card | Info | COMPACTAR | Remover grid de stats, manter resumo 1 linha |
| Players Grid | Exibição | MANTER | Reutilizar player-card--premium |
| Empty State | Feedback | MANTER | Se não há última partida/jogadores |

#### Elementos a REMOVER

- ❌ `.judge-hero__steps` - card de steps é desnecessário (fluxo é óbvio)
- ❌ Resumo completo com tabela de ranking
- ❌ Descrição detalhada de cada etapa
- ❌ Múltiplos badges informativos

#### Elementos a ADICIONAR

- ✅ Navigation bar (3 action buttons no topo)
- ✅ Visual indicator da seção atual (tab ativa)
- ✅ Quick action cards com ícones + gradientes
- ✅ Compact last match info (1 card simples)

---

### 2. **CRIAR PARTIDA** → `juiz_criar_partida.html` (Nova Estrutura)

#### Objetivo
- Fluxo em 2 etapas diretas: quantidade + seleção/sorteio
- Tudo na mesma tela (sem navegação entre páginas)
- Foco absoluto no seletor de jogadores

#### Layout Recomendado

```
┌─────────────────────────────────────────┐
│  Header: "Criar Partida"                │
│  [← Voltar] [Active Tab: Criar]         │
├─────────────────────────────────────────┤
│                                         │
│  ╔══════════════════════════════════╗   │
│  ║ ETAPA 1: Quantidade              ║   │
│  ║                                  ║   │
│  ║  Escolha o tamanho:              ║   │
│  ║  ┌────────┐ ┌────────┐ ┌────────┐║   │
│  ║  │ 10     │ │ 15     │ │ 20     ││   │
│  ║  │ 2 times│ │ 3 times│ │ 4 times││   │
│  ║  └────────┘ └────────┘ └────────┘║   │
│  ║                                  ║   │
│  ║  Status: [Disponíveis] / [Meta] │   │
│  ║           15 / 10 ✓              ║   │
│  ║                                  ║   │
│  ╚══════════════════════════════════╝   │
│                                         │
│  ╔══════════════════════════════════╗   │
│  ║ ETAPA 2: Seleção de Jogadores    ║   │
│  ║                                  ║   │
│  ║ [ Player Cards Grid ]            ║   │
│  ║ (selecionar 10/15/20)            ║   │
│  ║                                  ║   │
│  ║ [Limpar] [Sortear >]             ║   │
│  ║          (botão ativo se meta OK)║   │
│  ║                                  ║   │
│  ╚══════════════════════════════════╝   │
│                                         │
└─────────────────────────────────────────┘
```

#### Elementos Estruturais

| Componente | Tipo | Status | Nota |
|-----------|------|--------|------|
| Header | Minimalista | MANTER | "Criar Partida" + back link |
| Quantity Selector | CTA | MELHORAR | 3 cards maiores com descripção |
| Selection Counter | Stats | MANTER | Mostra selecionados vs meta |
| Players Grid | Seletor | MANTER | Checkboxes discretos + visuais |
| Action Bar | CTA | SIMPLIFICAR | 2 botões: Limpar | Sortear |
| Feedback | Validação | ADICIONAR | Status visual "meta atingida" |

#### Elementos a REMOVER

- ❌ `.judge-selection-hero` - painel com explicação detalhada
- ❌ `.judge-selection-stats` - cards de stats (mover para badge simples)
- ❌ Descrição redundante de como selecionar
- ❌ Formulário implícito (usar AJAX para sorteio)

#### Elementos a ADICIONAR

- ✅ Visual feedback: status da meta (Disponíveis | Selecionados | Meta)
- ✅ Botão "Sortear" com estado ativo/inativo
- ✅ Animação discreta ao atingir meta
- ✅ Layout robusto: quantity cards maiores, mais clicáveis

---

### 3. **COMPARTILHAR TIMES** → `times.html` (Nova Estrutura)

#### Objetivo
- Visualizar os 2+ times gerados
- Ações claras: Registrar Resultado | Voltar | QR/Compartilhar (opcional)

#### Layout Recomendado

```
┌─────────────────────────────────────────┐
│  Header: "Resultado do Sorteio"         │
│  [← Voltar] [Active Tab: Compartilhar]  │
├─────────────────────────────────────────┤
│                                         │
│  Sorteio #42 | 10 jogadores (2 times)  │
│                                         │
│  ╔═══════════════════╦═══════════════════╗│
│  ║    TIME 1 (A)     ║    TIME 2 (B)     ║│
│  ║                   ║                   ║│
│  ║ 🧤 João Silva N5  ║ 🧤 Pedro Costa N4 ║│
│  ║ ⚽ Maria Oliveira ║ ⚽ Ana Silva      ║│
│  ║    N3             ║    N3             ║│
│  ║ ⚽ Carlos Santos  ║ ⚽ Bruno Alves    ║│
│  ║    N2             ║    N2             ║│
│  ║ ⚽ Fernanda Costa ║ ⚽ Juliana Rocha  ║│
│  ║    N3             ║    N3             ║│
│  ║ ⚽ Roberto Souza  ║ ⚽ Patricia Lima  ║│
│  ║    N2             ║    N2             ║│
│  ║                   ║                   ║│
│  ║ Nível Médio: 2.8  ║ Nível Médio: 2.9  ║│
│  ║ Bal: 0.1 ✓        ║                   ║│
│  ╚═══════════════════╩═══════════════════╝│
│                                         │
│  ╔══════════════════════════════════╗   │
│  ║ [← Voltar] [Novo Sorteio]        ║   │
│  ║ [Registrar Resultado] [QR Code]  ║   │
│  ╚══════════════════════════════════╝   │
│                                         │
└─────────────────────────────────────────┘
```

#### Elementos Estruturais

| Componente | Tipo | Status | Nota |
|-----------|------|--------|------|
| Header | Minimalista | MANTER | "Resultado do Sorteio" + meta |
| Teams Grid | Exibição | REFACTOR | 2-4 cards lado a lado (premium) |
| Player List | Info | SIMPLIFICAR | Apenas nome + nível, sem stats |
| Balance Info | Stats | MANTER | Média de nível + diferença |
| Action Bar | CTA | REORGANIZAR | 4 botões claros e bem espaçados |
| Back Link | Navegação | MANTER | Voltar para home ou criar partida |

#### Elementos a REMOVER

- ❌ Nav tabs (jogadores/votação/histórico) - são para jogadores, não juiz
- ❌ Campos de input para gols/assistências - isso fica em "Registrar Resultado"
- ❌ Tabelas complexas de stats

#### Elementos a ADICIONAR

- ✅ Cards premium para cada time (gradientes, sombras)
- ✅ Visualização lado-a-lado dos times
- ✅ Indicador visual de balanceamento (checkmark se bem balanceado)
- ✅ Ações bem definidas no rodapé

---

### 4. **VOTAÇÕES** → `resultado_partida.html` (Nova Estrutura)

#### Objetivo
- Registrar resultado (gols, cartões)
- Abrir votação para jogadores
- Exibir ranking/resultados finais

#### Layout Recomendado (2 fases)

##### FASE 1: Registrar Resultado

```
┌─────────────────────────────────────────┐
│  Header: "Registrar Resultado"          │
│  [← Voltar] [Active Tab: Votações]      │
├─────────────────────────────────────────┤
│                                         │
│  Sorteio #42                            │
│                                         │
│  ╔═══════════════════╦═══════════════════╗│
│  ║    TIME 1         ║    TIME 2         ║│
│  ║                   ║                   ║│
│  ║  João Silva       ║  Pedro Costa      ║│
│  ║  [Gols] [Assists] ║  [Gols] [Assists] ║│
│  ║    0       0      ║    0       0      ║│
│  ║                   ║                   ║│
│  ║  ... (outros players)                 ║│
│  ║                   ║                   ║│
│  ║  Placar Total:    ║  Placar Total:    ║│
│  ║    [___]         ║    [___]          ║│
│  ║                   ║                   ║│
│  ║  [Vencedor: TIME] ║                   ║│
│  ╚═══════════════════╩═══════════════════╝│
│                                         │
│  ╔══════════════════════════════════╗   │
│  ║ [Voltar] [Abrir Votação →]       ║   │
│  ╚══════════════════════════════════╝   │
│                                         │
└─────────────────────────────────────────┘
```

##### FASE 2: Votação Aberta (Read-Only para Juiz)

```
┌─────────────────────────────────────────┐
│  Header: "Votação Aberta"               │
│  [← Voltar] [Active Tab: Votações]      │
├─────────────────────────────────────────┤
│                                         │
│  Sorteio #42 | Votação ID: abc123      │
│  ⏱️  Tempo restante: 5 min 32 sec       │
│                                         │
│  ╔══════════════════════════════════╗   │
│  ║ PLACAR ATUAL                     ║   │
│  ║ TIME A: 12 gols | TIME B: 8 gols ║   │
│  ╚══════════════════════════════════╝   │
│                                         │
│  ╔══════════════════════════════════╗   │
│  ║ TOP 5 VOTADOS (ATÉ AGORA)       ║   │
│  ║ 1. João Silva (12 votos)         ║   │
│  ║ 2. Pedro Costa (10 votos)        ║   │
│  ║ 3. Maria Oliveira (8 votos)      ║   │
│  ║ 4. Carlos Santos (7 votos)       ║   │
│  ║ 5. Bruno Alves (6 votos)         ║   │
│  ╚══════════════════════════════════╝   │
│                                         │
│  ╔══════════════════════════════════╗   │
│  ║ [Encerrar Votação] [Renovar]     ║   │
│  ╚══════════════════════════════════╝   │
│                                         │
└─────────────────────────────────────────┘
```

#### Elementos Estruturais

| Componente | Tipo | Status | Nota |
|-----------|------|--------|------|
| Header | Minimalista | MANTER | Contexto claro: qual seção |
| Teams Display | Info | SIMPLIFICAR | Sem input, só exibição |
| Goal Inputs | Form | MANTER | Campos de número simples |
| Vote Status | Info | ADICIONAR | Status: aberto/votando/encerrado |
| Live Ranking | Stats | ADICIONAR | Top 5 votados em tempo real |
| Action Bar | CTA | REORGANIZAR | Ações principais em destaque |

#### Elementos a REMOVER

- ❌ Nav tabs de jogadores/histórico (é seção do juiz)
- ❌ Campos de assistências/cartões inicialmente (deixar para MVP2)
- ❌ Formulário implícito (usar AJAX/fetch)
- ❌ Tabelas complexas de stats individuais

#### Elementos a ADICIONAR

- ✅ Timer visual de votação
- ✅ Real-time ranking top 5
- ✅ Status badges (Votação Aberta | Encerrada)
- ✅ Botões para Encerrar/Renovar votação

---

## 🎨 Padrões CSS e Naming

### Naming Convention - BEM Modular

```
.judge-[secao]__[elemento]--[modificador]

Exemplos:
- .judge-nav             # Navigation bar principal
- .judge-nav__tab        # Tab individual
- .judge-nav__tab--active # Tab ativa
- .judge-hero            # Hero section (ações principais)
- .judge-hero__card      # Card de ação
- .judge-hero__card--primary  # Card principal (Criar)
- .judge-hero__card--secondary # Card secundário
- .judge-info            # Info panels (última partida, etc)
- .judge-selection       # Seleção de jogadores
- .judge-selection__counter # Contador de seleção
- .judge-result          # Exibição de resultado
- .judge-result__team    # Team card
- .judge-vote            # Votação
- .judge-vote__ranking   # Ranking de votação
```

### CSS Classes to Reuse/Create

#### Novo Navigation Bar

```css
.judge-nav {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  padding: 0.5rem 0;
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--border-dark);
}

.judge-nav__tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.08), rgba(124, 58, 237, 0.04));
  border: 1px solid var(--border-dark);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: var(--transition);
  font-weight: 600;
  color: rgba(255, 255, 255, 0.72);
  text-decoration: none;
}

.judge-nav__tab:hover {
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.16), rgba(124, 58, 237, 0.08));
  border-color: var(--primary);
}

.judge-nav__tab--active {
  background: linear-gradient(135deg, var(--primary), rgba(124, 58, 237, 0.6));
  border-color: var(--primary);
  color: white;
  box-shadow: 0 8px 20px rgba(124, 58, 237, 0.3);
}

.judge-nav__icon {
  font-size: 1.5rem;
}

.judge-nav__label {
  font-size: 0.95rem;
}
```

#### Hero Cards (Ações Principais)

```css
.judge-hero {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.judge-hero__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2rem 1.5rem;
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-dark);
  cursor: pointer;
  transition: var(--transition);
  text-align: center;
  text-decoration: none;
  color: white;
  min-height: 200px;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.12), rgba(124, 58, 237, 0.06));
}

.judge-hero__card:hover {
  transform: translateY(-4px);
  border-color: var(--primary);
  box-shadow: 0 12px 30px rgba(124, 58, 237, 0.2);
}

.judge-hero__card--primary {
  background: linear-gradient(135deg, var(--primary), rgba(124, 58, 237, 0.5));
  border-color: var(--primary);
  box-shadow: 0 10px 30px rgba(124, 58, 237, 0.25);
}

.judge-hero__card--primary:hover {
  box-shadow: 0 15px 40px rgba(124, 58, 237, 0.35);
}

.judge-hero__icon {
  font-size: 3rem;
  line-height: 1;
}

.judge-hero__title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
}

.judge-hero__subtitle {
  font-size: 0.95rem;
  opacity: 0.85;
}
```

#### Compact Info Panel

```css
.judge-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.judge-info__card {
  padding: 1.5rem;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.08), rgba(124, 58, 237, 0.04));
  border: 1px solid var(--border-dark);
  border-radius: var(--radius-lg);
  border-left: 4px solid var(--primary);
}

.judge-info__label {
  display: block;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.judge-info__content {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  justify-content: space-between;
}

.judge-info__value {
  font-size: 1.75rem;
  font-weight: 700;
  color: white;
}

.judge-info__secondary {
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.72);
}
```

#### Selection Counter

```css
.judge-selection__counter {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.judge-selection__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.08), rgba(124, 58, 237, 0.04));
  border: 1px solid var(--border-dark);
  border-radius: var(--radius-lg);
  flex: 1;
  min-width: 120px;
}

.judge-selection__stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--primary);
}

.judge-selection__stat-label {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.judge-selection__stat--success {
  border-color: var(--success);
}

.judge-selection__stat--success .judge-selection__stat-value {
  color: var(--success);
}
```

---

## 🔄 Fluxo de Navegação Proposto

```
┌─ JUIZ_HOME (hub)
│
├─ [Criar Partida] → CRIAR_PARTIDA
│  ├─ [Selecionar Jogadores]
│  ├─ [Sortear] → COMPARTILHAR_TIMES
│  │  ├─ [Voltar] → JUIZ_HOME
│  │  ├─ [Novo Sorteio] → CRIAR_PARTIDA
│  │  └─ [Registrar Resultado] → VOTACOES (Fase 1)
│  └─ [Voltar] → JUIZ_HOME
│
├─ [Compartilhar] → COMPARTILHAR_TIMES (direta, última partida)
│  ├─ [Voltar] → JUIZ_HOME
│  ├─ [Novo Sorteio] → CRIAR_PARTIDA
│  └─ [Registrar Resultado] → VOTACOES (Fase 1)
│
└─ [Votações] → VOTACOES (Fase 1 ou 2 dependendo do estado)
   ├─ [Abrir Votação] → VOTACOES (Fase 2 - Live)
   ├─ [Voltar] → JUIZ_HOME
   └─ [Encerrar Votação] → Ranking final + JUIZ_HOME
```

---

## 📐 Breakpoints Responsivos

Manter os breakpoints atuais, mas adicionar refinamentos para o painel do juiz:

```css
/* Desktop: hero-card grid 3 colunas */
@media (min-width: 1024px) {
  .judge-hero {
    grid-template-columns: repeat(3, 1fr);
  }
  .judge-nav {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* Tablet: hero-card grid 2 colunas */
@media (max-width: 1023px) and (min-width: 768px) {
  .judge-hero {
    grid-template-columns: repeat(2, 1fr);
  }
  .judge-nav {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* Mobile: hero-card grid 1 coluna, stack vertical */
@media (max-width: 767px) {
  .judge-hero {
    grid-template-columns: 1fr;
  }
  .judge-nav {
    grid-template-columns: 1fr;
  }
  .judge-hero__card {
    padding: 1.5rem 1rem;
    min-height: 150px;
  }
  .judge-nav__tab {
    padding: 0.75rem 1rem;
  }
}
```

---

## 🎯 Priorização de Mudanças

### FASE 1 (MVP - Refatoração Estrutural) - 1 semana

#### P1.1: Novo Header + Navigation
- [ ] Criar `.judge-nav` e `.judge-nav__tab` CSS classes
- [ ] Refatorar `juiz_home.html`: adicionar nav bar com 3 tabs
- [ ] Atualizar `juiz_criar_partida.html`: adicionar nav bar
- [ ] Atualizar `times.html`: adicionar nav bar
- [ ] Atualizar `resultado_partida.html`: adicionar nav bar
- **Impacto**: Visual unificado em todas as páginas

#### P1.2: Simplificar JUIZ_HOME
- [ ] Remover `.judge-hero__steps` (3 cards informativos)
- [ ] Criar `.judge-hero` com 3 action cards (Criar | Compartilhar | Votações)
- [ ] Compactar "Última Partida" em card único simples
- [ ] Manter grid de jogadores (reutilizar existing)
- **Impacto**: Home fica limpa, foco absoluto nas ações

#### P1.3: Refatorar CRIAR_PARTIDA
- [ ] Renomear `.judge-selection-hero` → `.judge-selection` (semântica)
- [ ] Expandir quantity buttons (cards maiores, mais clicáveis)
- [ ] Compactar stats em badge única
- [ ] Adicionar validação visual (meta atingida)
- [ ] Botão "Sortear" só ativo se meta OK
- **Impacto**: UX mais rápida, menos confusão

#### P1.4: Refatorar TIMES (Compartilhar)
- [ ] Atualizar `.times-container` (usar premium styling)
- [ ] Remover nav tabs de jogador (não relevante)
- [ ] Simplificar exibição de times (cards lado a lado)
- [ ] Reorganizar botões de ação (bottom bar clara)
- **Impacto**: Foco em visualizar times, pronto para compartilhar

#### P1.5: Refatorar VOTAÇÃO
- [ ] Dividir em Fase 1 (Registrar) e Fase 2 (Votação Aberta)
- [ ] Remover campos desnecessários inicialmente
- [ ] Adicionar status badge (Registrando | Votação Aberta)
- [ ] Reorganizar layout de times (exibição clara)
- **Impacto**: Separação clara de responsabilidades

### FASE 2 (Refinamentos Visuais) - 1 semana

#### P2.1: Premium Cards + Gradientes
- [ ] Aplicar `.player-card--premium` padrão aos cards de ação
- [ ] Gradient backgrounds unificados
- [ ] Sombras e depth via `--shadow-md` / `--shadow-lg`
- [ ] Hover effects consistentes
- **Impacto**: Design premium em todo o painel

#### P2.2: Animações & Feedback
- [ ] Transições suaves ao trocar seções
- [ ] Pulse animation se meta atingida
- [ ] Loading states para sorteio
- [ ] Toast/toast notifications (feedback de ações)
- **Impacto**: Experiência mais polida

#### P2.3: Responsive Refinements
- [ ] Testar mobile: nav stacks, cards ficam 1 coluna
- [ ] Tablet: nav 3 colunas mantidas, cards 2 colunas
- [ ] Desktop: perfecto conforme proposto
- [ ] Ajustar padding/gap para telas pequenas
- **Impacto**: Premium em qualquer dispositivo

#### P2.4: Acessibilidade
- [ ] Labels descritivos em buttons de ação
- [ ] ARIA labels em cards
- [ ] Keyboard navigation: tab entre tabs/cards
- [ ] Focus states visíveis
- **Impacto**: Usável por todos

### FASE 3 (Integração Backend) - 2 semanas

#### P3.1: Rotas do Flask
- [ ] Validar fluxo de rotas em `juiz_routes.py`
- [ ] Adicionar endpoint para "Compartilhar Última Partida"
- [ ] Refatorar context passado para templates (remover dados desnecessários)
- **Impacto**: Backend alinhado com novo frontend

#### P3.2: Votação Real-time
- [ ] Integrar WebSocket ou polling para live ranking
- [ ] Update top 5 votados em tempo real
- [ ] Timer visual de votação
- **Impacto**: Juiz vê status em tempo real

#### P3.3: Testes
- [ ] Testes de fluxo completo (criar → sortear → votação)
- [ ] Testes responsivos (mobile/tablet/desktop)
- [ ] Testes de acessibilidade
- **Impacto**: Confiança na qualidade

---

## 🔧 Alterações Técnicas Recomendadas

### Templates (Jinja2)

#### Criar Componente Reutilizável: `_judge_nav.html`

```jinja2
{# _judge_nav.html #}
<nav class="judge-nav" role="navigation" aria-label="Painel do Juiz">
  <a href="{{ url_for('juiz.jogar_page') }}"
     class="judge-nav__tab {% if current_section == 'home' %}judge-nav__tab--active{% endif %}"
     aria-current="{% if current_section == 'home' %}page{% endif %}">
    <span class="judge-nav__icon">🎲</span>
    <span class="judge-nav__label">Criar</span>
  </a>
  <a href="{{ url_for('juiz.compartilhar_times') }}"
     class="judge-nav__tab {% if current_section == 'times' %}judge-nav__tab--active{% endif %}"
     aria-current="{% if current_section == 'times' %}page{% endif %}">
    <span class="judge-nav__icon">👥</span>
    <span class="judge-nav__label">Compartilhar</span>
  </a>
  <a href="{{ url_for('votacao.votacao_admin_page') }}"
     class="judge-nav__tab {% if current_section == 'votacao' %}judge-nav__tab--active{% endif %}"
     aria-current="{% if current_section == 'votacao' %}page{% endif %}">
    <span class="judge-nav__icon">🗳️</span>
    <span class="judge-nav__label">Votações</span>
  </a>
</nav>
```

#### Usar em Templates

```jinja2
{# juiz_home.html #}
{% include '_judge_nav.html' %}

{# Template passa current_section = 'home' ao contexto #}
```

### Backend (Flask)

#### Refatorar `juiz_routes.py`

```python
# Simplificar context para home
@juiz_bp.route('/painel')
@juiz_required
def jogar_page():
    ultima_partida = juiz_partida_service.obter_ultima_partida_resumida()
    todos_jogadores = jogador_service.listar_todos()

    # Nova chave: current_section para nav ativa
    return render_template('juiz_home.html',
                           ultima_partida=ultima_partida,
                           todos_jogadores=todos_jogadores,
                           current_section='home')

# Novo endpoint: compartilhar última partida
@juiz_bp.route('/compartilhar')
@juiz_required
def compartilhar_times():
    ultima_partida = juiz_partida_service.obter_ultima_partida_completa()
    # Retorna times.html com last match data
    return render_template('times.html',
                           sorteio=ultima_partida.sorteio,
                           current_section='times')
```

### CSS

#### Adicionar Classes Novas

```css
/* Adicionar ao final de style.css */

/* ============================================================
   JUDGE PANEL REDESIGN - Premium, Minimalista, Objetivo
   ============================================================ */

/* Navigation Bar */
.judge-nav { /* ... código acima ... */ }
.judge-nav__tab { /* ... código acima ... */ }
.judge-nav__tab--active { /* ... código acima ... */ }
.judge-nav__icon { /* ... código acima ... */ }
.judge-nav__label { /* ... código acima ... */ }

/* Hero Cards */
.judge-hero { /* ... código acima ... */ }
.judge-hero__card { /* ... código acima ... */ }
.judge-hero__card--primary { /* ... código acima ... */ }
.judge-hero__icon { /* ... código acima ... */ }
.judge-hero__title { /* ... código acima ... */ }
.judge-hero__subtitle { /* ... código acima ... */ }

/* Info Panels */
.judge-info { /* ... código acima ... */ }
.judge-info__card { /* ... código acima ... */ }
.judge-info__label { /* ... código acima ... */ }
.judge-info__content { /* ... código acima ... */ }
.judge-info__value { /* ... código acima ... */ }
.judge-info__secondary { /* ... código acima ... */ }

/* Selection */
.judge-selection__counter { /* ... código acima ... */ }
.judge-selection__stat { /* ... código acima ... */ }
.judge-selection__stat-value { /* ... código acima ... */ }
.judge-selection__stat-label { /* ... código acima ... */ }
.judge-selection__stat--success { /* ... código acima ... */ }

/* Responsive */
@media (min-width: 1024px) { /* ... código acima ... */ }
@media (max-width: 1023px) and (min-width: 768px) { /* ... código acima ... */ }
@media (max-width: 767px) { /* ... código acima ... */ }
```

---

## ✅ Checklist de Implementação

### FASE 1: Estrutura

- [ ] CSS classes criadas (`judge-nav`, `judge-hero`, etc)
- [ ] Componente `_judge_nav.html` criado e testado
- [ ] `juiz_home.html` refatorado com nav e hero cards simplificados
- [ ] `juiz_criar_partida.html` refatorado com nav
- [ ] `times.html` refatorado com nav
- [ ] `resultado_partida.html` refatorado com nav
- [ ] Todos os templates testados responsivos
- [ ] Routes atualizadas com `current_section` context

### FASE 2: Visuais

- [ ] Gradientes e sombras aplicadas aos cards
- [ ] Animações hover/focus implementadas
- [ ] Responsive breakpoints testados
- [ ] ARIA labels adicionadas
- [ ] Keyboard navigation funcionando

### FASE 3: Backend

- [ ] Endpoints validados
- [ ] Context data simplificada
- [ ] Real-time features (se aplicável)
- [ ] Testes completos

---

## 📝 Notas Finais

### Decisões Arquiteturais

1. **Separação de Responsabilidades**: Cada seção (Criar | Compartilhar | Votações) tem layout próprio, mas compartilha nav unificada
2. **Minimalismo**: Remove elementos desnecessários que distraem do fluxo principal
3. **Reusabilidade**: Componentes CSS base (`judge-*`) reutilizáveis em múltiplas seções
4. **Premium Design**: Mantém linguagem de design dos cards de jogadores (gradientes, sombras, backdrop-filter)
5. **Mobile-First**: Responsive desde o início, mantendo experience premium em qualquer tela

### Impacto Esperado

- ✅ **Velocidade**: Juiz completa fluxo em < 2 minutos (criar → sortear → votação)
- ✅ **Clareza**: Não há dúvida sobre próxima ação (3 tabs únicos no topo)
- ✅ **Premium**: Visual alinhado com resto do app
- ✅ **Acessível**: Navegável por qualquer pessoa em qualquer dispositivo

---

## 🔗 Referências

- Design System: Cores, sombras, tipografia em `style.css` (linhas 1-120)
- Player Card Premium: `.player-card--premium` (reutilizar padrões)
- Existing Routes: `/routes/juiz_routes.py`
- Templates Base: `/templates/base.html`, `_brand_header.html`

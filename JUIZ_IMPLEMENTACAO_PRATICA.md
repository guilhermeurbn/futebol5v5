# 🚀 Guia de Implementação Prática

## Arquivo 1: Componente Compartilhado `_judge_nav.html`

**Localização**: `/templates/_judge_nav.html` (CRIAR NOVO)

```jinja2
{# Navigation bar para painel do juiz - reutilizável em todas as páginas #}
<nav class="judge-nav" role="navigation" aria-label="Navegação do Painel do Juiz">
  {# Tab 1: Criar Partida #}
  <a href="{{ url_for('juiz.jogar_page') }}"
     class="judge-nav__tab {% if current_section == 'home' %}judge-nav__tab--active{% endif %}"
     {% if current_section == 'home' %}aria-current="page"{% endif %}>
    <span class="judge-nav__icon" aria-hidden="true">🎲</span>
    <span class="judge-nav__label">Criar</span>
  </a>

  {# Tab 2: Compartilhar Times #}
  <a href="{{ url_for('juiz.compartilhar_times') }}"
     class="judge-nav__tab {% if current_section == 'times' %}judge-nav__tab--active{% endif %}"
     {% if current_section == 'times' %}aria-current="page"{% endif %}>
    <span class="judge-nav__icon" aria-hidden="true">👥</span>
    <span class="judge-nav__label">Compartilhar</span>
  </a>

  {# Tab 3: Votações #}
  <a href="{{ url_for('votacao.votacao_admin_page') }}"
     class="judge-nav__tab {% if current_section == 'votacao' %}judge-nav__tab--active{% endif %}"
     {% if current_section == 'votacao' %}aria-current="page"{% endif %}>
    <span class="judge-nav__icon" aria-hidden="true">🗳️</span>
    <span class="judge-nav__label">Votações</span>
  </a>
</nav>
```

---

## Arquivo 2: CSS Classes (Adicionar ao fim de `style.css`)

**Localização**: Fim de `/static/style.css`

```css
/* ============================================================
   JUDGE PANEL REDESIGN - Premium & Minimalista
   Adicionado: [DATA]
   ============================================================ */

/* ─────────────────────────────────────────────────────────
   1. NAVIGATION BAR
   ───────────────────────────────────────────────────────── */

.judge-nav {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  padding: 0.5rem 0;
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--border-dark);
  width: 100%;
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
  outline: none;
}

.judge-nav__tab:hover {
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.16), rgba(124, 58, 237, 0.08));
  border-color: var(--primary);
  color: white;
}

.judge-nav__tab:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.judge-nav__tab--active {
  background: linear-gradient(135deg, var(--primary), rgba(124, 58, 237, 0.6));
  border-color: var(--primary);
  color: white;
  box-shadow: 0 8px 20px rgba(124, 58, 237, 0.3);
}

.judge-nav__icon {
  font-size: 1.5rem;
  line-height: 1;
}

.judge-nav__label {
  font-size: 0.95rem;
  letter-spacing: 0.02em;
}

/* ─────────────────────────────────────────────────────────
   2. HERO CARDS (Ações Principais)
   ───────────────────────────────────────────────────────── */

.judge-hero {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
  width: 100%;
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
  position: relative;
  overflow: hidden;
}

.judge-hero__card::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(124, 58, 237, 0.1), transparent);
  border-radius: 50%;
  pointer-events: none;
}

.judge-hero__card:hover {
  transform: translateY(-4px);
  border-color: var(--primary);
  box-shadow: 0 12px 30px rgba(124, 58, 237, 0.2);
}

.judge-hero__card:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.judge-hero__card--primary {
  background: linear-gradient(135deg, var(--primary), rgba(124, 58, 237, 0.5));
  border-color: var(--primary);
  box-shadow: 0 10px 30px rgba(124, 58, 237, 0.25);
}

.judge-hero__card--primary:hover {
  box-shadow: 0 15px 40px rgba(124, 58, 237, 0.35);
  transform: translateY(-6px);
}

.judge-hero__card--secondary {
  background: linear-gradient(135deg, rgba(236, 72, 153, 0.12), rgba(236, 72, 153, 0.06));
  border-color: rgba(236, 72, 153, 0.3);
}

.judge-hero__card--secondary:hover {
  border-color: var(--secondary);
  box-shadow: 0 12px 30px rgba(236, 72, 153, 0.15);
}

.judge-hero__icon {
  font-size: 3rem;
  line-height: 1;
  position: relative;
  z-index: 1;
}

.judge-hero__title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
  position: relative;
  z-index: 1;
  letter-spacing: -0.01em;
}

.judge-hero__subtitle {
  font-size: 0.95rem;
  opacity: 0.85;
  position: relative;
  z-index: 1;
  margin: 0;
}

/* ─────────────────────────────────────────────────────────
   3. INFO PANELS (Última Partida, Status, etc)
   ───────────────────────────────────────────────────────── */

.judge-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
  width: 100%;
}

.judge-info__card {
  padding: 1.5rem;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.08), rgba(124, 58, 237, 0.04));
  border: 1px solid var(--border-dark);
  border-radius: var(--radius-lg);
  border-left: 4px solid var(--primary);
  transition: var(--transition);
}

.judge-info__card:hover {
  border-color: var(--primary);
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.12), rgba(124, 58, 237, 0.08));
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
  flex-wrap: wrap;
}

.judge-info__value {
  font-size: 1.75rem;
  font-weight: 700;
  color: white;
  line-height: 1.2;
}

.judge-info__secondary {
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.72);
}

/* ─────────────────────────────────────────────────────────
   4. SELECTION COUNTER (Criar Partida)
   ───────────────────────────────────────────────────────── */

.judge-selection__counter {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
  width: 100%;
}

.judge-selection__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.08), rgba(124, 58, 237, 0.04));
  border: 1px solid var(--border-dark);
  border-radius: var(--radius-lg);
  transition: var(--transition);
}

.judge-selection__stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--primary);
  line-height: 1;
}

.judge-selection__stat-label {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: center;
}

.judge-selection__stat--success {
  border-color: var(--success);
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(16, 185, 129, 0.04));
}

.judge-selection__stat--success .judge-selection__stat-value {
  color: var(--success);
}

.judge-selection__stat--warning {
  border-color: var(--warning);
  background: linear-gradient(135deg, rgba(249, 115, 22, 0.12), rgba(249, 115, 22, 0.04));
}

.judge-selection__stat--warning .judge-selection__stat-value {
  color: var(--warning);
}

/* ─────────────────────────────────────────────────────────
   5. RESPONSIVE DESIGN
   ───────────────────────────────────────────────────────── */

@media (min-width: 1024px) {
  .judge-hero {
    grid-template-columns: repeat(3, 1fr);
  }

  .judge-nav {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1023px) and (min-width: 768px) {
  .judge-hero {
    grid-template-columns: repeat(2, 1fr);
  }

  .judge-nav {
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
  }

  .judge-hero__card {
    padding: 1.5rem 1.25rem;
    min-height: 180px;
  }

  .judge-hero__icon {
    font-size: 2.5rem;
  }

  .judge-hero__title {
    font-size: 1.1rem;
  }
}

@media (max-width: 767px) {
  .judge-hero {
    grid-template-columns: 1fr;
  }

  .judge-nav {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .judge-nav__tab {
    padding: 0.75rem 1rem;
  }

  .judge-nav__icon {
    font-size: 1.25rem;
  }

  .judge-nav__label {
    font-size: 0.85rem;
  }

  .judge-hero__card {
    padding: 1.5rem 1rem;
    min-height: 150px;
    gap: 0.75rem;
  }

  .judge-hero__icon {
    font-size: 2.5rem;
  }

  .judge-hero__title {
    font-size: 1.1rem;
  }

  .judge-selection__counter {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .judge-info {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }
}

@media (max-width: 480px) {
  .judge-hero__card {
    padding: 1.25rem 0.75rem;
    min-height: 130px;
  }

  .judge-hero__icon {
    font-size: 2rem;
  }

  .judge-hero__title {
    font-size: 1rem;
  }

  .judge-info__value {
    font-size: 1.5rem;
  }
}
```

---

## Arquivo 3: Atualizar `juiz_home.html`

**Localização**: `/templates/juiz_home.html`

### Mudanças:

1. **Adicionar nav bar** logo após o header
2. **Simplificar hero section** (remover steps)
3. **Compactar última partida**

```jinja2
{% extends 'base.html' %}

{% block title %}Painel do Juiz{% endblock %}

{% block content %}
<div class="container page-container-wide">
    <header class="header">
        <div class="header-content">
            {% set brand_title = 'Painel do Juiz' %}
            {# Remover: brand_subtitle - apenas deixar o título #}
            {% include '_brand_header.html' %}
        </div>
    </header>

    <main class="main">

        {# NOVO: Navigation bar #}
        {% set current_section = 'home' %}
        {% include '_judge_nav.html' %}

        {# SEÇÃO 1: AÇÕES PRINCIPAIS (NOVO LAYOUT) #}
        <section class="section" style="margin-bottom: 2rem;">
            <div class="judge-hero">

                {# Card 1: Criar Partida #}
                <form method="post" action="{{ url_for('juiz.juiz_criar_partida') }}" class="judge-hero__card judge-hero__card--primary" style="border: none; text-decoration: none;">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <div class="judge-hero__icon">🎲</div>
                    <div class="judge-hero__title">Criar Partida</div>
                    <div class="judge-hero__subtitle">Selecione jogadores e sorteie times</div>
                    <button type="submit" class="btn btn-primary" style="width: auto; margin-top: 0.5rem;">Começar</button>
                </form>

                {# Card 2: Compartilhar Times #}
                <a href="{{ url_for('juiz.compartilhar_times') }}" class="judge-hero__card judge-hero__card--secondary" style="text-decoration: none;">
                    <div class="judge-hero__icon">👥</div>
                    <div class="judge-hero__title">Compartilhar Times</div>
                    <div class="judge-hero__subtitle">Visualize a última rodada</div>
                    <span class="btn btn-secondary" style="width: auto; margin-top: 0.5rem;">Ver</span>
                </a>

                {# Card 3: Votações #}
                <a href="{{ url_for('votacao.votacao_admin_page') }}" class="judge-hero__card judge-hero__card--secondary" style="text-decoration: none;">
                    <div class="judge-hero__icon">🗳️</div>
                    <div class="judge-hero__title">Votações</div>
                    <div class="judge-hero__subtitle">Abra votação e veja ranking</div>
                    <span class="btn btn-secondary" style="width: auto; margin-top: 0.5rem;">Abrir</span>
                </a>

            </div>
        </section>

        {# SEÇÃO 2: ÚLTIMA PARTIDA (COMPACTADA) #}
        {% if ultima_partida %}
        <section class="section" style="margin-bottom: 2rem;">
            <div class="judge-info">
                <div class="judge-info__card">
                    <div class="judge-info__label">Última Rodada</div>
                    <div class="judge-info__content">
                        <div>
                            <div class="judge-info__value">{{ ultima_partida.titulo or 'Partida' }}</div>
                            <div class="judge-info__secondary">Sorteio #{{ ultima_partida.sorteio_id or 'N/A' }}</div>
                        </div>
                    </div>
                </div>

                {% if ultima_partida.resultado_resumido %}
                <div class="judge-info__card">
                    <div class="judge-info__label">Placar</div>
                    <div class="judge-info__content">
                        {% for time in ultima_partida.resultado_resumido %}
                            <div>
                                <div class="judge-info__value">{{ time.gols }}</div>
                                <div class="judge-info__secondary">Time {{ time.time_numero }}</div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}

                {% if ultima_partida.melhor_jogador %}
                <div class="judge-info__card">
                    <div class="judge-info__label">Melhor Jogador</div>
                    <div class="judge-info__content">
                        <div>
                            <div class="judge-info__value">{{ ultima_partida.melhor_jogador.jogador_nome }}</div>
                            <div class="judge-info__secondary">{{ ultima_partida.total_votos }} votos</div>
                        </div>
                    </div>
                </div>
                {% endif %}
            </div>
        </section>
        {% endif %}

        {# SEÇÃO 3: ELENCO (MANTER) #}
        <section class="section">
            <div class="section-header judge-section-header">
                <div>
                    <h2 class="section-title">👥 Perfis dos Jogadores</h2>
                    <p class="section-subtitle">Visualize todos os jogadores disponíveis para a próxima partida.</p>
                </div>
                <span class="badge badge-primary">{{ total_jogadores }} cadastrados</span>
            </div>

            {% if todos_jogadores %}
            <div class="players-grid judge-players-grid">
                {% for jogador in todos_jogadores %}
                <a class="player-card player-card--premium judge-player-card" href="{{ url_for('jogador.perfil_jogador_publico', jogador_id=jogador.id) }}" aria-label="Ver perfil de {{ jogador.nome }}">
                    <img class="player-card__bg" src="{{ jogador.foto_url or url_for('static', filename='foto_card_jogador.jpeg') }}" alt="" aria-hidden="true">
                    <div class="player-card__surface judge-player-card__surface">
                        <div class="player-card__top judge-player-card__top">
                            <div class="player-card__avatar-shell">
                                <div class="player-card__avatar" aria-hidden="true">{{ jogador.nome[:2]|upper }}</div>
                            </div>
                        </div>

                        <div class="player-card__content">
                            <div class="player-card__identity">
                                <div class="player-card__identity-row">
                                    <h3 class="player-card__name">{{ jogador.nome }}</h3>
                                    <span class="player-card__level-badge">Nível {{ jogador.nivel }}</span>
                                </div>
                                <div class="player-card__tags">
                                    <span class="player-card__tag {% if jogador.posicao != 'goleiro' %}player-card__tag--ghost{% endif %}">
                                        {% if jogador.posicao == 'goleiro' %}🧤 Goleiro{% else %}⚽ Linha{% endif %}
                                    </span>
                                    <span class="player-card__tag player-card__tag--ghost">
                                        {% if jogador.tipo == 'fixo' %}⭐ Fixo{% else %}👤 Avulso{% endif %}
                                    </span>
                                </div>
                            </div>

                            <div class="player-card__stats judge-player-card__stats">
                                <div class="player-card__stat">
                                    <span class="player-card__stat-value">{{ jogador.nivel }}</span>
                                    <span class="player-card__stat-label">Nível</span>
                                </div>
                                <div class="player-card__stat">
                                    <span class="player-card__stat-value">{{ 'G' if jogador.posicao == 'goleiro' else 'L' }}</span>
                                    <span class="player-card__stat-label">Perfil</span>
                                </div>
                            </div>

                            <div class="player-card__actions judge-player-card__actions">
                                <span class="btn btn-primary btn-large player-card__cta">Ver perfil</span>
                            </div>
                        </div>
                    </div>
                </a>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-state">
                <div class="empty-icon">👥</div>
                <p>Nenhum jogador cadastrado ainda.</p>
            </div>
            {% endif %}
        </section>

    </main>
</div>
{% endblock %}
```

---

## Arquivo 4: Backend - Atualizar Routes

**Localização**: `/routes/juiz_routes.py`

### Mudanças mínimas:

```python
# Já existente - adicionar current_section
@juiz_bp.route('/painel')
@juiz_required
def jogar_page():
    ultima_partida = juiz_partida_service.obter_ultima_partida_resumida()
    todos_jogadores = jogador_service.listar_todos()
    total_jogadores = len(todos_jogadores)

    return render_template('juiz_home.html',
                           ultima_partida=ultima_partida,
                           todos_jogadores=todos_jogadores,
                           total_jogadores=total_jogadores,
                           current_section='home')  # ADICIONAR ESTA LINHA


# NOVO ENDPOINT: Compartilhar Times (atalho para última partida)
@juiz_bp.route('/compartilhar')
@juiz_required
def compartilhar_times():
    ultima_partida = juiz_partida_service.obter_ultima_partida_completa()

    if not ultima_partida or not ultima_partida.get('sorteio'):
        return redirect(url_for('juiz.jogar_page'))

    sorteio = ultima_partida['sorteio']
    num_times = len(sorteio.get('times', []))

    return render_template('times.html',
                           sorteio=sorteio,
                           num_times=num_times,
                           current_section='times')


# Já existente - adicionar current_section
@juiz_bp.route('/criar_partida', methods=['GET', 'POST'])
@juiz_required
def juiz_criar_partida():
    # ... código existente ...
    return render_template('juiz_criar_partida.html',
                           todos_jogadores=todos_jogadores,
                           total_jogadores=total_jogadores,
                           total_presentes=total_presentes,
                           current_section='home')  # ADICIONAR
```

---

## Testando a Implementação

### 1. Testar Navigation Bar

```bash
# Acessar home
http://localhost:5000/painel

# Verificar:
- [ ] 3 tabs visíveis (Criar | Compartilhar | Votações)
- [ ] Tab "home" está ativa (destaque visual)
- [ ] Clicando em "Compartilhar" vai para /compartilhar
- [ ] Clicando em "Votações" vai para votação
- [ ] CSS classes aplicadas (.judge-nav, .judge-nav__tab--active)
```

### 2. Testar Hero Cards

```bash
# Verificar em http://localhost:5000/painel
- [ ] 3 cards grandes visíveis (Criar | Compartilhar | Votações)
- [ ] Card "Criar" tem gradiente principal (roxo)
- [ ] Cards têm ícones visíveis
- [ ] Hover effect funciona (levanta card + brilho)
- [ ] Textos legíveis em mobile
```

### 3. Testar Responsivo

```bash
# Testar em DevTools (F12 > Responsive Mode):

Mobile (375px):
- [ ] Nav stacks em 1 coluna
- [ ] Hero cards stacked (1 coluna)
- [ ] Texto legível

Tablet (768px):
- [ ] Nav 3 colunas
- [ ] Hero cards 2 colunas
- [ ] Espaçamento balanceado

Desktop (1280px):
- [ ] Nav 3 colunas (perfeito)
- [ ] Hero cards 3 colunas (perfeito)
- [ ] Espaçamento generoso
```

### 4. Testar Acessibilidade

```bash
# Keyboard navigation (Tab):
- [ ] Consegue tab através dos 3 tabs
- [ ] Consegue enter para ativar
- [ ] Focus state visível (outline roxo)

# Screen reader (NVDA/JAWS):
- [ ] "Navegação do Painel do Juiz" - lê label
- [ ] "Criar, tab ativo" - lê estado ativo
- [ ] "Criar Partida, botão" - lê componente
```

---

## Ordem de Implementação Recomendada

### Dia 1 (Morning - 2h):

```
1. Copiar código de _judge_nav.html
2. Adicionar CSS classes ao style.css
3. Adicionar {% include '_judge_nav.html' %} em juiz_home.html
4. Adicionar current_section='home' em juiz_routes.py
5. Testar: nav bar aparece + está ativa
```

### Dia 1 (Afternoon - 2h):

```
6. Adicionar hero cards em juiz_home.html (remover steps)
7. Compactar última partida em judge-info cards
8. Testar: hero cards aparecem, compactação funciona
```

### Dia 2 (Morning - 2h):

```
9. Adicionar {% include '_judge_nav.html' %} em juiz_criar_partida.html
10. Adicionar current_section='criar' em rota
11. Adicionar em times.html + resultado_partida.html
12. Testar: nav bar em todas as páginas
```

### Dia 2 (Afternoon - 2h):

```
13. Testar responsivo (mobile/tablet/desktop)
14. Ajustar media queries conforme necessário
15. Testar acessibilidade (keyboard + screen reader)
16. Deploy!
```

---

## Troubleshooting

### Problema: Nav bar aparece mas texto fica invisível

**Solução**: Verificar se `color: white` está sendo aplicado. Adicionar `!important` se necessário:

```css
.judge-nav__label {
  color: white !important;
}
```

### Problema: Hero cards não formam grid 3 colunas

**Solução**: Verificar se CSS foi adicionado ao final de style.css corretamente:

```bash
grep -n "JUDGE PANEL REDESIGN" static/style.css
# Deve retornar a linha onde a seção foi adicionada
```

### Problema: current_section não é reconhecido no template

**Solução**: Verificar se foi passado no render_template:

```python
# ERRADO:
return render_template('juiz_home.html', ...)

# CORRETO:
return render_template('juiz_home.html',
                       current_section='home',
                       ...)
```

---

## Next Steps

Após completar a implementação:

1. **Teste completo** em produção
2. **Feedback do juiz** (UX real)
3. **Iteração**: ajustar cores, espaçamento, etc.
4. **Documenter mudanças** no README.md

---

## Arquivos a Modificar (Summary)

| Arquivo | Tipo | Ação |
|---------|------|------|
| `/templates/_judge_nav.html` | CRIAR | Novo componente |
| `/static/style.css` | EDIT | Adicionar classes ao final |
| `/templates/juiz_home.html` | EDIT | Adicionar nav + hero cards |
| `/templates/juiz_criar_partida.html` | EDIT | Adicionar nav + current_section |
| `/templates/times.html` | EDIT | Adicionar nav + current_section |
| `/templates/resultado_partida.html` | EDIT | Adicionar nav + current_section |
| `/routes/juiz_routes.py` | EDIT | Adicionar current_section + novo endpoint |

**Total de mudanças**: ~7 arquivos
**Linhas adicionadas**: ~300 (CSS + HTML + Python)
**Tempo estimado**: 6-8 horas (incluindo testes)

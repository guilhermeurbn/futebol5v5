# Design System da Area do Juiz

Este arquivo e a referencia visual oficial das telas:

- Criar
- Times
- Compartilhar
- Votacoes
- Historico

Antes de criar ou alterar qualquer componente da area do juiz, consulte este
documento e o bloco `Judge workspace: shared visual language` em
`static/style.css`.

## Regra principal

Toda pagina do juiz deve usar a classe raiz:

```html
<div class="container page-container-wide judge-workspace-page">
```

Os estilos devem ficar limitados por `.judge-workspace-page` para nao afetar
outras areas do site.

## Tokens oficiais

```css
.judge-workspace-page {
  /* Superficies */
  --judge-surface: rgba(18, 15, 25, 0.94);
  --judge-surface-raised: rgba(30, 24, 40, 0.86);
  --judge-surface-soft: rgba(255, 255, 255, 0.035);

  /* Bordas */
  --judge-border: rgba(167, 139, 250, 0.2);
  --judge-border-strong: rgba(34, 197, 94, 0.38);

  /* Texto */
  --judge-text: #f4f1f8;
  --judge-muted: #aaa3b5;

  /* Cores de marca */
  --judge-green: #22c55e;
  --judge-purple: #8b5cf6;
  --judge-pink: #ec4899;
}
```

## Paleta

| Uso | Cor |
| --- | --- |
| Fundo principal | `#000000` |
| Superficie principal | `rgba(18, 15, 25, 0.94)` |
| Superficie elevada | `rgba(30, 24, 40, 0.86)` |
| Texto principal | `#f4f1f8` |
| Texto secundario | `#aaa3b5` |
| Verde, selecao e sucesso | `#22c55e` |
| Roxo, navegacao e destaque | `#8b5cf6` |
| Rosa, apoio de gradiente | `#ec4899` |
| Amarelo, pendente | `#f8d58b` |
| Vermelho, acao destrutiva | `#ef4444` |

Nao introduza uma nova cor sem uma necessidade funcional clara.

## Gradientes oficiais

Fundo da pagina:

```css
background:
  radial-gradient(circle at 12% 8%, rgba(34, 197, 94, 0.09), transparent 28rem),
  radial-gradient(circle at 88% 14%, rgba(139, 92, 246, 0.11), transparent 27rem),
  #000;
```

Card principal:

```css
background:
  radial-gradient(circle at top left, rgba(34, 197, 94, 0.07), transparent 34%),
  radial-gradient(circle at top right, rgba(236, 72, 153, 0.06), transparent 30%),
  linear-gradient(155deg, rgba(255, 255, 255, 0.025), transparent 45%),
  var(--judge-surface);
```

Botao primario e barra de progresso:

```css
background: linear-gradient(
  135deg,
  var(--judge-green) 0%,
  var(--judge-purple) 58%,
  var(--judge-pink) 100%
);
```

## Componentes oficiais

Use estas classes antes de criar componentes novos:

| Componente | Classe |
| --- | --- |
| Raiz da pagina | `.judge-workspace-page` |
| Navegacao | `.judge-nav-shell`, `.judge-nav`, `.judge-nav__tab` |
| Introducao | `.judge-flow-intro` |
| Introducao compacta | `.judge-flow-intro--compact` |
| Card principal | `.judge-flow-card` |
| Rotulo superior | `.judge-flow-kicker` |
| Badge de estado | `.judge-flow-status` |
| Botao principal | `.btn.btn-primary` dentro de `.judge-workspace-page` |
| Historico compacto | `.judge-draw-history`, `.judge-draw-history__item` |

Exemplo:

```html
<section class="judge-flow-intro judge-flow-intro--compact">
  <span class="judge-flow-kicker">Criar partida</span>
  <h1>Titulo da etapa</h1>
  <p>Explique a proxima acao de forma curta.</p>
</section>

<section class="judge-flow-card">
  <h2>Titulo do card</h2>
  <p>Conteudo da etapa.</p>
  <button class="btn btn-primary" type="button">Continuar</button>
</section>
```

## Estados

| Estado | Classe | Cor |
| --- | --- | --- |
| Pendente | `.is-pending` | Amarelo |
| Bloqueado | `.is-locked` | Cinza |
| Disponivel | `.is-available` | Roxo |
| Ativo | `.is-active` | Verde |
| Concluido | `.is-complete` | Verde |

Exemplo:

```html
<span class="judge-flow-status is-pending">Pendente</span>
<span class="judge-flow-status is-locked">Bloqueada</span>
<span class="judge-flow-status is-available">Disponivel</span>
<span class="judge-flow-status is-active">Aberta</span>
<span class="judge-flow-status is-complete">Concluida</span>
```

Nunca use verde para um estado pendente ou bloqueado.

## Tipografia

- Titulo da pagina: `clamp(1.75rem, 4vw, 2.7rem)`.
- Titulo de card: texto solido, sem gradiente.
- Texto principal: `var(--judge-text)`.
- Texto de apoio: `var(--judge-muted)`.
- Kicker: pequeno, uppercase e verde suave.
- Titulos usam `letter-spacing: -0.035em`.

## Forma e espacamento

- Largura maxima do conteudo: `1180px`.
- Card principal: raio de `22px`.
- Card interno: raio entre `13px` e `16px`.
- Navegacao: raio de `18px`.
- Espaco entre cards: `16px`.
- Padding principal: `clamp(1.15rem, 2.5vw, 2rem)`.
- Altura minima de controles importantes: `48px`.

## Responsividade

O breakpoint estrutural da area do juiz e `700px`.

Abaixo dele:

- grids passam para uma coluna;
- botoes principais ocupam toda a largura quando necessario;
- o conteudo usa padding de `1rem`;
- cards usam raio de `18px`;
- a navegacao continua com as cinco opcoes visiveis.

## O que evitar

- Estilos globais sem o prefixo `.judge-workspace-page`.
- Novos gradientes ou cores para componentes equivalentes.
- Titulos em gradiente apenas em uma das tres telas.
- Badges verdes para estados pendentes ou bloqueados.
- Misturar os componentes globais `.section-*` com a familia `.judge-flow-*`.
- Alterar cores diretamente no template com `style=""`.

## Arquivos relacionados

- `static/style.css`
- `templates/_judge_nav.html`
- `templates/juiz_home.html`
- `templates/juiz_criar_partida.html`
- `templates/juiz_times.html`
- `templates/juiz_compartilhar.html`
- `templates/votacao_admin.html`
- `templates/juiz_historico.html`

Ao alterar os tokens, atualize este documento e o CSS no mesmo commit.

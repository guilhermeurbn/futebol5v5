# 🎨 Design System - NaTrave

## Visão Geral
O design system foi completamente refatorado em **Abril de 2026** para ser mais elegante, acessível e fácil de manter.

### Benefícios
- ✨ **Elegante**: Gradientes suaves, cores vibrantes, tipografia moderna
- 🎯 **Acessível**: Contraste adequado, focus states, navegação por teclado
- 📱 **Responsivo**: Mobile-first, funciona em todos os dispositivos
- 🛠️ **Fácil Manutenção**: 60 variáveis CSS reutilizáveis, estrutura lógica
- 🌙 **Dark Mode**: Suporte automático para preferências do usuário

---

## 🎭 Variáveis CSS

### Paleta de Cores
```css
--primary: #7c3aed;          /* Roxo vibrante (principal) */
--secondary: #ec4899;        /* Rosa intenso */
--accent: #06b6d4;           /* Cyan/Turquesa */
--success: #10b981;          /* Verde */
--warning: #f97316;          /* Laranja */
--danger: #ef4444;           /* Vermelho */
```

### Espaçamento (Base 8px)
```css
--spacing-xs: 0.25rem;   /* 4px */
--spacing-sm: 0.5rem;    /* 8px */
--spacing-md: 1rem;      /* 16px */
--spacing-lg: 1.5rem;    /* 24px */
--spacing-xl: 2rem;      /* 32px */
--spacing-2xl: 2.5rem;   /* 40px */
--spacing-3xl: 3rem;     /* 48px */
```

### Border Radius
```css
--radius-sm: 4px;
--radius: 8px;            /* Padrão */
--radius-lg: 12px;        /* Cards, sections */
--radius-xl: 16px;        /* Logo */
--radius-full: 9999px;    /* Badges */
```

### Sombras (Profundidade)
```css
--shadow: 0 2px 8px rgba(...);      /* Leve */
--shadow-md: 0 4px 12px rgba(...);  /* Média */
--shadow-lg: 0 10px 25px rgba(...); /* Grande */
--shadow-xl: 0 20px 40px rgba(...); /* Muito Grande */
--shadow-2xl: 0 25px 50px rgba(...);/* Maior */
```

---

## 🎯 Componentes Principais

### Botões
```html
<!-- Primário (recomendado) -->
<button class="btn btn-primary">Clique aqui</button>

<!-- Variações -->
<button class="btn btn-secondary">Secundário</button>
<button class="btn btn-success">Sucesso</button>
<button class="btn btn-danger">Perigo</button>
<button class="btn btn-warning">Aviso</button>
<button class="btn btn-outline">Outline</button>

<!-- Tamanhos -->
<button class="btn btn-large">Grande</button>
<button class="btn btn-small">Pequeno</button>
```

### Seções
```html
<section class="section">
    <h2 class="section-title">Título da Seção</h2>
    <p class="section-subtitle">Subtítulo opcional</p>
    <!-- Conteúdo -->
</section>
```

### Formulários
```html
<div class="form-group">
    <label class="form-label">Seu Label</label>
    <input class="form-input" type="text" placeholder="Digite...">
</div>

<!-- Seletor de Nível -->
<div class="level-selector">
    <div class="level-buttons">
        <button class="level-btn" data-nivel="1">1</button>
        <button class="level-btn" data-nivel="5" data-active>5</button>
        <button class="level-btn" data-nivel="10">10</button>
    </div>
</div>
```

### Cards
```html
<div class="card">
    <h3>Título do Card</h3>
    <p>Conteúdo aqui</p>
</div>

<!-- Card de Jogador -->
<div class="player-card">
    <div class="player-header">
        <div class="player-info">
            <p class="player-name">João Silva</p>
            <p class="player-tipo">Fixo</p>
        </div>
        <div class="player-level-badge">⭐ Nível 7</div>
    </div>
    <div class="player-level-bar">
        <div class="player-level-fill" style="width: 70%;"></div>
    </div>
    <div class="player-actions">
        <button class="btn btn-small btn-primary">Editar</button>
        <button class="btn btn-small btn-danger">Deletar</button>
    </div>
</div>
```

### Stats
```html
<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-label">Total de Jogadores</div>
        <div class="stat-value">24</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Times Criados</div>
        <div class="stat-value">12</div>
    </div>
</div>
```

### Alertas
```html
<div class="alert alert-success">✅ Operação concluída!</div>
<div class="alert alert-warning">⚠️ Atenção necessária</div>
<div class="alert alert-danger">❌ Erro!</div>
<div class="alert alert-info">ℹ️ Informação</div>
```

### Modais
```html
<div class="modal active">
    <div class="modal-content">
        <div class="modal-header">
            <h2>Título do Modal</h2>
            <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
            <p>Conteúdo aqui</p>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary">Cancelar</button>
            <button class="btn btn-primary">Confirmar</button>
        </div>
    </div>
</div>
```

---

## 📱 Responsividade

### Breakpoints
- **Desktop**: > 1024px
- **Tablet**: 768px - 1024px
- **Mobile**: < 768px
- **Mobile Pequeno**: < 480px

### Exemplo de Uso
```css
@media (max-width: 768px) {
    .my-component {
        padding: 1rem;
    }
}
```

---

## 🌙 Dark Mode

O dark mode é automático baseado em `prefers-color-scheme: dark`

```css
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #1a1a1a;
        --text: #e0e0e0;
        /* ... mais variáveis ... */
    }
}
```

---

## ✨ Animações

### Transições
```css
--transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);      /* Padrão */
--transition-fast: all 0.15s ease-out;                     /* Rápida */
--transition-slow: all 0.5s ease-out;                      /* Lenta */
```

### Keyframes Disponíveis
- `float`: Animação flutuante (usado no header)
- `fadeIn`: Desvanecimento de entrada
- `slideIn`: Deslizamento de entrada

---

## 🛠️ Como Estender

### Adicionar Nova Cor
```css
:root {
    --custom-color: #your-hex-code;
}

.btn-custom {
    background: linear-gradient(135deg, var(--custom-color) 0%, #darker-shade 100%);
    color: white;
}
```

### Criar Novo Componente
```css
.my-new-component {
    padding: var(--spacing-lg);
    border-radius: var(--radius-lg);
    background: linear-gradient(135deg, #ffffff 0%, #fafafa 100%);
    box-shadow: var(--shadow-md);
    transition: var(--transition);
}

.my-new-component:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
}
```

---

## 🎯 Best Practices

1. **Use Variáveis CSS**: Nunca hardcode cores, espaçamentos, etc.
2. **Mobile First**: Estile para mobile, depois adicione media queries
3. **Acessibilidade**: Sempre use labels com inputs, focus states, contraste
4. **Sem Estilos Inline**: Use classes CSS ao invés de `style=`
5. **Consistência**: Mantenha o mesmo padrão em todos os templates
6. **Gradientes**: Use os gradientes primários para elementos importantes
7. **Sombras**: Use `--shadow-*` para profundidade, nunca hard-code

---

## 📚 Referência Rápida

| Elemento | Classe | Uso |
|----------|--------|-----|
| Botão Principal | `.btn .btn-primary` | Ações principais |
| Botão Perigo | `.btn .btn-danger` | Deletar, logout |
| Alerta | `.alert .alert-success` | Feedback positivo |
| Seção | `.section` | Contenedor principal |
| Card | `.card` | Container genérico |
| Stat | `.stat-card` | Estatísticas |
| Form Group | `.form-group` | Agrupamento de inputs |
| Grid | `.players-grid` | Layout com cards |

---

## 🐛 Suporte

Para problemas com o design system:
1. Verifique se está usando as classes CSS corretas
2. Verifique as variáveis CSS em `:root`
3. Teste em dispositivos diferentes
4. Verifique o console do browser para erros

**Última atualização**: Abril 2026

# 🎯 Sistema de Seleção de Jogadores

## O que é?

Um novo fluxo profissional para gerenciar jogadores em um único "dia de jogo":

### ✨ Novo Fluxo de Uso

```
1. CADASTRO (permanente)
   ↓
   Adicionar jogadores (Fixos ou Avulsos)
   ↓
2. SELEÇÃO (antes de cada jogo)
   ↓
   Selecionar apenas quem está PRESENTE
   ↓
3. SORTEIO (durante o jogo)
   ↓
   Balancear os selecionados em times
```

---

## 📊 Conceitos

### Tipos de Jogadores

**⭐ FIXOS**
- Jogam com frequência/regularidade
- Sempre na lista
- Opção padrão para jogadores comprometidos

**👤 AVULSOS**
- Jogadores ocasionais/pontuais
- Aparecem eventualmente
- Ótimo para novatos ou temporários

### Estados

**TODOS** (no banco de dados)
- Todos os 50, 100, etc. jogadores cadastrados
- Vistos na página inicial

**PRESENTES** (selecionados)
- Apenas os 10, 15 ou 20 do dia
- Usados para o sorteio

---

## 🔄 Passo a Passo

### 1️⃣ Página Inicial - Cadastro

```
[Adicionar Jogador]
├─ Nome
├─ Nível (1-10)
└─ Tipo: ⭐ Fixo ou 👤 Avulso

👥 Jogadores Cadastrados
├─ João (⭐ Fixo, Nível 8)
├─ Maria (👤 Avulso, Nível 6)
├─ ...
└─ [👥 Selecionar Jogadores para o Jogo]
```

### 2️⃣ Página de Seleção - Escolher Presentes

```
📊 Estatísticas
├─ Total Disponível: 45
├─ Selecionados: 0
└─ Necessários: 10, 15 ou 20

📊 Quantos Jogadores?
├─ [🔟 10 Jogadores] (5v5)
├─ [1️⃣5️⃣ 15 Jogadores] (5v5 + 5 banco)
└─ [2️⃣0️⃣ 20 Jogadores] (5v5 + 10 banco)

ABAS:
├─ ⭐ Fixos (15)
├─ 👤 Avulsos (30)
└─ 👥 Todos (45)

LISTA DE SELEÇÃO:
☐ João (⭐, Nível 8)
☑ Maria (👤, Nível 6)  ✓ Selecionada
☐ Pedro (⭐, Nível 7)
...

[🗑️ Limpar] [✓ Selecionar e Sortear]
```

### 3️⃣ Página de Times - Sorteio

```
⚽ Resultado do Sorteio

📊 Estatísticas
├─ Diferença: 3 pts
├─ Favorito: Time 1
└─ Total: 20 jogadores

⚽ TIME 1 (38 pts)     ⚽ TIME 2 (35 pts)
├─ 1. João (8)         ├─ 1. Maria (6)
├─ 2. Pedro (7)        ├─ 2. Ana (7)
├─ ...                 ├─ ...
└─ 5 jogadores         └─ 5 jogadores

[← Voltar] [🎲 Novo Sorteio]
```

---

## 🎮 Interatividade

### Botões de Quantidade

```
[🔟 10]  [1️⃣5️⃣ 15]  [2️⃣0️⃣ 20]
  ↓
Clica em um → marca como "ativo" em azul
↓
O sistema permite selecionar EXATAMENTE esse número
↓
Não deixa confirmar com número errado
```

### Abas de Filtro

```
[⭐ Fixos] [👤 Avulsos] [👥 Todos]
    ↓
Clica → mostra apenas jogadores daquele tipo
    ↓
Todos os checkboxes continuam funcionando
```

### Sincronização de Seleção

```
Marque um jogador:
☐ → Checkbox marcado ✓
   → Contador aumenta
   → Botão "Selecionar" fica disponível (se atingiu quantidade)

Desmarque:
☑ → Checkbox desmarcado ☐
   → Contador diminui
```

---

## 📊 Estatísticas em Tempo Real

```
Total Disponível     →  Todos os cadastrados (somado)
Selecionados         →  Checkboxes marcados (agora)
Necessários          →  10, 15 ou 20 (após escolher)
```

---

## ⚙️ Regras de Negócio

✅ **Deve**
- Selecionar exatamente 10, 15 ou 20 jogadores
- Ter escolhido uma quantidade antes de marcar
- Ver feedback visual ao selecionar (checkbox, contador)

❌ **Não pode**
- Sortear times sem seleção de presença
- Usar jogadores ausentes no sorteio
- Confirmar seleção com número errado

---

## 🔌 API Endpoints

```bash
# Atualizar presença (marcar selecionados)
POST /api/presenca
Content-Type: application/json
{
  "jogador_ids": ["uuid1", "uuid2", "uuid3", ...]
}

# Limpar presença (desselecionar todos)
POST /api/presenca/limpar

# Sortear com presentes
GET /api/times
(usa apenas jogadores.presente == true)
```

---

## 🎨 Visualmente

### Antes (Antigo)
```
[Cadastro] → [Sortear Times] → Usa TODOS
```

### Depois (Novo - Profissional)
```
[Cadastro] → [Selecionar Presentes] → [Sortear Times] → Usa apenas SELECIONADOS
```

---

## 💡 Casos de Uso

### Cenário 1: Jogo Pequeno (10 jogadores)
1. Tem 45 no banco
2. Clica em "👥 Selecionar Jogadores"
3. Clica "[🔟 10 Jogadores]"
4. Marca os 10 que estão presentes
5. Clica "[✓ Selecionar e Sortear]"
6. Sistema soreia apenas os 10 presentes

### Cenário 2: Jogo Grande (20 jogadores)
1. Tem 45 no banco
2. Clica em "👥 Selecionar Jogadores"
3. Clica "[2️⃣0️⃣ 20 Jogadores]"
4. Filtra por "⭐ Fixos" (10 jogadores)
5. Marca todos os 10
6. Muda para "👤 Avulsos"
7. Marca mais 10 que chegaram
8. Clica "[✓ Selecionar e Sortear]"
9. Sistema soreia com os 20 selecionados

### Cenário 3: Mudança de Presença
1. Estava com 15 selecionados
2. Clica "[🗑️ Limpar]" → volta a 0
3. Clica "[🔟 10 Jogadores]"
4. Marca novos 10
5. Clica "[✓ Selecionar e Sortear]"

---

## ✨ Benefícios

✅ **Profissional**: Fluxo claro e intuitivo
✅ **Escalável**: Funciona com 10 ou 1000 jogadores
✅ **Organizado**: Separa fixos de avulsos
✅ **Rápido**: Selecionar é mais rápido que editar
✅ **Flexível**: 10, 15 ou 20 jogadores
✅ **Seguro**: Não perde o banco de dados

---

## 🔄 Próximas Melhorias

- [ ] Editar jogador (nome, nível, tipo)
- [ ] Histórico de sorteios
- [ ] Presença de jogador no sorteio anterior (sugestão)
- [ ] Exportar seleção para PDF
- [ ] API para apps externos

---

**Versão**: 2.0.0  
**Novo Feature**: Sistema de Seleção de Presença

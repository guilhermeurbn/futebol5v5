# Revisão de Arquitetura - NaTrave 5v5

**Data**: Maio 2026 | **Status**: Análise Completa

---

## 1. ESTADO ATUAL DA ARQUITETURA

### ✅ Pontos Positivos
- MVC com Blueprints bem implementado
- Factory Pattern em `config.py`
- Type hints e docstrings presentes
- Separação básica de responsabilidades (models → services → routes)
- Fallback entre Postgres e JSON local

### ❌ Problemas Identificados

#### **CRÍTICO: Routes Monolítica**
```
routes/
  └── jogador_routes.py (ÚNICO arquivo com TODAS as rotas)
      ├── 16 imports de services diferentes
      ├── 100+ endpoints (jogadores, partidas, votações, stats, juiz, etc)
      ├── 8+ decoradores de autenticação
      └── Duplicação de lógica (ex: múltiplos handlers de erro)
```

**Impacto**: 
- Impossível encontrar funcionalidade específica
- Acoplamento alto (mudança em uma feature afeta todas)
- Escalabilidade comprometida

---

#### **CRÍTICO: Services Sem Padrão**
```
16 classes de serviço diferentes, sem interface comum:

✗ JogadorService, PartidaService, HistoricoService...
✗ Alguns fazem CRUD, outros fazem lógica, outros fazem export
✗ stats_service.py + jogador_stats_service.py (DUPLICAÇÃO?)
✗ Cada service reimplementa:
  - _carregar_raw()
  - _salvar()
  - _garantir_arquivo()
```

**Impacto**:
- Código duplicado (acesso a dados) em 10+ arquivos
- Difícil adicionar novo tipo de entidade
- Inconsistência em tratamento de erros

---

#### **ALTO: Data Access Sem Abstração**
```python
# ❌ Padrão duplicado em cada service:
def _carregar_raw(self):
    if os.getenv("DATABASE_URL"):
        return load_json_data(self.namespace, [])
    try:
        with open(self.arquivo, "r") as f:
            return json.load(f)
    except:
        return []

# Repetido em: JogadorService, PartidaService, 
#              HistoricoService, VotacaoService, ...
```

**Impacto**:
- Código duplicado > 200 linhas
- Mudanças em db.py exigem atualizar todos os services
- Sem contrato de acesso a dados

---

#### **ALTO: Violação de Single Responsibility**
```python
# JogadorService faz TUDO:
✗ CRUD (criar, listar, atualizar, deletar)
✗ Validação de dados
✗ Acesso direto a JSON/DB
✗ Lógica de negócio (ex: listar_por_usuario)

# PartidaService similar:
✗ Persistência
✗ Cálculos (diferença de placar, stats)
✗ Conversão de dados
```

**Impacto**:
- Services crescem indefinidamente
- Difícil testar isoladamente
- Difícil reutilizar lógica

---

#### **MÉDIO: Model Layer Deficiente**
```python
# Apenas:
✓ Jogador (dataclass com validação)

# Faltam:
✗ Partida, Votacao, Sorteio, Historico... 
  (são apenas dicts circulando)
✗ Sem validação centralizada
✗ Sem serialização padrão
```

**Impacto**:
- Inconsistência em estrutura de dados
- Validação espalhada em services
- Difícil manutenção

---

#### **MÉDIO: Cross-cutting Concerns Espalhados**
```python
# Autenticação/autorização em decoradores ad-hoc:
@login_required
@admin_required
@admin_or_juiz_required

# Múltiplas funções de erro:
_resposta_nao_autenticado()
_resposta_sem_permissao()
_resposta_somente_leitura()
_resposta_voto_somente_usuario()
_resposta_votacao_pendente()

# Sem padrão centralizado
```

**Impacto**:
- Inconsistência em respostas de erro
- Difícil adicionar novos tipos de permissão
- Lógica espalhada

---

## 2. RECOMENDAÇÕES (Prioridade)

### 🔴 **PRIORIDADE 1: Refatorar Routes em Módulos** (CRÍTICO)
**Impacto**: Escalabilidade + Manutenção | **Esforço**: Alto | **Timeline**: 2-3 dias

**Ação**:
```
routes/
  ├── __init__.py
  ├── auth_routes.py        (login, logout, cadastro)
  ├── jogador_routes.py     (CRUD de jogadores)
  ├── partida_routes.py     (sorteios, resultados, balanceamento)
  ├── stats_routes.py       (rankings, histórico, estatísticas)
  ├── votacao_routes.py     (votações)
  ├── juiz_routes.py        (funcionalidades de juiz)
  └── admin_routes.py       (administração)
```

**Benefício**:
- Cada blueprint tem máx 30-50 rotas relacionadas
- Fácil localizar funcionalidade
- Isolamento de features para testes

---

### 🔴 **PRIORIDADE 2: Criar Padrão Repository Unificado** (CRÍTICO)
**Impacto**: Reduz duplicação (>200 linhas) | **Esforço**: Médio | **Timeline**: 1-2 dias

**Ação**:
```python
# services/base_repository.py
class BaseRepository:
    """Padrão unificado para acesso a dados"""
    
    def __init__(self, namespace: str, arquivo: str, model_class=None):
        self.namespace = namespace
        self.arquivo = arquivo
        self.model_class = model_class
    
    def _carregar_raw(self) -> list:
        """Centralizado: trata DB + JSON fallback"""
        if os.getenv("DATABASE_URL"):
            return load_json_data(self.namespace, [])
        # fallback local...
    
    def _salvar(self, dados: list):
        """Centralizado"""
        save_json_data(self.namespace, dados) or save_local()
    
    def listar(self) -> list:
        """Padrão CRUD"""
    
    def criar(self, **kwargs):
    def obter_por_id(self, id):
    def atualizar(self, id, **kwargs):
    def deletar(self, id):

# Cada service herda:
class JogadorRepository(BaseRepository):
    def __init__(self):
        super().__init__("jogadores", "jogadores.json", Jogador)
```

**Benefício**:
- 0 duplicação de acesso a dados
- Mudanças centralizadas em db.py
- Contratos claros

---

### 🟠 **PRIORIDADE 3: Model Layer Completa** (ALTO)
**Impacto**: Consistência + Validação | **Esforço**: Médio | **Timeline**: 1-2 dias

**Ação**:
```python
# models/
  ├── jogadores.py       ✓ (já existe)
  ├── partidas.py        (criar com @dataclass)
  ├── votacoes.py        (criar)
  ├── sorteios.py        (criar)
  ├── historicos.py      (criar)
  └── schemas.py         (Pydantic para API validation)
```

**Exemplo**:
```python
@dataclass
class Partida:
    id: str
    sorteio_id: str
    data: str
    time_vencedor: int
    gols_times: List[int]
    notas: str = ""
    
    def __post_init__(self):
        if len(self.gols_times) < 2:
            raise ValueError("Precisa de gols para todos os times")
```

**Benefício**:
- Validação centralizada
- Type safety
- Serialização clara

---

### 🟠 **PRIORIDADE 4: Reorganizar Services com Interface Comum** (MÉDIO)
**Impacto**: Manutenção + Padrão | **Esforço**: Médio | **Timeline**: 1-2 dias

**Ação**:
```python
# services/base_service.py
class BaseService:
    """Interface comum para todos os services"""
    
    def __init__(self, repository: BaseRepository):
        self.repo = repository
    
    # Cada service foca em LÓGICA DE NEGÓCIO, não acesso a dados

class JogadorService(BaseService):
    """Lógica de jogadores (criar, filtrar, validar)"""
    
    def criar_com_validacao(self, nome, nivel):
        # Validação + regras de negócio
        
    def listar_melhores(self, limite=5):
        # Lógica específica

class BalanceadorTimes(BaseService):
    """Lógica de balanceamento (já bem feito)"""
    def balance(self, jogadores, num_times):
        # Algoritmo
```

**Benefício**:
- Services foco em lógica (testável)
- Repository foco em dados
- Separação clara

---

### 🟡 **PRIORIDADE 5: Centralizar Autenticação/Autorização** (MÉDIO)
**Impacto**: Padrão + Manutenção | **Esforço**: Baixo-Médio | **Timeline**: 1 dia

**Ação**:
```python
# services/decorators.py
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return _respond_error(401, "Autenticação obrigatória")
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        login_required_check = login_required(lambda: True)()
        if login_required_check is not True:
            return login_required_check
        if not _is_admin():
            return _respond_error(403, "Acesso restrito")
        return f(*args, **kwargs)
    return wrapper

# Response padrão
def _respond_error(status, message):
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': message}), status
    return redirect(url_for('auth.login'))
```

**Benefício**:
- Respostas consistentes
- Fácil adicionar novos tipos de permissão
- Sem duplicação de código de erro

---

## 3. IMPACTO DAS MUDANÇAS

| Recomendação | Escalabilidade | Manutenção | Testabilidade | Timeline |
|---|---|---|---|---|
| Routes modularizadas | ⬆️⬆️ | ⬆️⬆️ | ⬆️ | 2-3 dias |
| Repository Pattern | ⬆️ | ⬆️⬆️ | ⬆️⬆️ | 1-2 dias |
| Model Layer | ⬆️ | ⬆️ | ⬆️ | 1-2 dias |
| Services interface | ⬆️ | ⬆️ | ⬆️⬆️ | 1-2 dias |
| Auth centralizado | ➡️ | ⬆️ | ➡️ | 1 dia |

**Total Impacto**:
- Redução de ~300 linhas duplicadas
- Escalabilidade para 50+ rotas sem overhead
- Tempo de onboarding reduzido 50%

---

## 4. ROADMAP DE IMPLEMENTAÇÃO

### Fase 1 (Semana 1)
- [ ] Criar `BaseRepository` → migrar 3 services críticos
- [ ] Refatorar `routes/` em 2-3 módulos principais
- [ ] Centralizar respostas de erro

### Fase 2 (Semana 2)
- [ ] Completar Models layer (Partida, Votação, etc)
- [ ] Refatorar todos os services com BaseService
- [ ] Adicionar testes para novos padrões

### Fase 3 (Semana 3)
- [ ] Refatorar routes restantes
- [ ] Documentar padrões
- [ ] Code review e testes e2e

---

## 5. PRÓXIMOS PASSOS

1. **Imediato**: Iniciar com Priority 1 (Routes modularizadas)
2. **Paralelo**: Preparar BaseRepository
3. **Validação**: Testes automatizados para novos padrões

**Status**: Pronto para implementação

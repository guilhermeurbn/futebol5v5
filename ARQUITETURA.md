cd /Users/guilhermeurbano/futebol5v5
python run.py# 📐 Arquitetura do Projeto

## Estrutura MVC com Blueprint

Este projeto segue um padrão profissional de organização usando Flask com Blueprints para melhor escalabilidade e manutenção.

```
futebol5v5/
├── app.py                 # Ponto de entrada - Factory Pattern
├── config.py             # Configurações (dev, test, prod)
├── run.py                # Script amigável para iniciar dev
├── utils.py              # Funções utilitárias
├── requirements.txt      # Dependências
├── README.md             # Documentação
├── .gitignore            # Git ignore
│
├── models/               # 📦 Camada de Dados
│   ├── __init__.py
│   └── jogadores.py      # Dataclass com validação
│
├── services/             # 🔧 Lógica de Negócio
│   ├── __init__.py
│   ├── jogador_service.py  # CRUD de jogadores
│   └── balanceamento.py    # Algoritmo de times
│
├── routes/               # 🛣️ Endpoints
│   ├── __init__.py
│   └── jogador_routes.py   # Blueprints com rotas
│
├── static/               # 🎨 Frontend
│   └── style.css         # Estilos CSS moderno
│
└── templates/            # 📄 HTML
    ├── index.html        # Página principal
    └── times.html        # Resultado sorteio
```

## Fluxo de Dados

```
Requisição HTTP
      ↓
routes/jogador_routes.py (Blueprint)
      ↓
services/jogador_service.py (Lógica)
      ↓
models/jogadores.py (Dados)
      ↓
jogadores.json (Persistência)
```

## Padrões de Design

### 1. **Factory Pattern** (app.py)
```python
def criar_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    return app
```

### 2. **Service Pattern** (services/)
Encapsula lógica de negócio

### 3. **Repository Pattern** (JogadorService)
Abstrai acesso aos dados

### 4. **Blueprint Pattern** (routes/)
Separa rotas em módulos

## Validação de Dados

**Modelo Jogador:**
```python
@dataclass
class Jogador:
    nome: str        # Mínimo 2 caracteres
    nivel: int       # Entre 1 e 10
    id: str          # UUID gerado
    criado_em: str   # ISO timestamp
```

## Algoritmo Snake Draft

Balanceia times alternando entre eles:

```
Jogadores ordenados: [A(10), B(9), C(8), D(7), E(6), F(5), G(4), H(3), I(2), J(1)]

Iteração:
1. Time 1 ← A(10)
2. Time 2 ← B(9)
3. Time 1 ← C(8)
4. Time 2 ← D(7)
... até completar 5 de cada

Resultado:
Time 1: A, C, E, G, I = 30 pontos
Time 2: B, D, F, H, J = 25 pontos
Diferença: 5 (equilibrado)
```

## API REST

Endpoints seguem padrão RESTful:

```
GET    /api/jogadores         # List
POST   /api/jogadores         # Create
GET    /api/jogadores/<id>    # Retrieve
PUT    /api/jogadores/<id>    # Update
DELETE /api/jogadores/<id>    # Delete
GET    /api/times             # Business Logic
```

## Tratamento de Erros

```python
# Validação em modelo
try:
    jogador = Jogador(nome, nivel)
except ValueError as e:
    return {'erro': str(e)}, 400

# Endpoints retornam JSON
{
    "sucesso": False,
    "erro": "Nome inválido"
}
```

## Performance

- **Dados**: JSON (leve, legível)
- **Cache**: Carregamento lazy do arquivo
- **CSS**: Variáveis CSS para performance
- **HTML**: Semântico e otimizado

## Segurança

- ✅ Validação em todos os endpoints
- ✅ Type hints para segurança
- ✅ Sanitização de inputs
- ✅ Error handling sem expor dados sensíveis

## Testabilidade

Estrutura permite fácil teste unitário:

```python
# Teste do serviço
def test_criar_jogador():
    service = JogadorService(":memory:")
    jogador = service.criar("João", 7)
    assert jogador.nome == "João"

# Teste do modelo
def test_validacao_jogador():
    with pytest.raises(ValueError):
        Jogador("A", 15)
```

## Extensibilidade

Adicionar novo endpoint é simples:

```python
@jogador_bp.route('/api/novo-endpoint')
def novo_endpoint():
    dados = jogador_service.metodo()
    return jsonify(dados)
```

## Configuração

Diferentes ambientes via `config.py`:

```python
# Desenvolvimento
export FLASK_ENV=development

# Produção
export FLASK_ENV=production
```

---

**Versão**: 1.0.0  
**Padrão Arquitetural**: MVC com Blueprint + Service Layer

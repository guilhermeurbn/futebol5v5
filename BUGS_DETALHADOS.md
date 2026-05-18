# 🐛 BUGS ENCONTRADOS - RELATÓRIO DETALHADO

---

## 🔴 CRÍTICOS (P0 - Interrupção de Serviço)

### BUG #1: Validação Inadequada de Votos Duplicados

**ID**: NATRAVE-001  
**Severidade**: 🔴 CRÍTICA  
**Afetado**: votacao_service.py  
**Status**: ⚠️ Necessita Correção

#### Descrição
O sistema permite que um usuário vote no mesmo jogador múltiplas vezes em uma mesma partida de votação. Enquanto a quantidade total de votos é validada (5 obrigatórios), não há verificação de unicidade.

#### Arquivo Afetado
```
services/votacao_service.py - Linha 323-340
Método: salvar_voto()
```

#### Código Problemático
```python
def salvar_voto(self, partida_id, user_id, votos_obrigatorios, votos_extras):
    # ✅ Valida quantidade
    if len(obrigatorios) < 5 or len(obrigatorios) > 5:
        raise ValueError("Voce deve votar em exatamente 5 jogadores obrigatorios")
    
    # ❌ NÃO valida unicidade
    nomes = set()
    for item in obrigatorios:
        nome = item.get("jogador_nome", "").strip()
        if not nome:
            continue
        # FALTA: if nome in nomes: raise ValueError("Jogador duplicado")
        nomes.add(nome)
```

#### Cenário de Exploração
```
1. Admin cria partida de votação com 5 jogadores
2. Usuário manipula payload:
   POST /votacao/salvar
   jogador_nome: ["João", "João", "João", "João", "João"]
   nota: [10, 10, 10, 10, 10]
   
3. Sistema valida: 5 votos ✅
4. Sistema NÃO valida: Todos são João ❌
5. Ranking incorreto: João recebe 50 pontos (deveria ser 10)
```

#### Impacto
- 🔴 **Ranking inválido** até fim da temporada
- 🔴 Resultados competitivos comprometidos
- 🔴 Injustiça para outros jogadores

#### Fix Recomendado
```python
def salvar_voto(self, partida_id, user_id, votos_obrigatorios, votos_extras):
    # ... validações existentes ...
    
    # ✨ NOVO: Validar unicidade
    nomes_obrigatorios = []
    for item in votos_obrigatorios:
        nome = (item.get("jogador_nome") or "").strip().lower()
        if not nome:
            continue
        if nome in nomes_obrigatorios:
            raise ValueError(f"Jogador {nome} aparece múltiplas vezes nos votos")
        nomes_obrigatorios.append(nome)
    
    if len(nomes_obrigatorios) != 5:
        raise ValueError("Deve haver exatamente 5 jogadores diferentes")
```

#### Teste para Validar Fix
```python
def test_voto_jogador_duplicado():
    service = VotacaoService()
    partida = criar_partida_teste()
    
    votos_duplicados = [
        {'jogador_nome': 'João', 'time_numero': 1, 'nota': 10},
        {'jogador_nome': 'João', 'time_numero': 1, 'nota': 10},
        {'jogador_nome': 'João', 'time_numero': 1, 'nota': 10},
        {'jogador_nome': 'João', 'time_numero': 1, 'nota': 10},
        {'jogador_nome': 'João', 'time_numero': 1, 'nota': 10},
    ]
    
    with pytest.raises(ValueError, match="multiplas"):
        service.salvar_voto(partida['id'], 'user1', votos_duplicados)
```

---

### BUG #2: Race Condition em Votação Concorrente

**ID**: NATRAVE-002  
**Severidade**: 🔴 CRÍTICA  
**Afetado**: votacao_service.py  
**Status**: ⚠️ Necessita Correção

#### Descrição
Quando múltiplos usuários votam simultaneamente na mesma partida, há possibilidade de race condition que causa perda de votos. O problema ocorre no padrão read-modify-write sem lock.

#### Arquivo Afetado
```
services/votacao_service.py - Método _salvar()
```

#### Código Problemático
```python
def _salvar(self, dados: Dict) -> None:
    """Salva dados - SEM LOCK"""
    if os.getenv("DATABASE_URL"):
        save_json_data("votacoes_partidas", dados)
        return
    # ❌ Operação não-atômica:
    with open(self.arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    # Entre abrir e fechar, outro processo pode ter escrito!
```

#### Timeline da Race Condition
```
Thread 1 (Alice):          Thread 2 (Bob):
Read file                  
  count = 8 votos
                           Read file
                             count = 8 votos
Parse JSON
Modify data
  count = 9 votos
Write file
  ✅ Escreveu com 9
                           Parse JSON
                           Modify data
                             count = 9 votos (não 10!)
                           Write file
                             ❌ Sobrescreveu com 9
                           
Resultado: Perdeu 1 voto!
```

#### Impacto
- 🔴 Votos são perdidos silenciosamente
- 🔴 Ranking não reflete votos reais
- 🔴 Impossível auditoria de votos

#### Fix Recomendado
Opção 1: Usar lock (rápido):
```python
import threading

class VotacaoService:
    def __init__(self, arquivo):
        self._lock = threading.Lock()
    
    def _salvar(self, dados):
        with self._lock:  # Garante acesso exclusivo
            if os.getenv("DATABASE_URL"):
                save_json_data("votacoes_partidas", dados)
                return
            with open(self.arquivo, "w") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
```

Opção 2: Usar transações (melhor para produção com PostgreSQL):
```python
def _salvar_com_transacao(self, dados):
    """Usar transações de banco em produção"""
    if os.getenv("DATABASE_URL"):
        # PostgreSQL com transação
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("BEGIN TRANSACTION")
            try:
                cur.execute("UPDATE votacoes SET data = %s WHERE id = %s", ...)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
```

---

### BUG #3: Vulnerabilidade de Autorização - Acesso a Recursos de Outros Usuários

**ID**: NATRAVE-003  
**Severidade**: 🔴 CRÍTICA  
**Afetado**: routes/jogador_routes.py, jogador_service.py  
**Status**: ⚠️ Necessita Correção

#### Descrição
Alguns endpoints permitem que um usuário acesse/modifique jogadores que pertencem a outro usuário. Não há validação de propriedade do recurso antes de operações.

#### Arquivo Afetado
```
routes/jogador_routes.py - Rotas de jogador
jogador_service.py - Métodos obter_por_id()
```

#### Cenários Vulneráveis

##### Cenário 1: Ver Perfil de Jogador (Possível Exposure)
```python
@app.route('/jogadores/<jogador_id>/perfil', methods=['GET'])
@login_required
def perfil_jogador_publico(jogador_id):
    jogador = jogador_service.obter_por_id(jogador_id)
    # ⚠️ QUESTÃO: Alguém pode visualizar qualquer jogador?
    # Provavelmente intencional (público), mas precisa verificar
```

##### Cenário 2: Editar Jogador (Crítico)
```python
@app.route('/jogadores/<jogador_id>/editar', methods=['POST'])
@login_required
def editar_jogador(jogador_id):
    jogador = jogador_service.obter_por_id(jogador_id)
    
    # ❌ FALTA: Validar se jogador pertence ao usuário
    if jogador.owner_user_id != session.get('user_id'):
        if not _is_admin():
            return forbidden()
    
    # Atual (VULNERÁVEL):
    jogador_service.atualizar(jogador_id, {
        'nivel': request.form.get('nivel'),
        'nome': request.form.get('nome'),
    })
```

#### Teste de Exploração
```bash
# 1. Alice faz login
curl -c cookies.txt \
  -d "username=alice&password=pass123" \
  http://localhost:5000/login

# 2. Alice consegue ID do jogador de Bob
curl -b cookies.txt \
  http://localhost:5000/jogadores \
  | grep -o '"id":"[^"]*"'
# Saída: "id":"bob-jogador-id-123"

# 3. Alice tenta editar jogador de Bob (VULNERÁVEL!)
curl -b cookies.txt -X POST \
  -d "nivel=1&nome=BadBob" \
  http://localhost:5000/jogadores/bob-jogador-id-123/editar

# 4. Resultado: Jogador de Bob foi degradado de nível 10 para 1! 🚨
```

#### Impacto
- 🔴 Griefing: Usuários podem sabotarmen uns aos outros
- 🔴 Integridade: Dados de jogadores podem ser alterados maliciosamente
- 🔴 Confiança: Sistema não é seguro

#### Fix Recomendado
```python
def validar_propriedade_jogador(jogador_id, user_id):
    """Valida se jogador pertence ao usuário"""
    jogador = jogador_service.obter_por_id(jogador_id)
    if not jogador:
        raise NotFound("Jogador não encontrado")
    
    if jogador.owner_user_id != user_id:
        # Admin pode editar qualquer um
        if not _is_admin():
            raise Forbidden("Você não tem permissão para editar este jogador")
    
    return jogador

@app.route('/jogadores/<jogador_id>/editar', methods=['POST'])
@login_required
def editar_jogador(jogador_id):
    try:
        jogador = validar_propriedade_jogador(jogador_id, session.get('user_id'))
    except Forbidden:
        return render_template('erro.html', msg='Sem permissão'), 403
    
    # Seguro agora
    jogador_service.atualizar(jogador_id, {...})
```

---

## 🟡 MÉDIOS (P1 - Dados Incorretos / UX)

### BUG #4: Validação Ausente para Nível de Jogador (1-10)

**ID**: NATRAVE-004  
**Severidade**: 🟡 MÉDIO  
**Afetado**: services/jogador_service.py, routes  
**Status**: ⚠️ Necessita Correção

#### Descrição
O frontend valida nível entre 1-10 com `input type="number" min="1" max="10"`, mas um atacante pode fazer POST direto bypass da validação frontend, criando jogador com nível inválido (999, -5, etc).

#### Teste de Exploração
```bash
# Bypass da validação frontend
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"nome":"Hacker","nivel":999,"tipo":"fixo"}' \
  http://localhost:5000/api/jogadores

# Resultado: Jogador com nível 999 ✅ (BUG)
```

#### Impacto
- 🟡 Algoritmo de balanceamento quebra
- 🟡 Sorteio gera times desbalanceados
- 🟡 Ranking incorreto

#### Código Atual (Vulnerável)
```python
# models/jogadores.py
@dataclass
class Jogador:
    nivel: int
    
    def __post_init__(self):
        if not (1 <= self.nivel <= 10):  # ✅ Valida aqui
            raise ValueError("Nível inválido: deve estar entre 1 e 10")
```

**PROBLEMA**: Validação existe no modelo, mas não é sempre chamada!

#### Fix
```python
# services/jogador_service.py
def criar(self, nome: str, nivel: int, ...):
    # ✨ Validação explícita ANTES de criar
    if not (1 <= int(nivel) <= 10):
        raise ValueError("Nível deve estar entre 1 e 10")
    
    try:
        jogador = Jogador(nome=nome, nivel=int(nivel), ...)
    except ValueError as e:
        raise ValueError(f"Dados inválidos: {str(e)}")
```

---

### BUG #5: Política de Senhas Fraca

**ID**: NATRAVE-005  
**Severidade**: 🟡 MÉDIO  
**Afetado**: services/auth_service.py  
**Status**: ⚠️ Necessita Correção

#### Descrição
Senhas são validadas apenas por tamanho mínimo (6 caracteres), sem requisitos de complexidade. Permite senhas fracas como "aaaaaa", "123456", "password".

#### Código Atual
```python
def criar_usuario(self, username, nome, password, role):
    if not password or len(password) < 6:
        raise ValueError("Senha deve ter ao menos 6 caracteres")
    # ❌ FIM DA VALIDAÇÃO
```

#### Senhas Fracas Aceitas
```
✅ Aceito: "aaaaaa"      (6x mesma letra)
✅ Aceito: "123456"      (sequência numérica)
✅ Aceito: "password"    (senha comum)
❌ Aceito: "P@ssw0rd!"   (forte)
```

#### Impacto
- 🟡 Senhas fracas vulneráveis a força bruta
- 🟡 Se arquivo users.json vazar, senhas fáceis de quebrar

#### Fix Recomendado
```python
import re
from zxcvbn import zxcvbn  # pip install zxcvbn

def validar_senha_forte(senha):
    """Valida força da senha"""
    # Requisitos mínimos
    if len(senha) < 8:
        raise ValueError("Senha deve ter ao menos 8 caracteres")
    
    if not re.search(r'[A-Z]', senha):
        raise ValueError("Senha deve conter letra maiúscula")
    
    if not re.search(r'[a-z]', senha):
        raise ValueError("Senha deve conter letra minúscula")
    
    if not re.search(r'[0-9]', senha):
        raise ValueError("Senha deve conter número")
    
    # Verificar força com zxcvbn
    resultado = zxcvbn(senha)
    if resultado['score'] < 3:  # Escala 0-4
        raise ValueError("Senha muito fraca. Use combinações mais complexas")

# Uso
def criar_usuario(self, username, nome, password, role):
    validar_senha_forte(password)  # Agora valida força!
```

---

### BUG #6: Validação de CSRF em APIs Não Explícita

**ID**: NATRAVE-006  
**Severidade**: 🟡 MÉDIO  
**Afetado**: routes/jogador_routes.py, app.py  
**Status**: ⚠️ Necessita Verificação

#### Descrição
Endpoints `/api/*` podem não estar validando CSRF tokens explicitamente. Enquanto Flask-WTF CSRFProtect pode estar configurado globalmente, não está claro se é aplicado a APIs JSON.

#### Código Questionável
```python
# app.py
if CSRFProtect is not None:
    try:
        csrf = CSRFProtect()
        csrf.init_app(app)
    except Exception as e:
        logger.warning(f"Falha ao iniciar CSRFProtect: {e}")
```

**Questão**: CSRFProtect valida POST JSON automaticamente?

#### Verificação Necessária
```python
# Testar se API POST sem token é bloqueado
def test_api_csrf_protegida():
    client = app.test_client()
    
    # POST sem CSRF token
    response = client.post('/api/sortear', 
                           json={'data': '...'},
                           content_type='application/json')
    
    # Deve retornar 400 (CSRF mismatch)
    assert response.status_code == 400  # Ou rejeitado?
```

#### Fix (Se Necessário)
```python
@app.route('/api/sortear', methods=['POST'])
@login_required
def sortear_api():
    # Validar CSRF manualmente se POST JSON
    if not request.form.get('csrf_token'):
        token = request.headers.get('X-CSRFToken')
        if not token:
            return jsonify({'erro': 'CSRF missing'}), 403
    
    # ... rest of code
```

---

### BUG #7: Session Cookie Security em Desenvolvimento

**ID**: NATRAVE-007  
**Severidade**: 🟡 MÉDIO  
**Afetado**: config.py  
**Status**: ⚠️ Configuração Questionável

#### Descrição
`SESSION_COOKIE_SECURE = False` está OK para desenvolvimento, mas pode causar problemas se produção usar HTTP por engano.

#### Código Atual
```python
# config.py
class Config:
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'  # Bom padrão
    PREFERRED_URL_SCHEME = 'https'   # Indica HTTPS, mas cookie não secure?
```

#### Cenário de Risco
```
1. App deployada em produção com HTTP (por engano)
2. SESSION_COOKIE_SECURE = False, então cookie é enviado em HTTP
3. Atacker faz man-in-the-middle
4. Cookie de session é interceptado
5. Atacker hijackeia sessão
```

#### Fix Recomendado
```python
# config.py - Environment-aware
class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True      # ✅ HTTPS only
    SESSION_COOKIE_HTTPONLY = True    # ✅ Não acessível via JS
    SESSION_COOKIE_SAMESITE = 'Strict'  # ✅ Mais restritivo

class DevelopmentConfig(Config):
    SESSION_COOKIE_SECURE = False     # OK para localhost
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

# Validação
def criar_app(config_name):
    app = criar_app(config_name)
    
    # Valida configuração
    if app.config['DEBUG'] is False:
        # Produção
        if not app.config['SESSION_COOKIE_SECURE']:
            logger.error("⚠️ PRODUÇÃO SEM SECURE COOKIES!")
```

---

## 🟢 LEVES (P2 - Qualidade de Código)

### BUG #8: Testes retornam valores (Anti-pattern Pytest)

**ID**: NATRAVE-008  
**Severidade**: 🟢 LEVE  
**Afetado**: tests/test_goleiros.py  
**Status**: ✅ Fácil de corrigir

#### Descrição
Funções de teste retornam `True` em vez de usar `assert`. Causa warnings do Pytest.

#### Código Atual
```python
def test_validacao():
    """Testa validação de jogadores"""
    jogadores = criar_jogadores_teste()
    valido, msg = BalanceadorTimes.validar_jogadores_com_goleiros(jogadores)
    
    assert valido, msg
    return True  # ❌ Anti-pattern: pytest espera None
```

#### Warnings Gerados
```
PytestReturnNotNoneWarning: Test functions should return None, 
but test_validacao returned <class 'bool'>
```

#### Fix
```python
def test_validacao():
    """Testa validação de jogadores"""
    jogadores = criar_jogadores_teste()
    valido, msg = BalanceadorTimes.validar_jogadores_com_goleiros(jogadores)
    
    assert valido, msg  # ✅ Sem return
```

---

## 📊 Resumo de Bugs por Severidade

| Severidade | Quantidade | Total | Prioridade |
|---|---|---|---|
| 🔴 Crítica | 3 | P0 | Agora (48h) |
| 🟡 Média | 4 | P1 | Semana 1 |
| 🟢 Leve | 1 | P2 | Semana 2 |
| **TOTAL** | **8** | - | - |

---

## 🔧 Plano de Correção

### Semana 1 (Próximos 7 dias)
```
[ ] BUG #1: Validação de votos duplicados (2h)
[ ] BUG #2: Race condition votação (3h)
[ ] BUG #3: Validação de propriedade (2h)
[ ] BUG #4: Validação de nível (1h)
[ ] BUG #8: Fix anti-patterns teste (30min)
Total: 8.5 horas
```

### Semana 2
```
[ ] BUG #5: Política de senhas forte (2h)
[ ] BUG #6: Verificar CSRF em APIs (1h)
[ ] BUG #7: Session cookie security (1h)
Total: 4 horas
```

---

**Última atualização**: 18/05/2026  
**Próxima revisão**: 01/06/2026

# 🔒 Segurança - Auditoria Completa

**Data:** 15 de junho de 2026  
**Status:** Auditoria realizada - Ações recomendadas  
**Responsável:** Tim de Segurança

---

## 📋 Sumário Executivo

Este documento registra uma auditoria de segurança completa do projeto NaTrave. Foram identificadas **15 vulnerabilidades** distribuídas em:

- **3 CRÍTICAS** (correção imediata)
- **4 ALTAS** (1-2 semanas)
- **4 MÉDIAS** (próximo sprint)
- **4 BAIXAS** (melhorias contínuas)

**Score de Segurança Atual:** 6/10  
**Meta:** 8.5/10 após correções críticas

---

## 🔴 CRÍTICAS (Correção Imediata)

### 1. SQL Injection via Interpolação em Nomes de Tabela

**Risco:** Um atacante poderia injetar SQL se o nome da tabela for dinamicamente alterado  
**Localização:** [services/db.py](../services/db.py#L52), linhas 52, 101, 149, 185  
**Código Vulnerável:**
```python
cur.execute(f"select payload from {json_store_table_name()} where namespace = %s", (namespace,))
```

**Mitigação (IMPLEMENTAR AGORA):**
```python
# ✅ Tabela está hardcoded em json_store_table_name(), mas adicione whitelist para segurança futura
ALLOWED_TABLES = {'app_json_store'}

def json_store_table_name() -> str:
    table = "app_json_store"
    if table not in ALLOWED_TABLES:
        raise ValueError("Invalid table name")
    return table
```

**Prazo:** Imediato (antes do próximo deploy)  
**Impacto em Produção:** Baixo (refactor apenas do validador)

---

### 2. Dependências Desatualizadas com CVEs Conhecidas

**Risco:** Vulnerabilidades conhecidas em Jinja2 e Gunicorn exploráveis em produção  
**Localização:** [requirements.txt](../requirements.txt)  
**CVEs Afetadas:**
- Jinja2 3.1.6: CVE-2024-22195, CVE-2024-34064, CVE-2024-56326
- Gunicorn 22.0.0: CVE-2024-1135 (HTTP Request Smuggling)

**Mitigação (IMPLEMENTAR AGORA):**
```txt
# Arquivo: requirements.txt
Jinja2>=3.1.5          # ⬆️ Atualizar de 3.1.6
gunicorn>=22.0.1       # ⬆️ Atualizar de 22.0.0
Flask-WTF>=1.2.1       # Manter atualizado
requests>=2.32.0       # Manter atualizado
psycopg2-binary>=2.9.10  # Manter atualizado
```

**Prazo:** Imediato (1-2 horas de testes)  
**Impacto:** Nenhum (backward compatible)  
**Comando:**
```bash
pip install --upgrade Jinja2 gunicorn
pip freeze > requirements.txt
```

---

### 3. Exposição de Chave de API do Resend

**Risco:** Credenciais em headers HTTP sem proteção; se logs forem expostos ou trafego interceptado, a chave do Resend fica comprometida  
**Localização:** [services/email_service.py](../services/email_service.py#L88-L98)  
**Código Vulnerável:**
```python
headers = {
    "Authorization": f"Bearer {resolved_api_key}",  # ❌ Visível em logs!
    "Content-Type": "application/json",
}

response = requests.post(url, headers=headers, json=payload, timeout=15)
```

**Mitigação (IMPLEMENTAR AGORA):**
```python
# ✅ Adicionar mascaramento em logs e usar HTTPS only (já configurado)
import logging

# Interceptar logs para redação automática
class RedactingFormatter(logging.Formatter):
    def format(self, record):
        record.msg = str(record.msg).replace(resolved_api_key, '[REDACTED]')
        return super().format(record)

logger.handlers[0].setFormatter(RedactingFormatter())

# Também adicionar na conexão
response = requests.post(
    url,
    headers=headers,
    json=payload,
    timeout=15,
    verify=True  # ✅ Validar certificado HTTPS
)
```

**Prazo:** Imediato  
**Impacto:** Baixo (logging apenas)  
**Checklist:**
- [ ] Implementar `RedactingFormatter`
- [ ] Verificar que `resolve_credentials()` nunca printa chaves
- [ ] Auditar logs em produção para exposições

---

## 🟠 ALTAS (1-2 Semanas)

### 4. Falta de Rate Limiting em Endpoints de Autenticação

**Risco:** Brute force de senha, ataque de dicionário, DoS em cadastro/login  
**Localização:** [routes/auth_routes.py](../routes/auth_routes.py#L107), linhas 107 (login), 225 (cadastro), 265 (recuperar senha)  
**Endpoints Vulneráveis:**
- `POST /login` - sem limite
- `POST /cadastro` - sem limite
- `POST /recuperar-senha` - sem limite

**Mitigação (IMPLEMENTAR EM 1 SEMANA):**
```bash
# 1. Instalar Flask-Limiter
pip install Flask-Limiter
```

```python
# No app.py, após criar a app:
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Em routes/auth_routes.py:
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # Max 5 tentativas por minuto
def login_submit():
    # ... código existente ...

@auth_bp.route('/cadastro', methods=['POST'])
@limiter.limit("3 per hour")  # Max 3 cadastros por hora por IP
def cadastro_submit():
    # ... código existente ...

@auth_bp.route('/recuperar-senha', methods=['POST'])
@limiter.limit("3 per hour")  # Max 3 resets por hora
def recuperar_senha_submit():
    # ... código existente ...
```

**Prazo:** 1 semana  
**Impacto:** Mínimo (melhora UX ao bloquear tentativas abusivas)

---

### 5. Sessão Muito Longa e Cookie SameSite Fraco

**Risco:** Sessão de 7 dias permite CSRF prolongado; `Lax` permite cross-site requests  
**Localização:** [config.py](../config.py#L13-L17)  
**Código Atual:**
```python
PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # ❌ Muito longa
SESSION_COOKIE_SAMESITE = 'Lax'               # ❌ Fraco
```

**Mitigação (IMPLEMENTAR EM 1 SEMANA):**
```python
# config.py
class Config:
    """Configuração base"""
    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # ✅ Reduzido para 2h
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'  # ✅ Elevado para Strict
    SESSION_COOKIE_SECURE = False  # Será True em produção
    PREFERRED_URL_SCHEME = 'https'

class ProductionConfig(Config):
    """Configuração de produção"""
    SESSION_COOKIE_SECURE = True  # ✅ Enforçar HTTPS
```

**Prazo:** 1 semana (testar logout automático)  
**Impacto:** Usuários receberão "sessão expirada" a cada 2h - comunicar isso com UX

---

### 6. Configuração de CORS Ausente

**Risco:** Se API for pública, qualquer site pode fazer requisições cross-origin  
**Localização:** [app.py](../app.py) - verificar se há endpoints `/api/*` públicos  
**Verificar:** 
- [ ] Endpoints `/api/` estão protegidos por autenticação?
- [ ] Site está servido no mesmo domínio da API?

**Mitigação (SE NECESSÁRIO):**
```python
# No app.py, após criar a app:
from flask_cors import CORS

if config_name != 'testing':
    CORS(app, resources={
        r"/api/*": {
            "origins": [os.getenv('ALLOWED_ORIGIN', 'http://localhost:5000')],
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "X-CSRFToken"],
            "supports_credentials": True
        }
    })
```

**Prazo:** 1 semana (se aplicável)  
**Impacto:** Baixo se API não for pública

---

### 7. Exceções Silenciosas Ocultando Erros

**Risco:** Bugs não detectados; comportamento indefinido em produção  
**Localização:** [services/stats_service.py](../services/stats_service.py#L220), [services/sugestoes_service.py](../services/sugestoes_service.py#L27)  
**Código Vulnerável:**
```python
try:
    # código
except:
    pass  # ❌ Silencia TODOS os erros
```

**Mitigação (IMPLEMENTAR EM 1 SEMANA):**
```python
# Exemplo correto:
try:
    data_sorteio = datetime.fromisoformat(data_str)
except (ValueError, TypeError) as e:
    logger.warning(f"Failed to parse date '{data_str}': {e}")
    continue  # ou raise com mensagem clara

# Em nenhum lugar usar bare except
```

**Prazo:** 1 semana  
**Impacto:** Nenhum (melhora observabilidade)  
**Comando para auditar:**
```bash
grep -n "except:" services/*.py routes/*.py
```

---

## 🟡 MÉDIAS (Próximo Sprint)

### 8. IDOR - Insecure Direct Object Reference

**Risco:** Um usuário pode acessar dados de outro usuário sabendo o ID  
**Localização:** [routes/jogador_crud_routes.py](../routes/jogador_crud_routes.py#L223)  
**Verificação Atual:**
```python
def obter_jogador(jogador_id):
    if _is_admin():
        return jogador_service.obter_por_id(jogador_id)
    else:
        return jogador_service.obter_por_id(jogador_id, session.get('user_id'))
```

**Status:** ✅ Já está protegido (verifica `user_id`), mas documentar como obrigatório em ALL endpoints

**Mitigação (DOCUMENTAR):**
Criar checklist de auditoria IDOR em todas as rotas GET com ID:
```python
# ✅ PADRÃO OBRIGATÓRIO:
@app.route('/recurso/<recurso_id>')
def get_recurso(recurso_id):
    if _is_admin():
        recurso = service.obter_por_id(recurso_id)
    else:
        recurso = service.obter_por_id(recurso_id, session.get('user_id'))
    
    if not recurso:
        abort(403)  # Não expor que existe ou não
    return recurso
```

**Prazo:** Próximo sprint (adicionar testes de IDOR)  
**Impacto:** Nenhum

---

### 9. Validação Insuficiente de Input

**Risco:** Erro 500 expostos; casting falhando silenciosamente  
**Localização:** [routes/admin_routes.py](../routes/admin_routes.py#L250) e similar  
**Código Vulnerável:**
```python
nivel = int(dados.get('nivel'))  # ❌ Pode falhar
```

**Mitigação (IMPLEMENTAR PRÓXIMO SPRINT):**
```python
try:
    nivel = int(dados.get('nivel', 0))
    if not (1 <= nivel <= 10):
        raise ValueError("Nível deve estar entre 1 e 10")
except (ValueError, TypeError):
    logger.warning(f"Invalid level input: {dados.get('nivel')}")
    return jsonify({'erro': 'Nível inválido (1-10)'}), 400
```

**Prazo:** Próximo sprint  
**Impacto:** Melhora robustez

---

### 10. Mensagens de Erro Expõem Detalhes do Sistema

**Risco:** Informação sobre stack trace, estrutura interna, banco de dados exposta  
**Localização:** Múltiplas rotas - exemplo em [routes/jogador_crud_routes.py](../routes/jogador_crud_routes.py#L230)  
**Padrão Correto:**
```python
try:
    # código
except Exception as e:
    logger.error(f"Erro ao obter jogador {jogador_id}: {e}", exc_info=True)
    return jsonify({'erro': 'Erro ao processar solicitação'}), 500  # ✅ Genérico
```

**Prazo:** Próximo sprint  
**Impacto:** Nenhum

---

### 11. Validação de Sessão Contra Banco de Dados

**Risco:** Se sessão for XSS-injetada, role pode ser spoofado  
**Mitigação (IMPLEMENTAR PRÓXIMO SPRINT):**
```python
def _validate_session():
    """Valida sessão contra dados persistidos"""
    user_id = session.get('user_id')
    if not user_id:
        return False
    
    try:
        user = auth_service.obter_por_id(user_id)
        if not user:
            session.clear()
            return False
        
        # Validar que role não foi alterado
        if user.get('role') != session.get('role'):
            logger.warning(f"Session tampering detected for user {user_id}")
            session.clear()
            return False
        
        return True
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return False

# Em app.py, adicionar middleware:
@app.before_request
def validate_session():
    if session.get('user_id') and not _validate_session():
        abort(401)
```

**Prazo:** Próximo sprint  
**Impacto:** Mínimo (1-2ms por request)

---

## 🟢 BAIXAS (Melhorias Contínuas)

### 12. Credenciais Temporárias Persistidas em Plaintext

**Risco:** Se arquivo `.secrets/initial_admin_credentials.json` for exposto, senha está visível  
**Localização:** [services/auth_service.py](../services/auth_service.py#L73)  
**Mitigação Existente:** ✅ Arquivo está em `.gitignore`  
**Mitigação Adicional (MELHORIAS):**
```python
# Ao invés de salvar credenciais, gerar token one-time:
import secrets

def criar_usuario_com_reset_token(username, email):
    usuario = self.criar_usuario(username, email, role='admin')
    token = secrets.token_urlsafe(32)
    self._salvar_reset_token(token, usuario['id'])
    
    reset_url = f"{self.base_url}/definir-senha?token={token}"
    return usuario, reset_url  # ✅ Nunca salvar senha
```

**Prazo:** Melhorias futuras  
**Impacto:** Nenhum

---

### 13. Contas Padrão Criadas Automaticamente

**Risco:** Baixo - apenas em ambiente não-prod, mas vulnerável se código for alterado  
**Status:** ✅ Já protegido (apenas em dev/test)  
**Verificação:**
```bash
# Confirmar que contas admin não existem em produção:
grep -n "admin" services/auth_service.py | grep -i "criar\|create"
```

**Prazo:** Documentar apenas  
**Impacto:** Nenhum

---

### 14. Política de Segurança de Conteúdo (CSP) Desabilitada

**Risco:** XSS pode executar JavaScript arbitrário  
**Localização:** [app.py](../app.py#L96)  
**Código Atual:**
```python
Talisman(app, content_security_policy=None)  # ❌ Desabilitado
```

**Mitigação (PRÓXIMO SPRINT):**
```python
Talisman(
    app,
    force_https=(config_name == 'production'),
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'"],  # Remover unsafe-inline em produção
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", "data:", "https:"],
        'font-src': "'self'",
        'connect-src': ["'self'"],
        'frame-ancestors': "'none'",
        'base-uri': "'self'",
        'form-action': "'self'"
    }
)
```

**Prazo:** Próximo sprint  
**Impacto:** Possível quebra de layouts inline (testar)

---

### 15. Falta de Logging de Eventos de Segurança

**Risco:** Impossível auditar tentativas de ataque ou acesso não autorizado  
**Mitigação (IMPLEMENTAR):**
```python
# Em config.py, adicionar audit logger:
AUDIT_LOG_FILE = os.getenv('AUDIT_LOG_FILE', 'logs/audit.log')

import logging
audit_logger = logging.getLogger('audit')
audit_handler = logging.FileHandler(AUDIT_LOG_FILE)
audit_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
))
audit_logger.addHandler(audit_handler)

# Em routes/auth_routes.py:
audit_logger.info(f"LOGIN_SUCCESS | user={username} | ip={request.remote_addr}")
audit_logger.warning(f"LOGIN_FAILED | user={username} | ip={request.remote_addr}")
audit_logger.warning(f"PRIVILEGE_ESCALATION_ATTEMPT | user={user_id} | ip={request.remote_addr}")
```

**Prazo:** Melhorias contínuas  
**Impacto:** Mínimo (logging apenas)

---

## 📊 Plano de Ação

| Prioridade | Item | Prazo | Responsável | Status |
|-----------|------|-------|-------------|--------|
| CRÍTICA | 1. SQL Injection Whitelist | Imediato | Dev | ⏳ TODO |
| CRÍTICA | 2. Atualizar Dependências | Imediato | DevOps | ⏳ TODO |
| CRÍTICA | 3. Mascarar API Key em Logs | Imediato | Dev | ⏳ TODO |
| ALTA | 4. Rate Limiting Auth | 1 semana | Dev | ⏳ TODO |
| ALTA | 5. Reduzir Session Lifetime | 1 semana | Dev | ⏳ TODO |
| ALTA | 6. Configurar CORS (se needed) | 1 semana | Dev | ⏳ TODO |
| ALTA | 7. Remover Bare Excepts | 1 semana | Dev | ⏳ TODO |
| MÉDIA | 8. Documentar IDOR Checklist | Sprint 2 | Dev | ⏳ TODO |
| MÉDIA | 9. Validar Input (1-10) | Sprint 2 | Dev | ⏳ TODO |
| MÉDIA | 10. Genérica Erro Messages | Sprint 2 | Dev | ⏳ TODO |
| MÉDIA | 11. Validar Session vs DB | Sprint 2 | Dev | ⏳ TODO |
| BAIXA | 12. Refactor Reset Tokens | Sprint 3+ | Dev | ⏳ TODO |
| BAIXA | 13. Documentar Default Accounts | Sprint 3+ | Dev | ⏳ TODO |
| BAIXA | 14. Enable CSP | Sprint 3+ | Dev | ⏳ TODO |
| BAIXA | 15. Audit Logging | Sprint 3+ | Dev | ⏳ TODO |

---

## 🛡️ Checklist de Segurança para Deployments

Antes de cada deploy em produção, verificar:

- [ ] Todas as dependências estão atualizadas (`pip list | grep -i "jinja\|gunicorn"`)
- [ ] `SECRET_KEY` está definida em variável de ambiente (não hardcoded)
- [ ] `RESEND_API_KEY` está definida em variável de ambiente
- [ ] `SESSION_COOKIE_SECURE = True` em produção
- [ ] `DEBUG = False` em produção
- [ ] HTTPS está ativado (verificar `PREFERRED_URL_SCHEME = 'https'`)
- [ ] Rate limiting está ativo
- [ ] Logs não contêm tokens/chaves (buscar `Bearer` em logs)
- [ ] Todos os endpoints com ID verificam `user_id` (IDOR check)
- [ ] Nenhum `except:` sem especificação
- [ ] `.gitignore` exclui `.secrets/` e `data/users.json`

---

## 📞 Contatos de Segurança

**Reportar Vulnerabilidade:** security@natrave.pt (criar email)  
**Últimas Revisões:** 15/06/2026  
**Próxima Auditoria Planejada:** 15/09/2026 (trimestral)

---

## 🔗 Referências Externas

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/sql-syntax.html)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Versão:** 1.0  
**Próxima Revisão:** 15 de setembro de 2026

# 🔐 Checklist de Segurança - Referência Rápida

## Antes de Cada Deploy

```bash
# 1. Verificar dependências desatualizadas
pip list | grep -E "Jinja2|gunicorn|requests|Flask-WTF|psycopg2"

# 2. Validar que não há chaves no git
git log -p -S "RESEND_API_KEY\|SECRET_KEY\|password" -- . | head -20

# 3. Procurar por bare except
grep -r "except:" services/ routes/ --include="*.py" | grep -v "except.*as\|except.*:"

# 4. Verificar se .secrets está em .gitignore
cat .gitignore | grep -E "\.secrets|data/users"

# 5. Validar HTTPS em produção
grep -n "PREFERRED_URL_SCHEME\|SESSION_COOKIE_SECURE" config.py render.yaml
```

---

## Score de Segurança por Componente

| Componente | Status | Crítico | Alto | Médio | Baixo |
|-----------|--------|---------|------|-------|-------|
| **Autenticação** | 🟠 | ❌ Rate Limit | ❌ Session TTL | ✅ Validação | ✅ Default Accounts |
| **Database** | 🟠 | ⚠️ SQL Whitelist | ✅ Prepared Stmts | ✅ Encryption | ✅ Backup |
| **Dependências** | 🔴 | ❌ Jinja2/Gunicorn | ✅ Others | - | - |
| **Email/API** | 🔴 | ❌ Key Exposure | - | ✅ Timeout | - |
| **HTTP Headers** | 🟡 | ✅ CSRF | ✅ HSTS | ✅ Cache | ❌ CSP |
| **Input Validation** | 🟡 | ✅ IDOR Check | ⚠️ Type Cast | ❌ Bare Except | ✅ Limits |
| **Error Handling** | 🟡 | ✅ Try/Catch | ✅ Logging | ⚠️ Messages | ✅ Stacks |
| **Logging/Audit** | 🟡 | - | - | ❌ No Audit | ✅ Errors |

---

## 🚨 Vulnerabilidades por Tipo

### Injection
- ⚠️ SQL: Usar whitelist para nomes de tabela mesmo que hardcoded
- ✅ Command: Nenhuma detecção de execução de shell
- ✅ Template: Jinja2 auto-escapa HTML

### Authentication
- ❌ Rate Limiting: Brute force em `/login`, `/cadastro`, `/recuperar-senha`
- ✅ Passwords: Hash com werkzeug.security (bom!)
- ❌ Session TTL: 7 dias é muito (reduzir para 2h)
- ⚠️ Session Validation: Não valida contra BD (permite spoofing)

### Authorization
- ✅ IDOR: Protegido em `/jogador/<id>` e `/api/*`
- ✅ Admin: Verificado em rotas sensíveis
- ✅ Juiz: Fluxo bem documentado

### Data Protection
- ❌ API Keys: Resend key exposta em headers
- ⚠️ Credentials: Temp password salva em `.secrets/` (fichinha)
- ✅ HTTPS: Forcado em produção (render.yaml)
- ✅ Cookies: HttpOnly + Secure + SameSite

### Error Handling
- 🟡 Silent Failures: Alguns `except:` sem especificação
- 🟡 Info Leakage: Algumas mensagens genéricas, outras podem expor stack
- ✅ Logging: Bom coverage com logging.INFO

### Cryptography
- ✅ CSRF: CSRFProtect + tokens gerados
- ✅ Passwords: Werkzeug hash
- ✅ Sessions: Flask sessions com SECRET_KEY
- ❌ CSP: Desabilitado (unsafe-inline para scripts)

---

## 💡 Dicas de Desenvolvimento Seguro

### ✅ FAÇA ISTO

```python
# 1. Sempre validar entrada
try:
    nivel = int(request.form.get('nivel', 0))
    if not (1 <= nivel <= 10):
        raise ValueError()
except (ValueError, TypeError):
    return jsonify({'erro': 'Inválido'}), 400

# 2. Especificar exceções
try:
    data = json.load(f)
except (json.JSONDecodeError, FileNotFoundError) as e:
    logger.error(f"Error: {e}")

# 3. Checar autorização SEMPRE
if not _is_admin() and user_id != session.get('user_id'):
    abort(403)

# 4. Usar prepared statements
cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# 5. Mascarar credenciais em logs
logger.warning(f"API call failed: {url}")  # Não incluir Bearer token

# 6. Fazer rate limiting
@limiter.limit("5 per minute")
def login_submit():
    pass

# 7. Validar session em middleware
@app.before_request
def validate_session():
    if session.get('user_id'):
        if not auth_service.obter_por_id(session['user_id']):
            session.clear()
```

### ❌ NÃO FAÇA ISTO

```python
# 1. NÃO aceitar sem validação
nivel = int(request.form.get('nivel'))  # Pode falhar

# 2. NÃO usar bare except
try:
    pass
except:
    pass

# 3. NÃO expor dados de outros usuários
return jsonify(all_users)  # Deveria filtrar por user_id

# 4. NÃO interpolar variáveis em SQL
cur.execute(f"SELECT * FROM {table_name}")  # NUNCA!

# 5. NÃO logar credenciais
logger.info(f"Connecting to {api_key}")  # NUNCA!

# 6. NÃO confiar em session sem validar
role = session.get('role')  # Pode ter sido XSS-injetado

# 7. NÃO servir conteúdo antigo
response.headers['Cache-Control'] = 'no-cache'  # Para HTML sensível
```

---

## 🔍 Auditoria Rápida

Executar a cada 2 semanas:

```bash
#!/bin/bash
echo "🔐 Security Audit Report"
echo "========================"
echo ""

echo "1. Outdated Packages:"
pip list --outdated | grep -E "Jinja2|gunicorn|Flask|requests"

echo ""
echo "2. Hardcoded Secrets in Code:"
git log -p -S "password\|api_key\|secret" --all | grep -i "password\|api_key" | head -10

echo ""
echo "3. Bare Excepts:"
grep -r "except:" services/ routes/ --include="*.py" | wc -l

echo ""
echo "4. Missing Authentication:"
grep -r "@app.route\|@.*_bp.route" routes/ --include="*.py" | grep -v "login\|cadastro\|recuperar" | wc -l

echo ""
echo "5. Log Exposures (Bearer tokens):"
grep -r "Bearer\|password\|token" services/ --include="*.py" | grep "logger\|print" | wc -l

echo ""
echo "Done! Address any findings above."
```

---

## 📋 Matriz de Risco

```
                   IMPACTO
             Baixo    Médio    Alto    Crítico
PROBAB.    ┌─────────┬─────────┬─────────┬─────────┐
ALTA       │  Médio  │  ALTO   │ CRÍTICO │ CRÍTICO │
           ├─────────┼─────────┼─────────┼─────────┤
MÉDIA      │  Baixo  │ Médio   │  ALTO   │ CRÍTICO │
           ├─────────┼─────────┼─────────┼─────────┤
BAIXA      │  Baixo  │ Baixo   │ Médio   │  ALTO   │
           ├─────────┼─────────┼─────────┼─────────┤
MUI BAIXA  │  Baixo  │ Baixo   │ Baixo   │ Médio   │
           └─────────┴─────────┴─────────┴─────────┘
```

---

## 📞 Reportar Vulnerabilidade

Se encontrar um problema de segurança:

1. **NÃO** poste em issues públicas
2. **ENVIE** para `security@natrave.com` (TODO: criar)
3. **INCLUA:**
   - Descrição do problema
   - Arquivo e linha
   - Impacto (what if someone exploits?)
   - Sugestão de fix (opcional)
4. **AGUARDE** resposta em até 48h

---

## 📚 Referências Rápidas

- [OWASP Top 10](https://owasp.org/Top10/) - Vulnerabilidades mais comuns
- [Flask Security](https://flask.palletsprojects.com/security/) - Best practices Flask
- [CWE](https://cwe.mitre.org/) - Fraquezas comuns de software
- [Burp Suite Community](https://portswigger.net/burp/communitydownload) - Teste penetração

---

**Última Atualização:** 15/06/2026  
**Próxima Revisão:** 15/09/2026

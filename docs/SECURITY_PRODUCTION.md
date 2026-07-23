# 🚀 Guia de Segurança em Produção

**Público:** Engenheiros de produção, DevOps, admin  
**Atualizado:** 15/06/2026

---

## 📌 TL;DR - Cuidados Críticos

Se você só tiver 2 minutos, leia isto:

### Antes de Fazer Deploy
1. ✅ `pip install --upgrade Jinja2 gunicorn` (vulnerabilidades críticas)
2. ✅ Confirmar variáveis de ambiente: `RESEND_API_KEY`, `DATABASE_URL`, `SECRET_KEY`
3. ✅ Garantir `HTTPS` ativado e `DEBUG=False`
4. ✅ Verificar que `.secrets/` não está em git
5. ✅ Rodar testes: `pytest -v tests/`

### Se Encontrar um Bug de Segurança
1. **NUNCA** commitar fix diretamente na main
2. **CRIAR** branch: `git checkout -b hotfix/security-xyz`
3. **TESTAR** localmente com dados de staging
4. **REVISAR** com pelo menos 1 pessoa
5. **FAZER** deploy somente com aprovação

---

## 🔐 Variáveis de Ambiente Críticas

**NUNCA** commitar estas em code:

```bash
# .env.production (NÃO VERSIONADO, somente em produção)
SECRET_KEY="gerar com: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
DATABASE_URL="postgresql://user:pass@host:5432/dbname"
RESEND_API_KEY="re_xyz123..."
WEB_CONCURRENCY=2
WEB_THREADS=4
GUNICORN_TIMEOUT=60
DB_CONNECT_TIMEOUT=5
PGSSLMODE="require"
FLASK_ENV="production"
DEBUG="False"
```

**Verificação:**
```bash
# Confirmar que não há secrets no código
git log -p --all -S "RESEND_API_KEY\|DATABASE_URL" -- . | head -5

# Se encontrou, fazer:
git filter-branch --tree-filter 'rm -f .env' HEAD
# (Reescrita de histórico - usar com cuidado!)
```

---

## 🏥 Saúde da Aplicação

### Health Check (adicionar em produção)

```python
# No app.py, adicionar:
@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    }), 200
```

Configurar no Render:
```yaml
# render.yaml
healthCheckPath: /health
```

### Monitoramento de Segurança

```bash
# Logs com erros de segurança
tail -f logs/app.log | grep -E "CSRF|Failed login|UNAUTHORIZED"

# Verificar Rate Limiting está ativo
curl -i -X POST http://localhost:5000/login
# Deve incluir: X-RateLimit-Limit: 5

# Certificado SSL em produção
openssl s_client -connect natrave.render.com:443 -showcerts
```

---

## 🔑 Gestão de Credenciais

### Nunca Faça Isto:
```python
# ❌ ERRADO - em produção
RESEND_API_KEY = "re_xyz123"

# ❌ ERRADO - no .env versionado
RESEND_API_KEY=re_xyz123

# ❌ ERRADO - em comentário
# Use sua chave: re_xyz123
```

### Sempre Faça Isto:
```python
# ✅ CORRETO - em config.py
import os
RESEND_API_KEY = os.getenv('RESEND_API_KEY')

if not RESEND_API_KEY:
    raise ValueError("Missing RESEND_API_KEY environment variable")

# ✅ CORRETO - em .env.production (não versionado)
# FILE: .env.production
# OWNER: root
# PERMISSIONS: 600
RESEND_API_KEY=re_xyz123

# ✅ CORRETO - em .gitignore
.env
.env.*
.secrets/
```

### Rotação de Chaves

Quando mudar `RESEND_API_KEY` ou `SECRET_KEY`:

1. Gerar nova chave:
   ```bash
   python -c 'import secrets; print(secrets.token_urlsafe(32))'
   ```

2. Atualizar em Render:
   - Dashboard → Environment
   - Colar nova chave
   - Deploy automático ativa com nova config

3. **Para SECRET_KEY em especial:**
   - Todas as sessões ativas serão invalidadas
   - Usuários precisarão fazer login novamente
   - Combinar com redução de SESSION_LIFETIME se possível

---

## 🛡️ HTTPS e Certificados

### Verificar HTTPS em Produção
```bash
# Deve redirecionar HTTP → HTTPS
curl -i http://natrave.render.com/
# Expect: 301 Moved Permanently
# Location: https://natrave.render.com/

# Deve servir HTTPS
curl -i https://natrave.render.com/
# Expect: 200 OK + "Strict-Transport-Security"
```

### Headers de Segurança
```bash
# Verificar que todos os headers estão presentes
curl -i https://natrave.render.com/ | grep -E "Strict-Transport-Security|X-Content-Type-Options|X-Frame-Options|CSP"

# Esperado:
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# Content-Security-Policy: ...
```

### Certificado SSL
```bash
# Expiração de certificado
echo | openssl s_client -servername natrave.render.com -connect natrave.render.com:443 2>/dev/null | openssl x509 -noout -dates

# Deve mostrar datas válidas
# notBefore: ... 
# notAfter: ...

# Alerta: Render renova automaticamente, mas verificar monthly
```

---

## 🚨 Resposta a Incidentes

### Se Descobrir SQL Injection
1. **IMEDIATO:** Desabilitar aplicação (return 503 Service Unavailable)
2. **DENTRO DE 30 MIN:** Investigar logs para ver se foi explorada
3. **DENTRO DE 1H:** Deploy de hotfix com input validation
4. **NOTIFICAR:** Todos os usuários se dados foram acessados

### Se Descobrir Credencial Exposta
1. **IMEDIATO:** Revogar credencial no Resend/PostreSQL
2. **DENTRO DE 15 MIN:** Deploy com nova credencial
3. **AUDITORIA:** Verificar logs de quando foi criada/exposta
4. **NOTIFICAR:** Security team

### Se Descobrir Account Takeover
1. **IMEDIATO:** Resetar password de admin afetado
2. **AUDIT:** Ver quais dados foram acessados
3. **CONTATAR:** Usuário afetado
4. **MONITOR:** Atividade suspeita nos logs

---

## 🔍 Auditoria Mensal

Executar no primeiro dia útil de cada mês:

```bash
#!/bin/bash
# audit-security.sh

echo "🔐 MONTHLY SECURITY AUDIT"
echo "========================="
echo ""

# 1. Dependências
echo "1. OUTDATED PACKAGES:"
pip list --outdated

echo ""
echo "2. DATABASE CONNECTION:"
psql "$DATABASE_URL" -c "SELECT current_database(), current_user, now();"

echo ""
echo "3. FAILED LOGINS (last 24h):"
grep "LOGIN_FAILED" logs/audit.log | tail -20

echo ""
echo "4. CERTIFICATE EXPIRY:"
echo | openssl s_client -servername natrave.render.com -connect natrave.render.com:443 2>/dev/null | openssl x509 -noout -dates

echo ""
echo "5. DISK USAGE:"
du -sh logs/ data/

echo ""
echo "AUDIT COMPLETE - Check items above"
```

---

## 🚀 Deploy Seguro - Checklist

Antes de cada deploy:

```bash
# 1. Validar Branch
[ "$(git rev-parse --abbrev-ref HEAD)" == "main" ] || exit 1

# 2. Pull Latest
git pull origin main

# 3. Testes Passam
python -m pytest tests/ -v || exit 1

# 4. Vulnerabilidades em Dependências
pip-audit || exit 1

# 5. Linting
flake8 . || exit 1

# 6. Secrets Não Estão Commitados
! git log -p -n 1 | grep -E "password|api_key|secret" || exit 1

# 7. Build Docker (se aplicável)
docker build -t natrave:latest .

# 8. Deploy para Staging
# Fazer testes em staging.natrave.render.com

# 9. Deploy para Produção
git push origin main  # Render auto-deploy
```

---

## 📊 Logs Críticos a Monitorar

### Segurança
```bash
# Buscar tentativas de brute force
grep "LOGIN_FAILED" logs/audit.log | cut -d' ' -f5 | sort | uniq -c | sort -rn

# Buscar CSRF errors
grep "CSRF" logs/app.log | tail -10

# Buscar acesso não autorizado
grep "UNAUTHORIZED\|403" logs/app.log | tail -10
```

### Performance
```bash
# Requests lentos
grep "duration=" logs/app.log | awk -F'duration=' '{print $2}' | sort -rn | head -10

# Database timeouts
grep "timeout\|connect_timeout" logs/app.log
```

### Erros
```bash
# Exceções não tratadas
grep "ERROR\|Exception" logs/app.log | tail -20

# Silent failures
grep "except:" services/*.py routes/*.py
```

---

## 🔧 Recuperação de Desastre

### Se o Banco de Dados Ficar Inacessível
```bash
# 1. Aplicação fallback para JSON local
# Já implementado - logs dirão "Using local JSON store"

# 2. Verificar timeout do BD
echo $DB_CONNECT_TIMEOUT

# 3. Se BD foi deletado acidentalmente:
# - Restaurar de backup automático
# - Render mantém backups dos últimos 7 dias
```

### Se a Aplicação Ficar Lenta
```bash
# 1. Verificar Gunicorn workers
ps aux | grep gunicorn

# 2. Verificar carga do servidor
top -b -n 1 | head -20

# 3. Aumentar workers em render.yaml:
# startCommand: "gunicorn --workers 4 --threads 4 --timeout 60 wsgi:app"

# 4. Monitorar banco de dados
psql $DATABASE_URL -c "SELECT * FROM pg_stat_activity;"
```

### Se Houver Secret Key Comprometida
```bash
# 1. Gerar nova chave
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# 2. Atualizar em Render dashboard
# Todas as sessões serão invalidadas

# 3. Notificar usuários
# Email: "Você foi desconectado por motivos de segurança"
```

---

## 📞 Escalation e Contatos

### Security Issues (Crítico)
- **Slack:** #security-incidents
- **Email:** security@natrave.pt
- **Escalate para:** Tech Lead dentro de 30 min

### Production Issues (Urgente)
- **Slack:** #production-alerts
- **On-call:** Consultar Schedule Runbook
- **Escalate se:** Mais de 1% de erro rate por 5 min

### Configurações/Dúvidas
- **Slack:** #devops
- **Docs:** `/docs/SECURITY_AUDIT.md`
- **Resposta esperada:** Próximo dia útil

---

## ✅ Primeiro Deploy em Produção - Checklist Completo

Se este é o seu primeiro deploy em produção:

- [ ] Variáveis de ambiente configuradas em Render
- [ ] Banco de dados PostgreSQL criado
- [ ] `.gitignore` inclui `.env`, `.secrets/`, `data/users.json`
- [ ] `DEBUG = False` em production config
- [ ] `HTTPS` ativado (render.yaml force_https)
- [ ] Certificado SSL válido (auto-gerado pelo Render)
- [ ] Health check em `/health` respondendo
- [ ] Logs sendo coletados em `logs/` ou stdout
- [ ] Rate limiting ativado
- [ ] CSRF protection ativado
- [ ] Session cookies com `Secure`, `HttpOnly`, `SameSite`
- [ ] Email service (Resend) testado com conta real
- [ ] Backup automático de BD configurado
- [ ] Monitoramento/alerts configurados
- [ ] Runbook de incidentes criado
- [ ] On-call schedule definido
- [ ] Versão da aplicação identificada (git tag)

---

**Última Revisão:** 15/06/2026  
**Próxima Revisão:** 15/09/2026  
**Mantido por:** Security Team

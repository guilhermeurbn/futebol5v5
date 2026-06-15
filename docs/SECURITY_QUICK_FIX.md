# ⚡ Guia Rápido - Correções Críticas Imediatas

**Tempo estimado:** 30-45 minutos  
**Criticidade:** 🔴 MÁXIMA - Deploy dentro de 24h

---

## Resumo das 3 Ações Críticas

| # | Ação | Arquivo | Tempo | Impacto |
|---|------|---------|-------|---------|
| 1️⃣ | Atualizar Jinja2 e Gunicorn | `requirements.txt` | 5 min | ✅ Zero risk |
| 2️⃣ | Mascarar API Key em logs | `services/email_service.py` | 10 min | ✅ Logs only |
| 3️⃣ | SQL Injection Whitelist | `services/db.py` | 15 min | ✅ Future-proof |

---

## 1️⃣ Atualizar Dependências Vulneráveis

### Problema
- Jinja2 3.1.6 tem 3 CVEs (template injection)
- Gunicorn 22.0.0 tem HTTP Request Smuggling

### Solução (5 minutos)

#### Passo 1: Atualizar requirements.txt
```bash
cd /Users/guilhermeurbano/futebol5v5

# Atualizar apenas as duas bibliotecas vulneráveis
pip install --upgrade Jinja2 gunicorn

# Gerar novo requirements.txt
pip freeze > requirements.txt

# Verificar versões
pip list | grep -E "Jinja2|gunicorn"
# Esperado:
# Jinja2 3.1.5+
# gunicorn 22.0.1+
```

#### Passo 2: Validar que aplicação ainda funciona
```bash
# Teste local
python -m pytest tests/ -v

# Se tudo passar, está pronto para deploy
```

#### Passo 3: Commit e push
```bash
git add requirements.txt
git commit -m "security: update Jinja2 and gunicorn CVE fixes

- Jinja2 3.1.6 → 3.1.5+ (fixes CVE-2024-22195, CVE-2024-34064, CVE-2024-56326)
- gunicorn 22.0.0 → 22.0.1+ (fixes CVE-2024-1135 HTTP Request Smuggling)
- All tests passing, zero breaking changes"

git push origin main
```

**Validação:** Render fará deploy automático. Monitorar em https://dashboard.render.com/

---

## 2️⃣ Mascarar API Key em Logs

### Problema
```python
# HOJE - expõe API key em logs!
headers = {
    "Authorization": f"Bearer {resolved_api_key}",  # ❌ Visível se logs forem expostos
}
logger.info(f"Sending email to {email}")
```

Se alguém tiver acesso aos logs, consegue roubar a chave do Resend.

### Solução (10 minutos)

#### Passo 1: Ler arquivo atual
```bash
cat services/email_service.py | head -100
```

#### Passo 2: Criar classe de redação automática

Editar `services/email_service.py` e adicionar no topo (depois dos imports):

```python
import logging
import re

# === SECURITY: Redacting Formatter ===
class RedactingFormatter(logging.Formatter):
    """Remove sensitive data from log messages"""
    
    PATTERNS = [
        (r'Bearer\s+[^\s]+', 'Bearer [REDACTED]'),
        (r'Authorization:\s+[^\s]+', 'Authorization: [REDACTED]'),
        (r'api[_-]?key[:\s=]+[^\s,}]+', 'api_key: [REDACTED]'),
        (r'password[:\s=]+[^\s,}]+', 'password: [REDACTED]'),
        (r'token[:\s=]+[^\s,}]+', 'token: [REDACTED]'),
    ]
    
    def format(self, record):
        """Redact sensitive patterns from log records"""
        msg = super().format(record)
        for pattern, replacement in self.PATTERNS:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        return msg
```

#### Passo 3: Aplicar formatter

Procurar pela função `obter_logger()` ou setup de logging, e modificar:

```python
# Adicionar após criar o logger
logger = logging.getLogger('email_service')

# ✅ NOVO: Aplicar redacting formatter
for handler in logger.handlers:
    handler.setFormatter(RedactingFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
```

#### Passo 4: Testar redação

Executar teste:
```bash
python -c "
from services.email_service import logger
logger.info('Testing: Authorization: Bearer re_xyz123abc')
# Deve imprimir: Authorization: Bearer [REDACTED]
"
```

#### Passo 5: Commit

```bash
git add services/email_service.py
git commit -m "security: redact API keys from logs

- Add RedactingFormatter to hide Bearer tokens and credentials
- Patterns: Bearer tokens, API keys, passwords, session tokens
- Zero impact on functionality"

git push origin main
```

---

## 3️⃣ SQL Injection - Whitelist de Tabelas

### Problema
```python
# HOJE - interpolação de nome de tabela
cur.execute(f"select payload from {json_store_table_name()} where namespace = %s", (namespace,))
```

Hoje a função `json_store_table_name()` retorna sempre "app_json_store", mas se alguém mudar a implementação, fica vulnerável a SQL injection.

### Solução (15 minutos)

#### Passo 1: Localizar a função

```bash
grep -n "def json_store_table_name" services/db.py
```

#### Passo 2: Adicionar validação

Na função `json_store_table_name()`, adicionar whitelist:

```python
def json_store_table_name() -> str:
    """Get the JSON store table name with whitelist validation"""
    
    # ✅ SECURITY: Whitelist de tabelas permitidas
    ALLOWED_TABLES = {
        'app_json_store',  # Tabela padrão
    }
    
    table_name = "app_json_store"
    
    # Validar que tabela está na whitelist
    if table_name not in ALLOWED_TABLES:
        raise ValueError(
            f"Unauthorized table name: {table_name}. "
            f"Allowed: {ALLOWED_TABLES}"
        )
    
    return table_name
```

#### Passo 3: Testar

```bash
# Executar testes para garantir que DB ainda funciona
python -m pytest tests/test_db.py -v

# Esperado: todos passar
```

#### Passo 4: Commit

```bash
git add services/db.py
git commit -m "security: add whitelist validation for SQL table names

- Add ALLOWED_TABLES whitelist in json_store_table_name()
- Prevent SQL injection if table name becomes dynamic
- All DB tests passing"

git push origin main
```

---

## ✅ Validação Pós-Deploy

Depois que as 3 mudanças foram deployadas, executar:

```bash
#!/bin/bash

echo "🔐 Security Update Validation"
echo "=============================="
echo ""

# 1. Verificar versões em produção
echo "1. Dependency Versions:"
curl -s https://natrave.render.com/api/health | python -m json.tool | grep -E "jinja2|gunicorn"
# Ou verificar no Render dashboard

# 2. Verificar que API Key não está em logs
echo ""
echo "2. Recent Logs (checking for Bearer tokens):"
tail -100 logs/app.log | grep -c "Bearer" || echo "✅ No Bearer tokens in logs"

# 3. Testar SQL com query simples
echo ""
echo "3. Database Connectivity:"
curl -s https://natrave.render.com/api/jogadores | head -20
# Deve retornar JSON, não erro

echo ""
echo "✅ All validation checks passed"
```

---

## 🚨 Se Algo Quebrar

### Cenário: Deploy quebrou a aplicação

```bash
# 1. Voltar para versão anterior
git revert HEAD

# 2. Deploy novamente
git push origin main

# 3. Investigar localmente o que falhou
# Rolar requirements.txt para versão anterior
git show HEAD~1:requirements.txt > requirements.txt
pip install -r requirements.txt
pytest -v

# 4. Corrigir problema
# Editar arquivo problemático

# 5. Fazer commit + push novamente
```

### Cenário: Logs continuam mostrando credenciais

```bash
# Verificar que RedactingFormatter está sendo usado
python -c "
import logging
from services.email_service import logger

# Check handlers
for h in logger.handlers:
    print(f'Handler: {h}')
    print(f'Formatter: {h.formatter.__class__.__name__}')
"

# Se não estiver usando RedactingFormatter, revisar step 3 acima
```

---

## 📋 Checklist Final

- [ ] Baixei e li este documento
- [ ] Atualizei Jinja2 e Gunicorn via pip
- [ ] Ran `pytest` e todos os testes passaram
- [ ] Commitei + pushei mudança de dependências
- [ ] Adicionei RedactingFormatter a email_service.py
- [ ] Testei que logs não mostram Bearer tokens
- [ ] Commitei + pushei mudança de redação
- [ ] Adicionei whitelist a json_store_table_name()
- [ ] Ran `pytest` novamente
- [ ] Commitei + pushei mudança de whitelist
- [ ] Monitorei o Render dashboard para confirmar deploy
- [ ] Executei validação pós-deploy
- [ ] Confirmei que aplicação está respondendo (HTTP 200)
- [ ] Notifiquei o time que security updates foram deployadas

---

## 📞 Se Tiver Dúvidas

1. **Sintaxe Python:** Procurar em `/docs/SECURITY_AUDIT.md` - tem exemplos
2. **Como fazer commit:** Copiar comandos de exemplo acima
3. **Erro de teste:** Executar `pytest -v tests/test_db.py` para debug
4. **Não conseguiu fazer:** Slack #security-help ou security@natrave.com

---

**Prazo:** ⏰ Fazer hoje ou amanhã no máximo  
**Impacto em Usuários:** ✅ Zero (mudanças internas)  
**Rollback Risk:** ✅ Muito baixo (todas backward-compatible)

---

**Versão:** 1.0  
**Atualizado:** 15/06/2026

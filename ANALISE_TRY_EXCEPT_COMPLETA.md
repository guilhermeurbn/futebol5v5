# ANÁLISE COMPLETA: TRY/EXCEPT GENÉRICOS ENCONTRADOS

## TAREFA 2: Remover try/except Genéricos ❌

### 1. app.py - CRÍTICO

**Linha 12-14**: Try/except silencioso
```python
try:
    from flask_wtf import CSRFProtect
    from flask_wtf.csrf import generate_csrf
except Exception:  # ❌ Silencia TODOS os erros
    CSRFProtect = None
    generate_csrf = None
```
**Problema**: Não registra nada, impossível debugar
**Solução**: Capturar ImportError especificamente
```python
try:
    from flask_wtf import CSRFProtect
    from flask_wtf.csrf import generate_csrf
except ImportError as e:
    logger.warning(f"Flask-WTF não instalado: {e}")
    CSRFProtect = None
    generate_csrf = None
```

---

**Linha 16-18**: Try/except silencioso (Talisman)
```python
try:
    from flask_talisman import Talisman
except Exception:  # ❌ Silencia TODOS os erros
    Talisman = None
```
**Solução**:
```python
try:
    from flask_talisman import Talisman
except ImportError as e:
    logger.warning(f"Flask-Talisman não instalado: {e}")
    Talisman = None
```

---

**Linha 68-70**: Try/except genérico com warning inadequado
```python
try:
    Talisman(app, content_security_policy=None)
except Exception as e:
    logger.warning(f"Falha ao iniciar Talisman: {e}")
```
**Problema**: Deveria ser `logger.error()` não `warning()`
**Solução**:
```python
try:
    Talisman(app, content_security_policy=None)
except RuntimeError as e:
    logger.error(f"Erro ao iniciar Talisman: {e}")
    raise
except Exception as e:
    logger.error(f"Erro inesperado ao iniciar Talisman: {e}")
    raise
```

---

**Linha 84-86**: Try/except genérico no seed
```python
try:
    auto_seed_on_init()
except Exception as e:
    logger.warning(f"Erro ao fazer seed do banco: {e}")
```
**Problema**: Warning deveria ser Error, não registra traceback
**Solução**:
```python
try:
    auto_seed_on_init()
except ValueError as e:
    logger.error(f"Erro de validação ao fazer seed: {e}")
except DatabaseError as e:
    logger.error(f"Erro de banco ao fazer seed: {e}")
except Exception as e:
    logger.exception(f"Erro inesperado ao fazer seed: {e}")
```

---

### 2. services/auth_service.py

**Linha 74-77**: Try/except silencioso
```python
try:
    os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
    creds_file = os.path.join('.secrets', 'initial_admin_credentials.json')
    with open(creds_file, 'w', encoding='utf-8') as cf:
        json.dump(created_credentials, cf, indent=2, ensure_ascii=False)
except Exception:  # ❌ Silencia TODOS os erros
    pass
```
**Problema**: SILENCIA erros críticos! Credenciais podem não ser salvas
**Solução**:
```python
try:
    os.makedirs(os.path.dirname(self.arquivo), exist_ok=True)
    creds_file = os.path.join('.secrets', 'initial_admin_credentials.json')
    with open(creds_file, 'w', encoding='utf-8') as cf:
        json.dump(created_credentials, cf, indent=2, ensure_ascii=False)
except PermissionError as e:
    logger.error(f"Permissão negada ao salvar credenciais: {e}")
except (OSError, IOError) as e:
    logger.error(f"Erro ao salvar credenciais iniciais: {e}")
except json.JSONEncodeError as e:
    logger.error(f"Erro ao serializar credenciais: {e}")
except Exception as e:
    logger.exception(f"Erro inesperado ao salvar credenciais: {e}")
```

---

### 3. services/db.py

**Linha 9-11**: Try/except silencioso
```python
try:
    import psycopg2
    from psycopg2.extras import Json
except Exception:  # ❌ Silencia TODOS os erros
    psycopg2 = None
    Json = None
```
**Solução**:
```python
try:
    import psycopg2
    from psycopg2.extras import Json
except ImportError as e:
    logger.warning(f"psycopg2 não instalado, usando apenas arquivos locais: {e}")
    psycopg2 = None
    Json = None
```

---

**Linha 83-85**: Try/except genérico em load_json_data
```python
try:
    # ... carregar do Postgres ...
except Exception as e:
    print(f"[DB] Error loading from Postgres: {e}")  # ❌ print() em vez de logger
finally:
    if conn:
        conn.close()
```
**Problema**: Usa `print()` em vez de `logger`, não registra tipo de erro
**Solução**:
```python
try:
    # ... carregar do Postgres ...
except psycopg2.DatabaseError as e:
    logger.error(f"Erro de banco ao carregar dados: {e}")
except psycopg2.OperationalError as e:
    logger.error(f"Erro operacional ao carregar dados: {e}")
except Exception as e:
    logger.exception(f"Erro inesperado ao carregar dados: {e}")
finally:
    if conn:
        conn.close()
```

---

**Linha 130-132**: Try/except genérico em save_json_data
```python
try:
    # ... salvar no Postgres ...
except Exception as e:
    print(f"[DB] Error saving to Postgres: {e}")
finally:
    conn.close()
```
**Solução**: Mesma aplicação acima

---

### 4. services/jogador_stats_service.py

**Linha 193-227**: Try/except genérico que SILENCIA erros
```python
try:
    # ... calcular stats complexas ...
    stats["historico_partidas"].sort(...)
    return stats
except Exception as e:
    # Se houver erro, retornar stats vazio em vez de quebrar a aplicação
    import sys
    print(f"Erro ao calcular stats para {nome_jogador}: {str(e)}", file=sys.stderr)
    return { ... stats vazio ... }
```
**Problema**: Retorna stats vazio mascarando o erro, impede debugging
**Solução**:
```python
try:
    # ... calcular stats complexas ...
    stats["historico_partidas"].sort(...)
    return stats
except KeyError as e:
    logger.error(f"Campo faltando em stats para {nome_jogador}: {e}")
    raise ValueError(f"Dados inconsistentes para jogador {nome_jogador}")
except ValueError as e:
    logger.error(f"Erro de validação em stats para {nome_jogador}: {e}")
    raise
except Exception as e:
    logger.exception(f"Erro inesperado ao calcular stats para {nome_jogador}: {e}")
    raise
```

---

**Linha 413-417**: Try/except genérico sem logging
```python
try:
    with open(self.partidas_arquivo, "w", encoding="utf-8") as f:
        json.dump(partidas, f, indent=2, ensure_ascii=False)
    return True
except Exception:  # ❌ Sem logging!
    return False
```
**Problema**: Não dá feedback do que falhou
**Solução**:
```python
try:
    with open(self.partidas_arquivo, "w", encoding="utf-8") as f:
        json.dump(partidas, f, indent=2, ensure_ascii=False)
    return True
except (OSError, IOError) as e:
    logger.error(f"Erro ao salvar partidas: {e}")
    return False
except json.JSONEncodeError as e:
    logger.error(f"Erro ao serializar partidas: {e}")
    return False
except Exception as e:
    logger.exception(f"Erro inesperado ao salvar partidas: {e}")
    return False
```

---

### 5. run.py

**Linha 55-60**: Try/except genérico
```python
try:
    import importlib.metadata
    flask_version = importlib.metadata.version("flask")
    print(f"{VERDE}✅ Flask {flask_version}{RESET}")
except Exception:  # ❌ Genérico
    try:
        import flask
        print(f"{VERDE}✅ Flask (versão não detectada){RESET}")
    except ImportError:
        print(f"{VERMELHO}❌ Flask não instalado{RESET}")
        return False
```
**Problema**: Genérico demais
**Solução**:
```python
try:
    import importlib.metadata
    flask_version = importlib.metadata.version("flask")
    print(f"{VERDE}✅ Flask {flask_version}{RESET}")
except importlib.metadata.PackageNotFoundError:
    try:
        import flask
        print(f"{VERDE}✅ Flask (versão não detectada){RESET}")
    except ImportError as e:
        logger.error(f"Flask não instalado: {e}")
        print(f"{VERMELHO}❌ Flask não instalado{RESET}")
        return False
except Exception as e:
    logger.exception(f"Erro ao verificar Flask: {e}")
    print(f"{VERMELHO}❌ Erro ao verificar Flask{RESET}")
    return False
```

---

**Linha 148-159**: Try/except genérico
```python
try:
    from app import app
    app.run(debug=app.config.get('DEBUG', False), host='0.0.0.0', port=porta)
except KeyboardInterrupt:
    print(f"\n{AMARELO}⏹️  Servidor interrompido pelo usuário{RESET}\n")
    return 0
except Exception as e:
    print(f"{VERMELHO}❌ Erro ao iniciar servidor:{RESET}")
    print(f"{VERMELHO}{str(e)}{RESET}\n")
    return 1
```
**Problema**: Exceção genérica não dá detalhe suficiente
**Solução**:
```python
try:
    from app import app
    app.run(debug=app.config.get('DEBUG', False), host='0.0.0.0', port=porta)
except KeyboardInterrupt:
    logger.info("Servidor interrompido pelo usuário")
    print(f"\n{AMARELO}⏹️  Servidor interrompido pelo usuário{RESET}\n")
    return 0
except OSError as e:
    if e.errno == 98:  # Address already in use
        logger.error(f"Porta {porta} já está em uso")
        print(f"{VERMELHO}❌ Porta {porta} já está em uso{RESET}\n")
    else:
        logger.error(f"Erro ao iniciar servidor (SO): {e}")
        print(f"{VERMELHO}❌ Erro ao iniciar servidor: {e}{RESET}\n")
    return 1
except ValueError as e:
    logger.error(f"Configuração inválida do servidor: {e}")
    print(f"{VERMELHO}❌ Erro ao iniciar servidor: {e}{RESET}\n")
    return 1
except Exception as e:
    logger.exception(f"Erro inesperado ao iniciar servidor")
    print(f"{VERMELHO}❌ Erro ao iniciar servidor:{RESET}")
    print(f"{VERMELHO}{str(e)}{RESET}\n")
    return 1
```

---

### 6. routes/jogador_routes.py (ANTIGO)

**Linha 583-589**: Try/except genérico
```python
try:
    if not _is_admin():
        meus = jogador_service.listar_por_usuario(session.get('user_id'))
        # ...
except Exception as e:
    # Se houver erro ao obter stats, continuar sem elas
    import sys
    print(f"Erro ao obter stats do perfil: {str(e)}", file=sys.stderr)
    stats_jogador = None
```
**✅ JÁ REFATORADO** em auth_routes.py

---

**Linha 1090-1099**: Try/except genérico
```python
try:
    # ... criar jogador ...
except ValueError as e:
    return jsonify({'sucesso': False, 'erro': str(e)}), 400
except Exception as e:  # ❌ Genérico muito amplo
    return jsonify({'sucesso': False, 'erro': 'Erro ao criar jogador'}), 500
```
**✅ JÁ REFATORADO** em jogador_crud_routes.py

---

### 7. scripts/seed_railway.py

**Linha 36-39**: Try/except genérico
```python
try:
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    save_json_data(namespace, data)
    print(f"✓ Seeded {namespace}: ...")
except Exception as e:
    print(f"✗ Error seeding {namespace}: {e}")
```
**Solução**:
```python
try:
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    save_json_data(namespace, data)
    print(f"✓ Seeded {namespace}: ...")
except json.JSONDecodeError as e:
    logger.error(f"JSON inválido em {namespace}.json: {e}")
    print(f"✗ JSON inválido em {namespace}.json: {e}")
except (OSError, IOError) as e:
    logger.error(f"Erro ao ler arquivo {namespace}.json: {e}")
    print(f"✗ Erro ao ler {namespace}.json: {e}")
except ValueError as e:
    logger.error(f"Erro ao salvar {namespace}: {e}")
    print(f"✗ Erro ao salvar {namespace}: {e}")
except Exception as e:
    logger.exception(f"Erro inesperado ao fazer seed de {namespace}")
    print(f"✗ Erro inesperado com {namespace}: {e}")
```

---

### 8. scripts/exemplos_api.py

**Linha 95-102**: Try/except genérico
```python
try:
    # ... fazer exemplos ...
except requests.exceptions.ConnectionError:
    print("\n❌ Erro: Servidor não está rodando")
    # ...
except Exception as e:
    print(f"\n❌ Erro: {str(e)}\n")
```
**Solução**:
```python
try:
    # ... fazer exemplos ...
except requests.exceptions.ConnectionError as e:
    logger.error(f"Conexão recusada: {e}")
    print("\n❌ Erro: Servidor não está rodando\n")
except requests.exceptions.HTTPError as e:
    logger.error(f"Erro HTTP: {e}")
    print(f"\n❌ Erro HTTP: {e}\n")
except requests.exceptions.RequestException as e:
    logger.error(f"Erro na requisição: {e}")
    print(f"\n❌ Erro na requisição: {e}\n")
except ValueError as e:
    logger.error(f"Erro de validação: {e}")
    print(f"\n❌ Erro de validação: {e}\n")
except Exception as e:
    logger.exception(f"Erro inesperado")
    print(f"\n❌ Erro inesperado: {str(e)}\n")
```

---

### 9. scripts/utils.py

**Linha 22-24**: Try/except correto, mas pode ser melhorado
```python
try:
    # ... validação ...
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    return jsonify({'sucesso': False, 'erro': 'Erro interno do servidor'}), 500
```
**✅ ACEITÁVEL** - mas deveria capturar erros específicos primeiro

---

## SUMMARY - CUSTOM EXCEPTIONS A CRIAR

Para melhorar o tratamento de erros, criar exceções customizadas:

```python
# services/exceptions.py

class NaTraveException(Exception):
    """Exceção base para o projeto"""
    pass

class ValidationError(NaTraveException):
    """Erro de validação de dados"""
    pass

class DatabaseError(NaTraveException):
    """Erro ao acessar banco de dados"""
    pass

class AuthenticationError(NaTraveException):
    """Erro de autenticação"""
    pass

class AuthorizationError(NaTraveException):
    """Erro de autorização"""
    pass

class NotFoundError(NaTraveException):
    """Recurso não encontrado"""
    pass

class ConfigurationError(NaTraveException):
    """Erro de configuração"""
    pass
```

---

## TOTAL DE ISSUES ENCONTRADAS

- ❌ **CRÍTICA**: 4 (silenciam erros completamente)
- ⚠️ **ALTA**: 8 (não registram logging adequado)
- 📌 **MÉDIA**: 10 (genéricos demais)
- ✅ **REFERÊNCIA**: 15+ (refatorados nos novos módulos)

**Total de try/except genéricos**: ~37 encontrados
**Recomendação**: Procurar por padrão "except Exception" em toda codebase

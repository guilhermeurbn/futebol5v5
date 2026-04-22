# 🔧 Solução de Problemas - Porta 5000 em Uso

## Problema
A porta 5000 está sendo usada por outro serviço (geralmente AirPlay Receiver no macOS).

## ✅ Solução 1: Automática (Recomendado)
O script `run.py` foi atualizado para usar automaticamente a porta **5001** se 5000 estiver ocupada:

```bash
python run.py
```

Você verá:
```
⚠️  Porta 5000 já está em uso (provavelmente AirPlay Receiver)
Usando porta alternativa: 5001

⚽ Servidor rodando em: http://localhost:5001
```

---

## ✅ Solução 2: Desabilitar AirPlay Receiver (macOS)

Se você não usa AirPlay, desabilite:

1. Abra **System Settings** (Configurações do Sistema)
2. Vá para **General** → **AirDrop & Handoff**
3. Desabilite **AirPlay Receiver**

Reinicie o terminal e execute `python run.py`

---

## ✅ Solução 3: Matar o Processo

Identifique qual processo está usando a porta:

```bash
lsof -i :5000
```

Então finalize-o:

```bash
kill -9 <PID>
```

Exemplo:
```bash
kill -9 1192
```

---

## ✅ Solução 4: Usar Porta Específica

Se quiser usar outra porta manualmente:

```bash
# Editar o código
# Mudar na função main():
app.run(debug=True, host='0.0.0.0', port=8000)
```

---

## Portas Comuns Alternativas

| Porta | Serviço |
|-------|---------|
| 5000  | AirPlay (macOS) / Antigos |
| **5001** | ✅ Próxima disponível |
| 8000  | Django padrão |
| 8080  | Muitos serviços |
| 3000  | Node.js comum |

---

## Verificar Porta Disponível

```bash
# Listar tudo que está usando portas
lsof -i -P -n | grep LISTEN

# Testar porta específica
nc -z 127.0.0.1 5000 && echo "Ocupada" || echo "Disponível"
```

---

## Ainda com Problemas?

1. Reinicie o terminal completamente
2. Execute: `python run.py`
3. Abra navegador em: `http://localhost:5001` (ou a porta mostrada)

Pronto! 🎉

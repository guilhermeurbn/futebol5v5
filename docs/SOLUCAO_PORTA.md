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

## ✅ Solução 2: Desabilitar AirPlay Receiver (macOS)

Se você não usa AirPlay, desabilite:

1. Abra **System Settings** (Configurações do Sistema)
2. Vá para **General** → **AirDrop & Handoff**
3. Desabilite **AirPlay Receiver**

Reinicie o terminal e execute `python run.py`

## ✅ Solução 3: Matar o Processo

Identifique qual processo está usando a porta:

```bash
lsof -i :5000
```

Então finalize-o:

```bash
kill -9 <PID>
```

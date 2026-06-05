# Solucao de Problemas - Porta 5000 em Uso

## Problema
A porta 5000 está sendo usada por outro serviço (geralmente AirPlay Receiver no macOS).

## Solucao 1: Escolher a porta no comando

O script `run.py` usa `5000` por padrao. Para entrar em outra porta, defina `PORT` no proprio comando:

```bash
PORT=5001 python run.py
```

Depois acesse `http://localhost:5001`.

## Solucao 2: Desabilitar AirPlay Receiver (macOS)

Se você não usa AirPlay, desabilite:

1. Abra **System Settings** (Configurações do Sistema)
2. Vá para **General** → **AirDrop & Handoff**
3. Desabilite **AirPlay Receiver**

Reinicie o terminal e execute `python run.py`

## Solucao 3: Matar o Processo

Identifique qual processo está usando a porta:

```bash
lsof -i :5000
```

Então finalize-o:

```bash
kill -9 <PID>
```

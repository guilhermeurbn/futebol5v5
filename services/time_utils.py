"""
Utilitário Central de Data e Hora no Fuso Horário Local da Europa (Europe/Lisbon).
Garante que todas as datas, partidas, votações e competições sigam o relógio local.
"""
import os
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
    EUROPE_TIMEZONE = ZoneInfo("Europe/Lisbon")
except Exception:
    EUROPE_TIMEZONE = timezone(timedelta(hours=1))

# Garantir fuso horário da Europa no ambiente
os.environ["TZ"] = "Europe/Lisbon"


def obter_agora_local() -> datetime:
    """
    Retorna objeto datetime atual no fuso horário da Europa (Europe/Lisbon).
    Retorna datetime ingênuo (sem tzinfo) para compatibilidade ISO limpa no sistema.
    """
    try:
        dt = datetime.now(EUROPE_TIMEZONE)
        return dt.replace(tzinfo=None)
    except Exception:
        return datetime.now()


def obter_agora_iso() -> str:
    """Retorna timestamp ISO8601 atual no fuso da Europa"""
    return obter_agora_local().isoformat()

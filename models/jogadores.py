"""
Modelos de dados para Jogadores
"""
from typing import Optional, Literal, List
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Jogador:
    """Representa um jogador de futebol.

    ``nivel`` é um float de precisão 0.1 no intervalo [1.0, 10.0] que
    representa a nota/rating do jogador. Começa como inteiro na criação e
    evolui automaticamente após cada rodada de votação.
    """
    nome: str
    nivel: float
    tipo: Literal["fixo", "avulso"] = "avulso"
    posicao: Literal["linha", "goleiro"] = "linha"
    presente: bool = False
    id: Optional[str] = None
    criado_em: Optional[str] = None
    owner_user_id: Optional[str] = None
    # Histórico de evolução: lista de dicts com ts/nivel_anterior/nivel_novo/motivo
    historico_nivel: Optional[List[dict]] = None
    nivel_preciso: Optional[float] = None
    foto_url: Optional[str] = None

    def __post_init__(self):
        """Validação e normalização pós-inicialização."""
        if not self.nome or len(self.nome.strip()) < 2:
            raise ValueError("Nome inválido: deve ter ao menos 2 caracteres")

        # Aceita int ou float; normaliza para float arredondado em 1 casa decimal (múltiplos de 0.1)
        try:
            self.nivel = round(float(self.nivel), 1)
        except (TypeError, ValueError):
            raise ValueError("Nível inválido: deve ser um número")

        if not (1.0 <= self.nivel <= 10.0):
            raise ValueError("Nível deve estar entre 1.0 e 10.0")

        if self.tipo not in ["fixo", "avulso"]:
            raise ValueError("Tipo deve ser 'fixo' ou 'avulso'")
        if self.posicao not in ["linha", "goleiro"]:
            raise ValueError("Posição deve ser 'linha' ou 'goleiro'")

        if self.id is None:
            import uuid
            self.id = str(uuid.uuid4())

        if self.criado_em is None:
            self.criado_em = datetime.now().isoformat()

        if self.historico_nivel is None:
            self.historico_nivel = []

        if self.nivel_preciso is None:
            self.nivel_preciso = self.nivel
        else:
            self.nivel_preciso = round(float(self.nivel_preciso), 4)

    def para_dict(self) -> dict:
        """Converte jogador para dicionário."""
        return asdict(self)

    @classmethod
    def do_dict(cls, data: dict) -> 'Jogador':
        """Cria jogador a partir de dicionário (tolerante a campos extras)."""
        campos_validos = {
            "nome", "nivel", "tipo", "posicao",
            "presente", "id", "criado_em", "owner_user_id", "historico_nivel", "nivel_preciso", "foto_url"
        }
        filtrado = {k: v for k, v in data.items() if k in campos_validos}
        return cls(**filtrado)

    def nivel_formatado(self) -> str:
        """Retorna nível com uma casa decimal, ex: '7.0'."""
        return f"{self.nivel:.1f}"

    def __str__(self) -> str:
        tipo_str = "⭐" if self.tipo == "fixo" else "👤"
        return f"{tipo_str} {self.nome} (Nível {self.nivel_formatado()})"

"""
Modelos de dados para Jogadores
"""
from typing import Optional, Literal
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Jogador:
    """Representa um jogador de futebol"""
    nome: str
    nivel: int
    tipo: Literal["fixo", "avulso"] = "avulso"
    posicao: Literal["linha", "goleiro"] = "linha"
    presente: bool = False
    id: Optional[str] = None
    criado_em: Optional[str] = None
    owner_user_id: Optional[str] = None
    
    def __post_init__(self):
        """Validação pós-inicialização"""
        if not self.nome or len(self.nome.strip()) < 2:
            raise ValueError("Nome inválido: deve ter ao menos 2 caracteres")
        if not (1 <= self.nivel <= 10):
            raise ValueError("Nível inválido: deve estar entre 1 e 10")
        if self.tipo not in ["fixo", "avulso"]:
            raise ValueError("Tipo deve ser 'fixo' ou 'avulso'")
        if self.posicao not in ["linha", "goleiro"]:
            raise ValueError("Posição deve ser 'linha' ou 'goleiro'")
        
        if self.id is None:
            import uuid
            self.id = str(uuid.uuid4())
        
        if self.criado_em is None:
            self.criado_em = datetime.now().isoformat()
    
    def para_dict(self) -> dict:
        """Converte jogador para dicionário"""
        return asdict(self)
    
    @classmethod
    def do_dict(cls, data: dict) -> 'Jogador':
        """Cria jogador a partir de dicionário"""
        return cls(**data)
    
    def __str__(self) -> str:
        tipo_str = "⭐" if self.tipo == "fixo" else "👤"
        return f"{tipo_str} {self.nome} (Nível {self.nivel})"

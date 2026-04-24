from database import Base
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)


from database import engine, SessionLocal
from models import Base, User

# Cria as tabelas se não existirem
Base.metadata.create_all(bind=engine)

# Adicionar um utilizador
def criar_utilizador(nome, email):
    db = SessionLocal()
    user = User(nome=nome, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user

# Listar todos
def listar_utilizadores():
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    return users
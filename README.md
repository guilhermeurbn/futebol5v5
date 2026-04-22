# ⚽ NaTrave - Gerador de Times Equilibrados

Um aplicativo web profissional para organizar, cadastrar jogadores e balancear times de futebol de forma equilibrada.

## 🎯 Recursos

- ✨ **Interface Moderna e Responsiva** - Design profissional que funciona em todos os dispositivos
- 🎲 **Balanceamento Inteligente** - Algoritmo Snake Draft para times equilibrados
- 👥 **Gerenciamento de Jogadores** - Adicione, edite e remova jogadores facilmente
- 📊 **Análise de Times** - Visualize pontuação total e diferença entre times
- 🔧 **API RESTful** - Endpoints JSON para integração com outros sistemas
- 💾 **Persistência de Dados** - Dados salvos em JSON local

## 🛠️ Tecnologias

- **Backend**: Python 3.8+, Flask 3.0
- **Frontend**: HTML5, CSS3 com Design Responsivo
- **Dados**: JSON
- **Arquitetura**: MVC com Blueprints

## 📋 Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## ⚙️ Instalação

1. **Clone ou baixe o projeto**

```bash
cd futebol5v5
```

2. **Crie um ambiente virtual** (recomendado)

```bash
python -m venv venv

# Ative o ambiente virtual
# No macOS/Linux:
source venv/bin/activate

# No Windows:
venv\Scripts\activate
```

3. **Instale as dependências**

```bash
pip install -r requirements.txt
```

## 🚀 Como Usar

### Forma Rápida (Recomendado)

```bash
python run.py
```

Este script irá:
- ✅ Verificar as dependências
- ✅ Criar dados de exemplo automaticamente
- ✅ Iniciar o servidor

### Forma Manual

```bash
python app.py
```

### Acesso

Abra seu navegador e vá para: **http://localhost:5000**

### Funcionamento

**Passo 1: Adicione jogadores**
 usando o slider
- Clique em "➕ Adicionar Jogador"

**Passo 2: Sorteie times**

- Adicione pelo menos 10 jogadores
- Clique em "🎲 Sortear Times"
- Visualize os times equilibrados com estatísticasdores
- Clique em "Sortear Times"
- Veja os times equilibrados!

## 📁 Estrutura do Projeto

```
futebol5v5/
├── app.py                    # Aplicação principal
├── config.py                 # Configurações
├── requirements.txt          # Dependências
├── jogadores.json           # Dados de jogadores
├── models/
│   └── jogadores.py         # Modelo de dados
├── services/
│   ├── jogador_service.py   # Serviço de jogadores
│   └── balanceamento.py     # Lógica de balanceamento
├── routes/
│   └── jogador_routes.py    # Rotas e endpoints
├── templates/
│   ├── index.html           # Página principal
│   └── times.html           # Página de resultados
└── static/
    └── style.css            # Estilos
```

## 🎨 Design

- **Cores**: Paleta profissional com gradientes
- **Tipografia**: Fonte do sistema para melhor performance
- **Layout**: Grid responsivo que adapta a tablets e mobile
- **Acessibilidade**: Contraste adequado e suporte a modo escuro

## 🔌 API Endpoints

```bash
# Listar todos
GET /api/jogadores

# Criar novo
POST /api/jogadores
Content-Type: application/json
{ "nome": "João Silva", "nivel": 7 }

# Obter por ID
GET /api/jogadores/<id>

# Atualizar
PUT /api/jogadores/<id>
{ "nome": "João Silva", "nivel": 8 }

# Deletar
DELETE /api/jogadores/<id>
```

### Times

```bash
# Sortear times
GET /api/times

# Resposta
{
  "sucesso": true,
  "time1": [...],
  "time2": [...],
  "soma1": 38,
  "soma2": 35,
  "favorito": "Time 1",
  "diferenca": 3
}
```

### Exemplos de Uso

Veja [exemplos_api.py](exemplos_api.py) para exemplos Python completos:

```bash
python exemplos_api.py
```

- `GET /api/times` - Sorteia e retorna times equilibrados

## 📊 Algoritmo de Balanceamento

O projeto utiliza o **Snake Draft** para equilibrar times:

1. Ordena os jogadores pelo nível (melhor para pior)
2. Alterna entre os times, pegando os melhores primeiro
3. Garante distribuição equilibrada de habilidades
4. Calcula a diferença total entre os times

**Exemplo:**
```
Jogadores: [A(10), B(9), C(8), D(7), E(6), F(5), G(4), H(3), I(2), J(1)]

Time 1: A(10) + C(8) + E(6) + G(4) + I(2) = 30 pontos
Time 2: B(9) + D(7) + F(5) + H(3) + J(1) = 25 pontos
Diferença: 5 pontos (equilibrado!)
```

## 🔒 Segurança

- Validação de entrada em todos os endpoints
- Sanitização de dados
- CORS ready para integração com frontends externos
- Type hints para melhor segurança de tipos

## 📈 Melhorias Futuras

- [ ] Autenticação de usuários
- [ ] Histórico de sorteios
- [ ] Integração com banco de dados (PostgreSQL/MongoDB)
- [ ] Dashboard com estatísticas
- [ ] Upload de foto de perfil
- [ ] Sistema de rating de jogadores
- [ ] Geração de PDF com times
- [ ] Envio de convites por email
- [ ] Mobile app nativa

## 🐛 Troubleshooting

### Porta 5000 já em uso
```bash
# Alternativamente, use outra porta
python app.py --port 5001
```

### Erro ao ler jogadores.json
- Verifique se o arquivo está no diretório raiz
- Delete o arquivo para recreiar

### Problemas com módulos
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

## 📝 Desenvolvimento

### Configuração de Desenvolvimento

```bash
export FLASK_ENV=development
export FLASK_DEBUG=True
python app.py
```

### Rodando Testes (futuro)

```bash
pytest tests/
```

## 📄 Licença

Este projeto é código aberto e disponível sob licença MIT.

## 👤 Autor

**Guilherme Urbano**

Desenvolvido com ❤️ para o futebol

## 📞 Suporte

Para reportar bugs ou sugerir melhorias, abra uma issue no repositório.

---

**Versão**: 1.0.0  
**Última atualização**: Abril 2026

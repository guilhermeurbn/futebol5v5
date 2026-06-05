# 🧪 TESTES PRÁTICOS RECOMENDADOS - NaTrave 5v5
**Quick Reference Guide para implementar testes críticos**

---

## 📦 Estrutura de Testes Recomendada

```
tests/
├── conftest.py                 # Fixtures compartilhadas
├── test_auth.py               # Testes de autenticação (4 testes)
├── test_votacao.py            # Testes de votação (6 testes)
├── test_jogador.py            # Testes de jogadores (4 testes)
├── test_juiz.py               # Testes do fluxo juiz (8 testes)
├── test_endpoints.py          # Testes de rotas (10 testes)
├── test_edge_cases.py         # Edge cases (6 testes)
└── test_responsividade.py     # Testes de UI (4 testes)
```

---

## 1️⃣ FIXTURES COMPARTILHADAS (conftest.py)

```python
# tests/conftest.py
import pytest
import json
import os
from datetime import datetime
from app import criar_app
from services.auth_service import AuthService
from services.jogador_service import JogadorService
from models.jogadores import Jogador
import uuid

@pytest.fixture
def app():
    """Flask app em modo teste"""
    app = criar_app('testing')
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Cliente HTTP para testes"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """CLI test runner"""
    return app.test_cli_runner()

@pytest.fixture
def auth_service(tmp_path):
    """AuthService com arquivo temporário"""
    arquivo = tmp_path / "users.json"
    service = AuthService(str(arquivo))
    return service

@pytest.fixture
def jogador_service(tmp_path):
    """JogadorService com arquivo temporário"""
    arquivo = tmp_path / "jogadores.json"
    service = JogadorService(str(arquivo))
    return service

@pytest.fixture
def usuario_padrao(auth_service):
    """Usuário padrão para testes"""
    return auth_service.criar_usuario(
        username='testuser',
        nome='Test User',
        password='senha123',
        role='usuario'
    )

@pytest.fixture
def usuario_admin(auth_service):
    """Admin para testes"""
    return auth_service.criar_usuario(
        username='admin',
        nome='Admin User',
        password='SUA_SENHA_ADMIN_LOCAL',
        role='admin'
    )

@pytest.fixture
def usuario_juiz(auth_service):
    """Juiz para testes"""
    return auth_service.criar_usuario(
        username='juiz',
        nome='Juiz User',
        password='juiz123',
        role='juiz'
    )

@pytest.fixture
def jogadores_padrao(jogador_service):
    """10 jogadores de teste"""
    nomes = [
        "Cristiano", "Messi", "Neymar", "Mbappé", "Vinicius Jr",
        "Rodrygo", "João Pedro", "Lucas", "Felipe", "Bruno"
    ]
    
    jogadores = []
    for i, nome in enumerate(nomes):
        jogador = jogador_service.criar(
            nome=nome,
            nivel=5 + (i % 5),
            tipo="fixo" if i % 3 == 0 else "avulso"
        )
        jogadores.append(jogador)
    
    return jogadores

@pytest.fixture
def sessao_autenticada(client, usuario_padrao):
    """Cliente com sessão autenticada"""
    with client.session_transaction() as sess:
        sess['user_id'] = usuario_padrao['id']
        sess['username'] = usuario_padrao['username']
        sess['nome'] = usuario_padrao['nome']
        sess['role'] = usuario_padrao['role']
    return client
```

---

## 2️⃣ TESTES DE AUTENTICAÇÃO (test_auth.py)

```python
# tests/test_auth.py
import pytest
from werkzeug.security import check_password_hash

class TestAuthService:
    """Testes do serviço de autenticação"""
    
    def test_criar_usuario_valido(self, auth_service):
        """Criar usuário com dados válidos"""
        usuario = auth_service.criar_usuario(
            username='alice',
            nome='Alice Silva',
            password='senha123',
            role='usuario'
        )
        
        assert usuario['username'] == 'alice'
        assert usuario['nome'] == 'Alice Silva'
        assert usuario['role'] == 'usuario'
        assert 'id' in usuario
        assert 'password_hash' in usuario
    
    def test_criar_usuario_duplicado(self, auth_service, usuario_padrao):
        """Username duplicado deve lançar erro"""
        with pytest.raises(ValueError, match="ja existe"):
            auth_service.criar_usuario(
                username='testuser',
                nome='Outro Nome',
                password='outra123',
                role='usuario'
            )
    
    def test_autenticar_valido(self, auth_service, usuario_padrao):
        """Autenticação com credenciais corretas"""
        resultado = auth_service.autenticar('testuser', 'senha123')
        
        assert resultado is not None
        assert resultado['username'] == 'testuser'
        assert resultado['nome'] == 'Test User'
    
    def test_autenticar_senha_incorreta(self, auth_service, usuario_padrao):
        """Autenticação com senha incorreta falha"""
        resultado = auth_service.autenticar('testuser', 'senha_errada')
        
        assert resultado is None
    
    def test_autenticar_usuario_inexistente(self, auth_service):
        """Autenticação de usuário inexistente falha"""
        resultado = auth_service.autenticar('naoexiste', 'qualquer_senha')
        
        assert resultado is None
    
    def test_alterar_senha_valido(self, auth_service, usuario_padrao):
        """Alterar senha com credencial antiga válida"""
        auth_service.alterar_senha(
            user_id=usuario_padrao['id'],
            senha_atual='senha123',
            nova_senha='novasenh123'
        )
        
        # Verificar que a nova senha funciona
        resultado = auth_service.autenticar('testuser', 'novasenh123')
        assert resultado is not None
    
    def test_alterar_senha_incorreta(self, auth_service, usuario_padrao):
        """Alterar senha com credencial antiga incorreta falha"""
        with pytest.raises(ValueError, match="incorreta"):
            auth_service.alterar_senha(
                user_id=usuario_padrao['id'],
                senha_atual='senha_errada',
                nova_senha='novasenh123'
            )
```

---

## 3️⃣ TESTES DE VOTAÇÃO (test_votacao.py)

```python
# tests/test_votacao.py
import pytest
from datetime import datetime, timedelta
from services.votacao_service import VotacaoService

class TestVotacaoService:
    """Testes do sistema de votação"""
    
    def test_criar_partida_votacao(self, tmp_path):
        """Criar partida de votação"""
        service = VotacaoService(str(tmp_path / "votacoes.json"))
        
        times_json = [
            {
                'numero': 1,
                'jogadores': [
                    {'nome': 'Jogador1', 'nivel': 8, 'posicao': 'linha'},
                    {'nome': 'Jogador2', 'nivel': 7, 'posicao': 'linha'},
                ]
            }
        ]
        
        usuarios = [
            {'user_id': 'user1', 'nome': 'User 1'},
            {'user_id': 'user2', 'nome': 'User 2'},
        ]
        
        partida = service.criar_partida(
            times_json=times_json,
            usuarios=usuarios,
            criado_por='admin_id',
            sorteio_id=1
        )
        
        assert partida['status'] == 'aberta'
        assert partida['sorteio_id'] == 1
        assert len(partida['participantes']) == 2
    
    def test_salvar_voto_valido(self, tmp_path):
        """Salvar voto válido"""
        service = VotacaoService(str(tmp_path / "votacoes.json"))
        
        # Criar partida
        times_json = [[{'nome': 'J1'}, {'nome': 'J2'}]]
        usuarios = [{'user_id': 'user1'}, {'user_id': 'user2'}]
        partida = service.criar_partida(times_json, usuarios, 'admin', sorteio_id=1)
        
        # Salvar voto
        votos = [
            {'jogador_nome': 'J1', 'time_numero': 1, 'nota': 8.0},
            {'jogador_nome': 'J2', 'time_numero': 1, 'nota': 7.0},
            {'jogador_nome': 'J3', 'time_numero': 2, 'nota': 9.0},
            {'jogador_nome': 'J4', 'time_numero': 2, 'nota': 6.0},
            {'jogador_nome': 'J5', 'time_numero': 2, 'nota': 8.0},
        ]
        
        voto_salvo = service.salvar_voto(
            partida_id=partida['id'],
            user_id='user1',
            votos_obrigatorios=votos
        )
        
        assert voto_salvo['user_id'] == 'user1'
        assert len(voto_salvo['votos']) == 5
    
    def test_salvar_voto_duplicado(self, tmp_path):
        """Usuário não pode votar duas vezes"""
        service = VotacaoService(str(tmp_path / "votacoes.json"))
        
        # Setup
        times_json = [[{'nome': 'J1'}]]
        usuarios = [{'user_id': 'user1'}]
        partida = service.criar_partida(times_json, usuarios, 'admin', sorteio_id=1)
        
        votos = [
            {'jogador_nome': 'J1', 'time_numero': 1, 'nota': 8.0},
            {'jogador_nome': 'J2', 'time_numero': 1, 'nota': 7.0},
            {'jogador_nome': 'J3', 'time_numero': 1, 'nota': 9.0},
            {'jogador_nome': 'J4', 'time_numero': 1, 'nota': 6.0},
            {'jogador_nome': 'J5', 'time_numero': 1, 'nota': 8.0},
        ]
        
        # Primeiro voto OK
        service.salvar_voto(partida['id'], 'user1', votos)
        
        # Segundo voto deve falhar
        with pytest.raises(ValueError, match="ja votou"):
            service.salvar_voto(partida['id'], 'user1', votos)
    
    def test_partida_expira(self, tmp_path):
        """Partida expira após tempo limite"""
        service = VotacaoService(str(tmp_path / "votacoes.json"))
        
        # Criar partida que expira em 1 segundo
        times_json = [[{'nome': 'J1'}]]
        usuarios = [{'user_id': 'user1'}]
        
        partida = service.criar_partida(
            times_json=times_json,
            usuarios=usuarios,
            criado_por='admin',
            sorteio_id=1,
            duracao_minutos=0  # Expira imediatamente
        )
        
        import time
        time.sleep(1)
        
        # Verificar status
        status = service._status_votacao(partida)
        assert status == 'expirada'
```

---

## 4️⃣ TESTES DE ENDPOINTS (test_endpoints.py)

```python
# tests/test_endpoints.py
import pytest
from flask import session

class TestLoginEndpoint:
    """Testes do endpoint de login"""
    
    def test_login_page_get(self, client):
        """GET /login retorna página"""
        response = client.get('/login')
        
        assert response.status_code == 200
        assert b'<form' in response.data
        assert b'username' in response.data
    
    def test_login_submit_valido(self, client, usuario_padrao):
        """POST /login com credenciais válidas"""
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'senha123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Painel' in response.data or b'index' in response.data
    
    def test_login_submit_invalido(self, client):
        """POST /login com senha incorreta"""
        response = client.post('/login', data={
            'username': 'naoexiste',
            'password': 'qualquer'
        })
        
        assert response.status_code == 401
        assert b'invalido' in response.data or b'error' in response.data


class TestCadastroEndpoint:
    """Testes do endpoint de cadastro"""
    
    def test_cadastro_page_get(self, client):
        """GET /cadastro retorna formulário"""
        response = client.get('/cadastro')
        
        assert response.status_code == 200
        assert b'<form' in response.data
    
    def test_cadastro_submit_valido(self, client):
        """POST /cadastro cria novo usuário"""
        response = client.post('/cadastro', data={
            'nome': 'Novo User',
            'username': 'newuser',
            'password': 'senha123',
            'confirmar_password': 'senha123',
            'nivel': '5',
            'tipo': 'avulso',
            'posicao': 'linha'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Deve redirecionar para login com mensagem de sucesso
        assert b'sucesso' in response.data or b'login' in response.data.lower()
    
    def test_cadastro_senhas_diferentes(self, client):
        """POST /cadastro com senhas diferentes falha"""
        response = client.post('/cadastro', data={
            'nome': 'Novo User',
            'username': 'newuser',
            'password': 'senha123',
            'confirmar_password': 'senha456'
        })
        
        assert response.status_code == 400
        assert b'nao confere' in response.data or b'differ' in response.data


class TestSortearEndpoint:
    """Testes do endpoint de sorteio"""
    
    def test_sortear_sem_autenticacao(self, client):
        """GET /sortear sem autenticação redireciona"""
        response = client.get('/sortear')
        
        assert response.status_code == 302  # Redirect
        assert '/login' in response.location
    
    def test_sortear_com_autenticacao(self, client, sessao_autenticada, jogadores_padrao):
        """GET /sortear com autenticação"""
        response = sessao_autenticada.get('/sortear')
        
        assert response.status_code == 200
        # Deve ter form para selecionar jogadores
```

---

## 5️⃣ EDGE CASES (test_edge_cases.py)

```python
# tests/test_edge_cases.py
import pytest
from services.balanceamento import BalanceadorTimes
from models.jogadores import Jogador

class TestEdgeCases:
    """Testes de casos extremos"""
    
    def test_sorteio_zero_jogadores(self):
        """Sorteio com zero jogadores deve falhar"""
        valido, msg = BalanceadorTimes.validar_jogadores([])
        
        assert not valido
        assert "minimo" in msg.lower()
    
    def test_sorteio_3_jogadores(self):
        """Sorteio com 3 jogadores (não divisível) falha"""
        jogadores = [
            Jogador("J1", 5, "avulso", presente=True),
            Jogador("J2", 5, "avulso", presente=True),
            Jogador("J3", 5, "avulso", presente=True),
        ]
        
        valido, msg = BalanceadorTimes.validar_jogadores(jogadores)
        
        assert not valido
    
    def test_nível_jogador_invalido(self):
        """Criar jogador com nível inválido"""
        with pytest.raises(ValueError):
            Jogador("Hacker", nivel=999, posicao="linha")
    
    def test_nível_zero(self):
        """Nível zero deve falhar"""
        with pytest.raises(ValueError):
            Jogador("Zero", nivel=0, posicao="linha")
    
    def test_nome_vazio(self):
        """Nome vazio deve falhar"""
        with pytest.raises(ValueError):
            Jogador("", nivel=5, posicao="linha")
    
    def test_todos_jogadores_mesmo_nivel(self):
        """Sorteio com todos no mesmo nível (edge case válido)"""
        jogadores = [
            Jogador(f"J{i}", 5, "avulso", presente=True)
            for i in range(10)
        ]
        
        valido, msg = BalanceadorTimes.validar_jogadores(jogadores)
        assert valido
        
        times, somas = BalanceadorTimes.sortear_multiplos_times(jogadores)
        
        # Todos times devem ter soma 25 (5*5)
        assert all(s == 25 for s in somas)
```

---

## 6️⃣ TESTES DE RESPONSIVIDADE (test_responsividade.py)

```python
# tests/test_responsividade.py
import pytest
# Requer: pip install selenium playwright

class TestResponsividadeMobile:
    """Testes de responsividade mobile (com Playwright)"""
    
    @pytest.mark.integration
    async def test_login_mobile_320px(self):
        """Login é responsivo em 320px (iPhone SE)"""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(viewport={"width": 320, "height": 568})
            page = await context.new_page()
            
            await page.goto('http://localhost:5000/login')
            
            # Verificar que botão é clicável
            btn = await page.query_selector('button.btn-primary')
            assert btn is not None
            
            # Botão deve ter height >= 44px (touch target)
            height = await btn.evaluate('el => el.offsetHeight')
            assert height >= 44
            
            await browser.close()
    
    @pytest.mark.integration
    async def test_votacao_tablet_768px(self):
        """Votação é responsiva em 768px (iPad)"""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(viewport={"width": 768, "height": 1024})
            page = await context.new_page()
            
            # Navegar para votação (requer autenticação)
            await page.goto('http://localhost:5000/votacao')
            
            # Verificar que elementos principais são visíveis
            inputs = await page.query_selector_all('input[name="nota"]')
            assert len(inputs) > 0
            
            await browser.close()
```

---

## 🚀 COMO RODAR OS TESTES

### Setup Inicial
```bash
# 1. Instalar dependências
pip install pytest pytest-cov pytest-asyncio pytest-flask playwright

# 2. Clonar fixtures e testes
cp tests/conftest.py tests/
cp tests/test_*.py tests/

# 3. Rodar testes
pytest -v --cov=. --cov-report=html
```

### Rodar Por Categoria
```bash
# Apenas testes de autenticação
pytest tests/test_auth.py -v

# Apenas testes críticos (não integration)
pytest -m "not integration" -v

# Com cobertura
pytest --cov=services --cov-report=html

# Modo watch (refazer a cada mudança)
pytest-watch tests/
```

### CI/CD Integration
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - run: pip install -r requirements.txt pytest pytest-cov
      - run: pytest --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v2
```

---

## 📊 Métricas Esperadas

Após implementar todos os testes:

```
Cobertura esperada:
├─ auth_service.py:        ✅ 95%
├─ votacao_service.py:      ✅ 90%
├─ balanceamento.py:        ✅ 85%
├─ jogador_service.py:      ✅ 80%
└─ Média geral:            ✅ 80%
```

---

**Próximo passo**: Implementar Phase 1 com 12 testes críticos

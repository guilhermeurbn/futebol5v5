# 🚀 Funcionalidades e Plugins Futuros - NaTrave 5v5

Este documento lista as melhorias nativas e plugins planejados para as próximas versões do aplicativo **NaTrave 5v5**.

---

## 📋 Lista de Plugins & Funcionalidades

### 1. 🔔 Notificações Push (`@capacitor/push-notifications`)
- Lembretes automáticos 2h antes da pelada.
- Alertas quando o sorteio dos times for realizado.
- Chamada para votação do Craque/Bagre da Rodada no final do jogo.

### 2. 📳 Feedback Háptico e Vibração (`@capacitor/haptics`)
- Tactile feedback ao realizar sorteios, marcar presença e votar em jogadores.
- Sensação nativa fluida com o Taptic Engine do iOS.

### 3. 📸 Câmera e Galeria (`@capacitor/camera`)
- Upload de foto de perfil (avatar do jogador) direto pela câmera do iPhone.
- Galeria dos campeões da pelada no final da partida.

### 4. 📲 Compartilhamento Rápido (`@capacitor/share`)
- Botão "Compartilhar no WhatsApp" com o resumo visual dos 2 times sorteados ou o card do Craque da Rodada para Instagram Stories.

### 5. 🔒 Autenticação Biométrica (`@capacitor-community/biometric-auth`)
- Login automático instantâneo com Face ID ou Touch ID sem digitação de senha.

### 6. 💳 Controle Financeiro & Mensalidade (Pix / Apple Pay)
- QR Code Pix automático para cobrança da taxa do campo e controle de quem já pagou.

### 7. ⚽ iOS Live Activities & Home Screen Widgets
- Widget na tela do iPhone com contagem regressiva para o jogo e contagem de presenças confirmadas.

---

## 🎨 Melhorias de Design Futuras - Estética Liquid Glass (UI/UX)

### 1. 🚤 Barra de Navegação Flutuante (Liquid Glass Dock)
- Barra de navegação inferior flutuante com cantos arredondados, fundo translúcido (`backdrop-filter: blur(20px) saturate(180%)`) e bordas iluminadas.
- Conteúdo refrata suavemente por baixo ao rolar.

### 2. 🎴 Cards dos Times e Jogadores em Vidro Refrativo
- Cartões translúcidos com bordas brilhantes em gradiente (*glass-glow*) e iluminação sutil nas cores dos times (roxo, verde, azul).

### 3. 🏆 Modais e Popups Flutuantes
- Janelas de votação e confirmação de presença em camadas de vidro flutuante com efeito *inner-glow* e desfocagem profunda do fundo.

### 4. ⚡ Botões de Ação com Brilho Líquido Dinâmico
- Botões de "Sortear" e "Confirmar" com onda de luz animada na superfície de vidro ao tocar.

---

## 🏆 Gamificação, Modo Ao Vivo & Gestão

### 1. 🥇 Conquista de Selos e Badges
- Sistema de medalhas e conquistas desbloqueáveis para os jogadores (ex: *Artilheiro do Mês*, *Paredão / Melhor Goleiro*, *Em Chamas - 3 Vitórias Seguidas*, *Garçom de Assistências*).
- Exibição dos selos conquistados no card do perfil do jogador.

### 2. ⏱️ Modo Ao Vivo (Placar e Cronômetro em Tempo Real)
- O juiz/organizador atualiza gols, assistências e tempo da partida ao vivo no app.
- Qualquer jogador ou espectador acompanha o placar atualizado em tempo real na tela do jogo ou na área de histórico.

### 3. 💳 Controle de Pagamento
- Status visual de pagamento individual para cada partida (🟢 *Pago* | 🟡 *Pendente*).
- Chave Pix Copia e Cola integrada para facilitar a cobrança da taxa da quadra/pelada.

### 4. ⚙️ Sorteio Dinâmico e Quantidade Flexível (Modo Juiz)
- **Fim das Limitações Fixas**: Eliminar a restrição de número fixo de participantes (10, 15 ou 20).
- **Personalização de Jogadores e Times**: Permitir que o Juiz/Organizador escolha livremente o **número total de jogadores** (ex: 18, 22, 14 pessoas) e a **quantidade desejada de equipes** (ex: 2, 3 ou 4 times).
- **Cálculo e Distribuição Automática**: O algoritmo divide e distribui automaticamente os jogadores por equipe de forma proporcional (ex: *18 pessoas ÷ 3 times = 6 jogadores por time*; *18 pessoas ÷ 4 times = 4 equipes com rodízio automático de reservas*).
- **Flexibilidade de Formato**: Suporte nativo para futebol 5v5, 6v6, Fut7 ou partidas de quadra com fila de espera.

### 5. 🔑 Persistência de Login ("Lembrar de Mim")
- **Correção da Sessão**: Fazer a opção *"Lembrar de mim"* salvar uma sessão de longa duração (cookie persistente / refresh token de 30 dias).
- **Experiência sem Redigitações**: Garantir que, ao fechar e reabrir o app no iPhone ou no navegador, o usuário continue logado automaticamente na sua conta sem precisar digitar usuário e senha novamente.







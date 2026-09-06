# Regras do Projeto

- **NUNCA** execute comandos Git (`git add`, `git commit`, `git push`, `git checkout`, etc.) de forma autônoma sem que o usuário solicite explicitamente ou aprove a ação primeiro.
- **Atualizações do App iOS**: O aplicativo iOS carrega dinamicamente o servidor web (`https://natrave.pt`). Alterações normais em Python, HTML, CSS e JavaScript são atualizadas automaticamente no app ao fazer deploy na web. O assistente deve **SEMPRE avisar o usuário proativamente** caso uma alteração exija abrir o Xcode ou compilar um novo build para a App Store (ex: ícones, splash screen, permissões do iOS ou novos plugins nativos do Capacitor).
- **Investigação e Alterações no Railway (Produção)**: Sempre investigar a produção diretamente via Railway quando necessário, mas **NUNCA fazer qualquer alteração, escrita ou deleção no banco de produção sem antes explicar tudo em detalhes e obter autorização prévia e explícita do usuário**. Durante investigações, realizar apenas leituras estritamente seguras (read-only).



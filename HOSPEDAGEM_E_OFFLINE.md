# Hospedagem e Offline (curto)

## 1) Melhor opcao agora: Render

Seu projeto ja esta quase pronto para isso.

Passos:
1. Suba o projeto no GitHub.
2. Entre em render.com e conecte o repo.
3. O Render vai ler `render.yaml` automaticamente.
4. Deploy.
5. Abra a URL publica no celular e use "Adicionar a tela inicial".

Obs:
- Defina uma variavel `SECRET_KEY` forte se quiser sobrescrever a gerada.
- Plano free pode "dormir" e demorar alguns segundos no primeiro acesso.

## 2) Offline no celular (estado atual)

Ja existe PWA + Service Worker.

Funciona offline para:
- paginas/estaticos ja visitados
- algumas respostas de API em cache

Nao funciona offline total para:
- acoes POST/PUT/DELETE com persistencia no servidor

## 3) Para offline de verdade (proximo passo)

Arquitetura recomendada:
1. Salvar operacoes no celular (IndexedDB).
2. Quando voltar internet, sincronizar fila com o servidor.
3. No servidor, processar lote e responder conflitos.

Se quiser, eu implemento isso em etapas pequenas.

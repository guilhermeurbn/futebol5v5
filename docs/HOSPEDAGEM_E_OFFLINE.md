# Hospedagem e Offline

## 1) Melhor opção agora: Render

Seu projeto já está quase pronto para isso.

Passos:
1. Suba o projeto no GitHub.
2. Entre em render.com e conecte o repo.
3. O Render vai ler `render.yaml` automaticamente.
4. Deploy.
5. Abra a URL pública no celular e use "Adicionar a tela inicial".

Obs:
- Defina uma variável `SECRET_KEY` forte se quiser sobrescrever a gerada.
- Plano free pode "dormir" e demorar alguns segundos no primeiro acesso.

## 2) Offline no celular (estado atual)

Já existe PWA + Service Worker.

Funciona offline para:
- Páginas/estáticos já visitados
- Algumas respostas de API em cache

Não funciona offline total para:
- Ações POST/PUT/DELETE com persistência no servidor

## 3) Para offline de verdade (próximo passo)

Arquitetura recomendada:
1. Salvar operações no celular (IndexedDB).
2. Quando voltar internet, sincronizar fila com o servidor.
3. No servidor, processar lote e responder conflitos.

# Stack técnica atual — Tucano

Este documento resume a arquitetura vigente. As justificativas, etapas e definições completas estão no [CODEX.md](CODEX.md); as regras de produto continuam no [AGENTS.md](AGENTS.md).

## Aplicação

- **Backend:** Go 1.23+, monólito modular, router `chi`, validação no servidor e contrato REST/JSON.
- **Dados:** PostgreSQL 16 + PostGIS 3.4, SQL explícito com `sqlc`, migrações com `golang-migrate`.
- **Jobs e cache:** Redis 7 + Asynq.
- **Tempo real:** WebSocket via `nhooyr.io/websocket` e Redis Pub/Sub quando o chat for portado.
- **Frontend:** SvelteKit + TypeScript + Tailwind CSS, adapter Node e desenho mobile first.
- **Autenticação:** JWT curto + refresh token rotativo em cookie `httpOnly`, senha com Argon2id.
- **Descoberta local:** catálogo de categorias, perfis e agendas em PostgreSQL; busca por raio com índice GiST e funções PostGIS.
- **Portfólio:** imagens JPEG/PNG em volume local no MVP, com metadados no PostgreSQL e chave pública não previsível.
- **Testes:** `testing`/`testify` no backend; Vitest e Playwright no frontend.

## Infraestrutura

O ambiente local e o deploy usam Docker Compose com:

- `api`: processo HTTP Go;
- `worker`: mesmo código-base, executando o servidor Asynq;
- `web`: SvelteKit no Node;
- `postgres`: PostGIS;
- `redis`: cache, fila e pub/sub;
- `migrate`: execução explícita e descartável das migrações;
- `traefik`: entrada HTTP/TLS e roteamento de `/api`.

O volume `uploads_data` guarda o portfólio básico. O entrypoint prepara somente esse diretório e então reduz privilégios para o usuário `tucano` antes de iniciar o processo Go.

O serviço prestado entre usuário e profissional nunca passa pela plataforma. Mercado Pago será usado somente para assinatura Premium, quando a Etapa 10 for implementada.

## Estado do legado

A implementação Django foi retirada do runtime. Seus arquivos permanecem temporariamente no repositório como referência comportamental durante a migração dos domínios, sem serem copiados para as imagens Go/SvelteKit. Dependências, modelos ou decisões do legado não devem ser reativados sem justificativa explícita.

# Tucano

Marketplace nacional e freemium que aproxima contratantes de profissionais autônomos disponíveis para serviços pontuais. A plataforma cuida de descoberta, disponibilidade, reputação e contato direto; não processa o pagamento do serviço nem cobra comissão sobre ele.

## Estado da reconstrução

O projeto está sendo refeito em Go + SvelteKit conforme o [CODEX.md](CODEX.md). As **Etapas 0 a 2 — Fundação, identidade, perfis e descoberta local** já estão estruturadas:

- API Go 1.23 com `chi`, logs estruturados, CORS, request ID, recuperação de panic e rate limit;
- PostgreSQL 16 + PostGIS, migrações versionadas e acesso SQL preparado com `sqlc`;
- `AuditEvent` como infraestrutura transversal desde a primeira migração;
- Redis 7 e worker Asynq;
- frontend SvelteKit/TypeScript com Tailwind, mobile first, consumindo `/api/health`;
- Docker Compose com `api`, `worker`, `web`, `postgres`, `redis`, `migrate` e Traefik;
- testes backend/frontend e CI com publicação das imagens no GHCR em `main`;
- cadastro, confirmação de e-mail, login, refresh rotativo, logout e recuperação de senha;
- perfis profissional e contratante coexistindo na mesma conta, com autorização no servidor;
- catálogo inicial de categorias permitido pelas decisões de produto;
- perfil profissional com apresentação, habilidades, região, disponibilidade e portfólio básico;
- busca PostGIS paginada por categoria e distância, sem expor coordenadas exatas;
- telas mobile-first para autenticação, alternância de perfil, edição profissional e busca local.

O código Django anterior permanece temporariamente em `apps/`, `config/`, `templates/` e `static/` apenas como referência durante a migração dos fluxos. Ele não participa mais do runtime definido pelo Docker Compose e será removido quando os respectivos domínios forem portados.

## Documentação que governa o projeto

Leia nesta ordem:

1. [AGENTS.md](AGENTS.md): produto, autonomia, privacidade, limites jurídicos e critérios de qualidade;
2. [ROADMAP.md](ROADMAP.md): progresso atual, próximos marcos e pendências;
3. [CODEX.md](CODEX.md): stack atual e roteiro detalhado de reconstrução;
4. [stack.md](stack.md): resumo operacional da arquitetura vigente;
5. [openapi.yaml](openapi.yaml): contrato HTTP atual.

## Rodar localmente

Pré-requisitos: Docker com Compose.

```bash
cp .env.example .env
docker compose up --build
```

O frontend fica em <http://localhost:8080> e a saúde da API em <http://localhost:8080/api/health>.

```bash
docker compose ps
docker compose logs -f api worker web
```

As migrações são executadas pelo serviço descartável `migrate`, antes da API. Em produção, esse passo deve continuar explícito no deploy; a aplicação nunca altera o schema silenciosamente.

## Desenvolvimento sem Compose

Backend (requer Go 1.23+, PostgreSQL/PostGIS e Redis):

```bash
export DATABASE_URL='postgres://tucano:senha@localhost:5432/tucano?sslmode=disable'
export REDIS_URL='redis://localhost:6379/0'
export UPLOAD_DIR='/tmp/tucano-uploads'
go run ./cmd/api
```

Frontend (requer Node 22 e pnpm):

```bash
cd web
pnpm install
pnpm dev
```

O proxy de desenvolvimento do Vite encaminha `/api` para `http://localhost:8080`.

## Verificações

```bash
go test ./...
cd web && pnpm test && pnpm check && pnpm lint && pnpm build
docker compose config --quiet
```

O código gerado pelo `sqlc` fica versionado em `internal/platform/database/sqlc`. Para regenerá-lo após alterar migrations ou queries:

```bash
make generate
```

## Estrutura ativa

```text
cmd/api/                 processo HTTP
cmd/worker/              jobs Asynq
internal/<domínio>/      regras do produto por domínio
internal/platform/       configuração, HTTP, banco e auditoria
migrations/              schema versionado (golang-migrate)
queries/                 SQL tipado pelo sqlc
web/                     aplicação SvelteKit
```

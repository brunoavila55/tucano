# CODEX.md — Roteiro de desenvolvimento (stack Go + JavaScript)

## Por que este documento existe

O MVP do Tucano foi iniciado em Django (Python) + HTMX. Essa stack foi abandonada por dois motivos concretos, não por moda:

1. **Desempenho abaixo do esperado** no ambiente de destino (VPS própria em Proxmox, a mesma infra que já hospeda as APIs Go da empresa).
2. **Falta de domínio real da stack** — o autor já desenvolve e opera APIs em Go em produção (`api.newlifefibra.com.br`) e tem experiência anterior com frontend em JavaScript (rotas SvelteKit que a própria API Go veio substituir em outro projeto). Construir o MVP numa stack que não domina cria risco de projeto, não só risco técnico.

Este arquivo **substitui** o `CLAUDE.md` anterior (roteiro Django) e a parte técnica do `stack.md` anterior. Ele **não** substitui o `AGENTS.md` — todas as regras de produto, limites jurídicos, entidades conceituais e critério de qualidade descritos lá continuam valendo integralmente. Nada neste documento contradiz o AGENTS.md; ele só troca *como* construir, nunca *o quê* construir.

Sempre que uma etapa esbarrar numa ambiguidade de produto (preços/limites de planos, regras de ranking, compartilhamento de localização, verificação de identidade, moderação, termos jurídicos, inclusão de pagamento do serviço), registre a hipótese ou pare e pergunte — não decida silenciosamente. Isso vale tanto quanto valia no roteiro Django.

---

## Stack técnica (nova)

### Backend — Go

- **Go 1.23+**, monólito modular (nada de microserviços prematuros — mesmo princípio de engenharia do AGENTS.md, só que em Go).
- **Router:** `chi` (stdlib-friendly, middleware composável, sem mágica). Alternativa aceitável: Fiber, se a familiaridade com Express-like APIs acelerar — decisão do executor, não bloqueante.
- **Acesso a dados:** `sqlc` (SQL escrito à mão, código Go gerado e tipado) em vez de ORM. Casa melhor com quem já pensa em SQL para dashboards (Zabbix/Grafana) do que um ORM tipo GORM esconderia. PostGIS entra como SQL puro nas queries geoespaciais.
- **Migrações:** `golang-migrate`, versionadas no repo, aplicadas via CLI/CI — nunca migração automática silenciosa em produção.
- **Banco:** PostgreSQL 16 + PostGIS 3.4 (mantido do desenho original — é a peça certa do stack.md antigo, independe de linguagem).
- **Cache / filas / pub-sub:** Redis 7.
- **Jobs assíncronos e agendados:** `Asynq` (fila sobre Redis, com painel de inspeção via `asynqmon`) substituindo Celery+beat. Cobre expiração de chamado, disparo de notificações, jobs de confirmação pós-serviço.
- **Tempo real (chat, contador de interessados):** WebSocket nativo via `nhooyr.io/websocket`, com Redis Pub/Sub para permitir múltiplas réplicas do serviço `api` no futuro sem sessão pinada.
- **Autenticação:** JWT de acesso de vida curta + refresh token httpOnly cookie; hashing de senha com `argon2id`. Login social (Google) como etapa opcional, não bloqueante.
- **Geoespacial:** consultas PostGIS diretas (`ST_DWithin`, `ST_Distance`) via sqlc — nada de reimplementar distância em Go.
- **Validação/serialização:** `go-playground/validator` sobre structs de request; resposta JSON consistente (envelope de erro único, ver Etapa 0).
- **Documentação de API:** OpenAPI gerado com `swaggo` a partir de comentários — é o contrato entre backend Go e frontend JS.
- **Testes:** `testing` + `testify` + `httptest` para handlers; `testcontainers-go` para testes de integração contra Postgres/Redis reais em CI.

### Frontend — JavaScript

- **SvelteKit** (TypeScript), consumindo a API Go via REST/JSON + WebSocket para chat. Escolhido por já ter familiaridade prévia (o projeto de integração MK teve rotas SvelteKit antes de migrar para API Go) e por gerar bundles pequenos — relevante para mobile-first em conexão de dados variável, que é o público real do app.
- **Tailwind CSS**, mobile-first, mesma diretriz de UX do AGENTS.md.
- **PWA:** `vite-plugin-pwa` (manifest + service worker), cobrindo a mesma necessidade que a Etapa 6 do roteiro antigo cobria com `django-pwa` — instalável sem loja, com fallback de push por WhatsApp/SMS em iOS sem push nativo.
- **Adapter de deploy:** `@sveltejs/adapter-node`, rodando como processo Node dentro de container próprio (não Vercel/Netlify — mantém tudo autohospedado na Proxmox, consistente com o resto da infra).
- **Testes:** `Vitest` (unitário/componente) + `Playwright` (E2E dos fluxos críticos: publicar chamado, demonstrar interesse, selecionar, chat).

### Infra e deploy

Mantém o padrão já usado nos outros projetos, só adicionando os serviços novos ao `docker-compose.yml` do repositório do Tucano — mesmo padrão descrito para as APIs Go existentes:

- **Proxmox** como base, **Docker Compose** por ambiente, **Traefik** como reverse proxy com TLS automático (Let's Encrypt), **GitHub Actions** fazendo build da imagem, push para **GHCR** e deploy via SSH.
- Serviços no `docker-compose.yml`: `api` (Go), `worker` (Go, mesmo binário rodando em modo worker do Asynq), `web` (SvelteKit/Node), `postgres` (PostGIS), `redis`, `traefik`.
- Métricas/observabilidade: expor `/metrics` (Prometheus) no serviço `api`, mesmo padrão já usado em `api.newlifefibra.com.br`; dashboards em Grafana.
- Domínio sugerido: subdomínio dedicado (ex.: `tucano.<domínio>` para o frontend, `api.tucano.<domínio>` para a API), separado da infra da New Life Fibra por ser produto próprio, não da ISP.

### Pagamentos e notificações

- **Assinatura Premium:** Mercado Pago via REST (SDK oficial Go ou chamadas HTTP diretas — decisão do executor), assinatura recorrente com Pix/cartão. Mesmo escopo do stack.md antigo: só cobra o software, nunca o valor do serviço.
- **Web Push:** `webpush-go` (VAPID), disparado pelos workers Asynq.
- **WhatsApp/SMS (fallback, janelas curtas):** Twilio (SDK Go oficial) ou API do WhatsApp Business, mesma decisão de produto do roteiro antigo — sem provedor fixado ainda, registrar como hipótese ao implementar.
- **E-mail:** SMTP simples (ou Resend/Postmark) para eventos não urgentes.

---

## Convenções gerais válidas em todas as etapas

- Envelope de resposta de erro único em toda a API, ex.: `{"error": {"code": "...", "message": "..."}}` — decidir e documentar na Etapa 0, nunca variar depois.
- Toda regra de permissão é checada no handler Go (servidor), nunca só escondida no frontend — mesmo princípio do AGENTS.md, agora como middleware `chi`.
- Toda entrada é validada no backend antes de tocar o banco.
- Segredos fora do repositório (`.env` + `.gitignore`), nunca hardcoded nem versionado.
- Toda operação sensível gera um `AuditEvent` (ver Etapa 0) — publicação de chamado, interesse, seleção, retirada, expiração, cancelamento, moderação.
- Migração versionada para toda mudança de schema — nunca `AutoMigrate` estilo ORM.
- Paginação obrigatória desde a primeira versão de qualquer listagem (busca, chat, avaliações).
- Cada etapa só é considerada concluída quando satisfizer seu próprio DoD **e** o [Critério de qualidade do AGENTS.md](https://github.com/brunoavila55/tucano/blob/main/AGENTS.md#crit%C3%A9rio-de-qualidade).

---

## Etapa 0 — Fundação do projeto

**Objetivo:** API Go e frontend SvelteKit rodando localmente e em Docker Compose, sem nenhuma feature de produto ainda.

Entregáveis:

- Módulo Go (`go.mod`) com estrutura por domínio (`internal/accounts`, `internal/professionals`, `internal/clients`, `internal/requests`, `internal/chat`, `internal/reviews`, `internal/subscriptions`, `internal/moderation`), espelhando os apps Django do desenho original.
- `chi` configurado com middlewares base: logger estruturado (sem dados pessoais), recover, CORS, request ID, rate limiting básico.
- `sqlc` configurado, primeira migração `golang-migrate` criando o banco com extensão PostGIS habilitada e testada com um campo geoespacial trivial.
- Envelope de resposta/erro padronizado, documentado no OpenAPI (`swaggo`) desde o primeiro endpoint (`/health`).
- Projeto SvelteKit criado, Tailwind configurado, layout base mobile-first, chamando `/health` da API Go como smoke test.
- `docker-compose.yml`: `api`, `worker`, `web`, `postgres` (PostGIS), `redis`, `traefik`.
- `.env.example` + `.gitignore` cobrindo segredos.
- CI no GitHub Actions: lint (`golangci-lint`, `eslint`), testes (`go test`, `vitest`), build de imagem e push para GHCR.
- Model conceitual `AuditEvent` criado desde já (tabela + função de registro), mesmo vazio de uso — é infraestrutura transversal, não uma feature de etapa futura.

DoD:

- `docker compose up` sobe todos os serviços sem erro.
- `go test ./...` e `pnpm test` passam localmente e em CI.
- Frontend consegue chamar `/health` da API e renderizar o resultado.
- Pipeline de CI publica imagem no GHCR em push para `main`.

---

## Etapa 1 — Identidade e perfis

**Objetivo:** cadastro, login e os dois tipos de perfil coexistindo na mesma conta.

Entregáveis:

- `internal/accounts`: tabela `users` (e-mail, hash argon2id, verificação de e-mail, timestamps), endpoints de cadastro, login, logout, refresh, recuperação de senha.
- `internal/professionals` / `internal/clients`: tabelas `professional_profiles` e `client_profiles`, ligadas a `users` por FK, permitindo que a mesma conta tenha os dois perfis simultaneamente (requisito do AGENTS.md).
- Middleware de autorização por papel (`RequireRole("professional")`, `RequireRole("client")`) aplicado a cada rota — nunca decidido só no frontend.
- Fluxo no frontend de escolha/alternância entre perfil profissional e contratante.
- Páginas de cadastro, login, verificação de e-mail e recuperação de senha em SvelteKit, consumindo a API.

DoD:

- Cadastro, login, logout, verificação de e-mail e recuperação de senha funcionam via UI ponta a ponta.
- Um usuário pode ter perfil profissional e de contratante simultaneamente.
- Testes Go cobrindo: contratante não acessa handler exclusivo de profissional e vice-versa (403 esperado).

---

## Etapa 2 — Categorias, região e disponibilidade

**Objetivo:** profissional configurável e buscável por categoria e localização aproximada, num marketplace geral (sem recorte de segmento) — mesmo escopo do AGENTS.md ("Foco inicial recomendado").

Entregáveis:

- Tabela `service_categories`, catálogo aberto administrável (endpoint admin simples ou seed via migration/script) — não lista fechada por segmento. Seed inicial respeitando as exclusões do AGENTS.md (saúde/medicina clínica, advocacia, segurança privada autônoma, consultoria de investimento) e incluindo explicitamente as categorias com conselho de classe permitidas (estética/beleza, engenharia/arquitetura, contabilidade), além de eventos/gastronomia/casa.
- Tabela `availabilities` associada a `professional_profiles`.
- Campo geoespacial (`geography(Point)`) de região atendida no perfil profissional, com índice GiST desde já.
- Endpoints de edição de perfil profissional: bio, categoria principal, habilidades, região, preço de referência opcional, portfólio básico (upload local em disco/volume Docker nesta etapa — trocar por bucket S3-compatível só quando o volume justificar).
- Endpoint de busca por categoria + região usando `ST_DWithin`/`ST_Distance`, paginado, ordenado por distância (sem ranking sofisticado ainda).
- Frontend: formulário de edição de perfil profissional e tela de busca/listagem com filtros.

DoD:

- Um profissional consegue configurar categoria, região e disponibilidade via UI.
- Busca por categoria retorna profissionais ordenados por distância aproximada, em qualquer região do país.
- Resposta da API nunca inclui coordenada exata do profissional para quem não deveria vê-la — só distância/região aproximada (AGENTS.md — Privacidade).
- Tentar cadastrar/selecionar uma categoria da lista de exclusão é bloqueado na validação do backend.

---

## Etapa 3 — Chamados e janela de interesse

**Objetivo:** o fluxo central do produto — publicar, demonstrar interesse, selecionar, expirar — com janela de duração configurável. Não existe fluxo separado de "chamado urgente": todo chamado usa a mesma mecânica, a urgência é só reflexo de o contratante escolher uma janela curta.

Entregáveis:

- `internal/requests`: tabela `service_requests` com os campos do fluxo "Publicar um chamado" (categoria, data/horário ou período, região, quantidade de posições, descrição, valor/faixa opcional, requisitos, **janela de interesse** como enum fixo: 2 horas, 5 horas, 24 horas, 3 dias).
- Estados mínimos do chamado (`draft`, `open`, `partially_filled`, `filled`, `expired`, `cancelled`, `completed`) como enum Postgres + máquina de estados simples em Go (transições validadas em código, não só no banco).
- Tabela `interests` com estados (`applied`, `shortlisted`, `selected`, `not_selected`, `withdrawn`, `expired`).
- Regra de validação no backend: a janela nunca ultrapassa o horário de início do serviço; perto demais do horário, a API retorna sugestão de janela mais curta em vez de aceitar a inválida.
- CRUD de chamado: criar, editar, encerrar manualmente a qualquer momento, cancelar com motivo.
- Formulário de publicação no frontend otimizado para ser rápido (meta: menos de 30s — AGENTS.md).
- Endpoint que lista, para um profissional, os chamados compatíveis com categoria/região; endpoint de demonstração de interesse.
- Endpoint que lista, para o contratante, os interessados em um chamado (paginado); seleção manual com atualização atômica das posições restantes (transação Postgres, evitando corrida se dois contratantes/admins tentam selecionar ao mesmo tempo).
- Job Asynq agendado (delay = janela escolhida, calculado no momento da publicação) para expirar o chamado automaticamente; deve sobreviver a reinício do processo `worker` (fila persistida em Redis, não em memória).
- Registro de `AuditEvent` para publicação, interesse, seleção, retirada, expiração, cancelamento.
- Limite anti-spam mínimo: mesmo contratante não publica chamados duplicados (mesma categoria/janela/região) num intervalo curto.
- Notificação (mesmo que só "TODO: hook para Etapa 5" nesta fase) dos quatro desfechos: selecionado, não selecionado, expirado, cancelado.

DoD:

- Fluxo completo publicar → interessar-se → selecionar → atualizar posições restantes funciona ponta a ponta para as quatro janelas.
- Selecionar uma posição não afasta ninguém das posições restantes, se houver mais de uma.
- Um chamado sem seleção expira automaticamente via Asynq, sem intervenção manual, mesmo reiniciando o processo `worker` no meio do caminho (teste de integração com `testcontainers-go` simulando isso).
- Testes cobrindo transições de estado de `service_requests` e `interests`, incluindo abuso (selecionar além da quantidade de posições, janela que ultrapassa o horário do serviço, seleção concorrente).
- Auditoria consultável (endpoint admin simples ou query direta) para um chamado de teste ponta a ponta.

---

## Etapa 4 — Conversa entre as partes (chat)

**Objetivo:** contratante e profissional trocam mensagens em tempo real após interesse/seleção.

Entregáveis:

- `internal/chat`: tabelas `conversations` e `messages`; endpoint WebSocket (`nhooyr.io/websocket`) autenticado por JWT na query string ou header do handshake.
- Redis Pub/Sub como backplane entre conexões WebSocket, preparando o terreno para múltiplas réplicas do serviço `api` sem sessão pinada.
- Conversa aberta automaticamente ao selecionar um profissional (hook direto na transação de seleção da Etapa 3).
- Proteção básica contra spam: limite de mensagens/tempo por conversa, bloqueio de usuário (reaproveitando estrutura de bloqueio que a Etapa 9 vai formalizar — aqui basta uma tabela mínima `blocked_users`).
- Frontend: componente de chat em SvelteKit conectando via WebSocket nativo do browser, com reconexão automática.

DoD:

- Mensagens chegam em tempo real nos dois lados.
- Limite anti-spam testado (ex.: N mensagens por minuto por conversa).
- Um usuário bloqueado não consegue enviar mensagem para quem o bloqueou.
- (Opcional, não bloqueador) avaliar migrar o contador de interessados da Etapa 3 para o mesmo canal WebSocket, se o volume de uso já justificar.

---

## Etapa 5 — Notificações em camadas

**Objetivo:** avisar profissionais e contratantes fora da aba aberta, especialmente para chamados com janela curta.

Entregáveis:

- Web Push via PWA (`webpush-go` no backend, Push API no service worker do frontend) para Android e iOS 16.4+ com app instalado.
- Fallback WhatsApp/SMS (Twilio ou API do WhatsApp Business — registrar a escolha final como decisão de produto ao implementar) para chamados de janela curta e usuários iOS sem o PWA instalado.
- E-mail para eventos não urgentes (confirmação, avaliação recebida, mudança de plano).
- Jobs Asynq disparando cada canal nos eventos certos: novo chamado compatível, seleção, não seleção, expiração, cancelamento — conectando aos hooks deixados como TODO na Etapa 3.
- Tabela `notification_consents` por canal (LGPD — AGENTS.md "Privacidade e segurança"), checada antes de qualquer disparo.

DoD:

- Um chamado com janela de 2h dispara push (ou fallback) em menos de X segundos após publicação (definir X junto ao time — requisito mais sensível para janelas curtas).
- Usuário consegue desativar cada canal individualmente via UI.
- Nenhum segredo/token de notificação aparece em log (auditar `internal/notifications` especificamente nesta etapa).

---

## Etapa 6 — PWA instalável

**Objetivo:** app instalável sem loja, cobrindo o gap de push nativo em iOS.

Entregáveis:

- `manifest.json` (nome, ícones, cor de tema, `display: standalone`) via `vite-plugin-pwa`.
- Service worker com cache de assets estáticos e estratégia de fallback offline para telas já visitadas.
- Onboarding explicando "Adicionar à Tela de Início" para iOS, condicionado à detecção de plataforma no frontend.

DoD:

- App instalável no Android via banner nativo e no iOS via instrução manual testada em dispositivo real ou emulador.
- Telas já visitadas abrem offline (cache básico).

---

## Etapa 7 — Confirmação pós-serviço e avaliação bilateral

**Objetivo:** fechar o ciclo de confiança do marketplace.

Entregáveis:

- Tabela `service_confirmations`: job Asynq agendado pergunta a ambas as partes, separadamente, após a data prevista, se o serviço ocorreu.
- Tabela `reviews`: avaliação bilateral, só liberada após confirmação legítima de interação (validado no backend, nunca só na UI).
- Mecanismo anti-retaliação mínimo: avaliações reveladas simultaneamente após ambas enviadas (ou janela de edição/contestação — registrar qual hipótese foi adotada).
- Reputação alimentada também por cancelamentos, no-show e ausência de resposta, com endpoint de contestação.

DoD:

- Avaliação só é possível para interações com confirmação registrada (ou processo definido para confirmação unilateral, se essa hipótese for adotada — registrar a decisão).
- Teste cobrindo tentativa de avaliar sem confirmação (deve falhar com 403/422).
- Teste cobrindo fluxo de contestação básico.

---

## Etapa 8 — Favoritos e recontratação

**Objetivo:** suportar recorrência, parte central do valor do produto.

Entregáveis:

- Tabela `favorites` (contratante → profissional).
- Endpoint que pré-preenche um novo chamado ou contato a partir de um favorito.

DoD:

- Contratante salva, lista e remove favoritos via UI.
- Fluxo de "chamar novamente" pré-preenche dados do chamado anterior.

---

## Etapa 9 — Moderação, denúncia, bloqueio e verificação

**Objetivo:** confiança e segurança administradas com trilha de auditoria.

Entregáveis:

- `internal/moderation`: tabelas `moderation_cases` (denúncia, análise, decisão, recurso) e `verifications` (identidade/documentos, estado, consentimento e finalidade claros).
- Endpoints de denúncia e bloqueio a partir de perfil e chat (generalizando a tabela `blocked_users` criada de forma mínima na Etapa 4).
- Painel admin simples (pode ser uma área protegida no próprio frontend SvelteKit, ou um admin interno separado) cobrindo fila de moderação e verificação.
- Endpoint de contestação/recurso para suspensão de conta.
- Selo de verificação nunca gerado por pagamento — sempre atrelado a um registro de checagem real em `verifications`.

DoD:

- Um caso de denúncia percorre o ciclo completo: aberto → analisado → decidido → (opcional) recurso, tudo auditável via `AuditEvent`.
- Suspensão de conta bloqueia acesso (checada no middleware de autenticação) e é reversível via recurso aprovado.

---

## Etapa 10 — Monetização: assinatura Premium e boosts

**Objetivo:** freemium funcionando, sem comprometer a relevância orgânica.

Entregáveis:

- `internal/subscriptions`: tabela `subscriptions` integrada ao Mercado Pago (assinatura recorrente, Pix/cartão), com webhook de confirmação de pagamento tratado de forma idempotente.
- Tabela `boosts`: promoção com início, fim e critérios, sempre rotulada ("Destaque"/"Patrocinado") na resposta da API e na UI — nunca disfarçada de resultado orgânico.
- Limites do plano gratuito implementados como configuração (não hardcoded) — categoria única, chamados limitados etc., conforme "Modelo freemium" do AGENTS.md; preços/limites definitivos ficam como hipótese configurável.
- Ranking da Etapa 2 revisado para intercalar boost apenas entre resultados já relevantes, nunca promovendo incompatíveis.
- Endpoint de cancelamento de assinatura self-service.

DoD:

- Teste garante que um perfil incompatível nunca aparece à frente de um compatível só por causa de boost.
- Assinatura, cobrança recorrente e cancelamento testados em sandbox do Mercado Pago.
- Rótulo de patrocinado presente em toda resposta de API que inclua resultado impulsionado, sem exceção.

---

## Etapa 11 — Hardening, observabilidade e deploy de produção

**Objetivo:** operar com segurança e resiliência na VPS/Proxmox.

Entregáveis:

- Traefik como reverse proxy com TLS automático, mesmo padrão dos outros serviços já em produção.
- Backup automatizado de Postgres (`pg_dump` agendado via Asynq/cron + retenção) — dado sensível (CPF, localização, avaliações) exige isso desde o primeiro dia.
- `/metrics` (Prometheus) exposto pela `api`, dashboards em Grafana — reaproveitando o padrão de observabilidade já usado em `api.newlifefibra.com.br`.
- Logs estruturados sem dados pessoais/segredos, auditados especificamente nesta etapa.
- Rate limiting e proteção em autenticação, upload, chat, assinatura e painel administrativo.
- Auditoria final de paginação e limites em busca, chat e avaliações (as etapas anteriores já deveriam cobrir isso — esta etapa confirma).
- Feature flags simples (tabela de config ou variável de ambiente por flag) para experimentos de ranking e Premium.

DoD:

- Restauração de backup testada manualmente ao menos uma vez.
- Checklist de segurança (autenticação, upload, chat, admin) revisado item a item.
- Nenhum dado sensível encontrado em logs de produção durante amostragem.

---

## Etapa 12 — Testes e qualidade contínua (transversal)

Não é uma etapa isolada no tempo — cada etapa acima já deve sair com testes proporcionais ao risco (`go test` + `testcontainers-go` no backend, `Vitest`/`Playwright` no frontend). Esta etapa é o checkpoint final antes de abrir para usuários reais:

- Cobertura garantida nos fluxos de maior risco: permissões, seleção/expiração de chamado, ranking, boosts, estados de assinatura.
- Revisão de acessibilidade básica nas telas mobile do SvelteKit.
- Revisão jurídica dos termos (profissional, contratante, privacidade, avaliações, Premium) e da lista de categorias excluídas/incluídas do AGENTS.md — fora do escopo de engenharia, mas bloqueador de lançamento.

---

## Caminho de evolução (pós-MVP, fora do roteiro acima)

- App nativo (Expo/React Native ou Kotlin/Swift) consumindo a mesma API Go via o contrato OpenAPI já existente, sem reescrever regra de negócio.
- Separar banco por domínio só quando a VPS única virar gargalo real (medir antes de separar).
- Trocar storage local por bucket S3-compatível só quando o volume de mídia justificar.
- Avaliar `NATS` ou similar só se o Redis Pub/Sub do chat mostrar limite real de escala — não antecipar.

Nenhum desses itens deve ser antecipado sem necessidade concreta (mesmo princípio de engenharia do AGENTS.md: não introduzir dependência "para o futuro").

## Fora de escopo em qualquer etapa

Ver "Fora do escopo inicial" no AGENTS.md — carteira digital, split de pagamento, comissão por serviço, garantia/reembolso do serviço, folha de pagamento, gestão de jornada/escala, contratação trabalhista, IA complexa prematura, gamificação coercitiva, penalidade automática por recusa. Ver também "Foco inicial recomendado" para a lista de categorias excluídas por risco jurídico (saúde/medicina clínica, advocacia, segurança privada autônoma, consultoria de investimento). Se uma etapa parecer exigir um desses itens, pare e questione o design antes de implementar.

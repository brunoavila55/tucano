# CLAUDE.md — Roteiro de desenvolvimento

## Como usar este documento

Antes de tocar em qualquer código, leia **[AGENTS.md](AGENTS.md)** (regras de produto, o que a plataforma pode e não pode fazer, entidades, critério de qualidade) e **[stack.md](stack.md)** (decisões técnicas e por quê). Este arquivo não repete essas regras — ele é o roteiro que organiza a construção do MVP em etapas sequenciais, na ordem em que devem ser implementadas.

Cada etapa abaixo é uma unidade de trabalho: só avance para a próxima quando a atual satisfizer seu **Definition of Done (DoD)** e o [Critério de qualidade do AGENTS.md](AGENTS.md#critério-de-qualidade). Não pule etapas — cada uma depende de dados/models criados na anterior. Dentro de uma etapa, siga o fluxo "Como trabalhar neste repositório" do AGENTS.md.

Sempre que uma etapa esbarrar em uma das ambiguidades listadas no AGENTS.md (stack, limites e preço dos planos, regras de ranking, compartilhamento de localização e contato, verificação de identidade, moderação, termos jurídicos, inclusão de pagamentos do serviço), registre a hipótese ou pare e pergunte — não decida silenciosamente.

---

## Etapa 0 — Fundação do projeto

**Objetivo:** ter um monólito Django rodando localmente e em Docker Compose, sem nenhuma feature de produto ainda.

Entregáveis:
- Projeto Django criado com `uv`, Python 3.12, Django 5.2 (stack.md §0), já em ASGI (Daphne) desde o início, já que Channels entra mais adiante (Etapa 4 — Chat).
- `docker-compose.yml` com os serviços descritos em stack.md §10: `web`, `worker`, `beat`, `postgres` (com PostGIS 3.4), `redis`, `caddy`.
- Apps Django vazios criados por domínio: `accounts`, `professionals`, `clients`, `requests`, `chat`, `reviews`, `subscriptions`, `moderation` (stack.md §1).
- `django.contrib.gis` habilitado e testado com uma migração trivial usando um campo geoespacial.
- Configuração de settings por ambiente (dev/produção), segredos fora do repositório (`.env` + `.gitignore`).
- `pytest-django` configurado com um teste de sanidade passando.
- Repositório git conectado a `github.com/brunoavila55/tucano`.

DoD:
- `docker compose up` sobe todos os serviços sem erro.
- Um teste `pytest` roda e passa dentro do container.
- Django Admin acessível localmente.

---

## Etapa 1 — Identidade e perfis

**Objetivo:** cadastro, login e os dois tipos de perfil coexistindo na mesma conta.

Entregáveis:
- App `accounts`: model `User` via `django-allauth` (stack.md §1).
- Apps `professionals`/`clients`: models `ProfessionalProfile` e `ClientProfile`, ligados a `User`, permitindo que a mesma conta tenha os dois perfis (AGENTS.md — "Requisitos funcionais mínimos").
- Fluxo de escolha/alternância entre perfil profissional e contratante.
- Autorização no servidor desde o início: mixins/decorators por papel, nunca esconder botão só no template (stack.md §1, AGENTS.md "Princípios de engenharia").
- Django Admin cobrindo os models criados.
- Templates base + Tailwind configurado (stack.md §2), mobile-first.

DoD:
- Cadastro, login, logout, verificação de e-mail e recuperação de senha funcionam via UI.
- Um usuário pode ter perfil profissional e de contratante simultaneamente.
- Testes de permissão: um contratante não acessa views exclusivas de profissional e vice-versa.

---

## Etapa 2 — Categorias, região e disponibilidade

**Objetivo:** profissional configurável e buscável por categoria e localização aproximada, num marketplace geral (sem recorte de segmento).

Entregáveis:
- Model `ServiceCategory`, gerenciável pelo Django Admin — catálogo aberto, não uma lista fixa por segmento (AGENTS.md — "Foco inicial recomendado"). Ao popular a base inicial, respeitar a lista de exclusões do AGENTS.md (saúde/medicina clínica, advocacia, segurança privada autônoma, consultoria de investimento) e incluir explicitamente categorias com conselho de classe que são permitidas (estética/beleza, engenharia/arquitetura, contabilidade), além das de eventos/gastronomia/casa.
- Model `Availability` associado a `ProfessionalProfile`.
- Campo geoespacial de região atendida no perfil profissional (PostGIS, índice geoespacial desde já — stack.md §4).
- Edição de perfil profissional: bio, categoria principal, habilidades, região, preço de referência opcional, portfólio básico (fotos via Django Storages local — stack.md §8).
- Busca simples por categoria + região com HTMX para paginação/filtros (stack.md §2), sem ranking sofisticado ainda (ordenação por distância é suficiente aqui).

DoD:
- Um profissional consegue configurar categoria, região e disponibilidade.
- Busca por categoria retorna profissionais ordenados por distância aproximada, em qualquer região do país.
- Distância exibida é aproximada, nunca a posição exata (AGENTS.md — Privacidade).
- Tentar cadastrar uma categoria da lista de exclusão é bloqueado ou sinalizado para moderação.

---

## Etapa 3 — Chamados e janela de interesse

**Objetivo:** o fluxo central do produto — publicar, demonstrar interesse, selecionar, expirar — com janela de duração configurável. Não existe um fluxo separado de "chamado urgente": todo chamado usa a mesma mecânica, e a urgência é só reflexo de o contratante escolher uma janela curta.

Entregáveis:
- App `requests`: model `ServiceRequest` com os campos do fluxo "Publicar um chamado" (categoria, data/horário ou período, região, quantidade de posições, descrição, valor/faixa opcional, requisitos, **janela de interesse** como choice fixo: 2 horas, 5 horas, 24 horas, 3 dias).
- Estados mínimos do chamado (`draft`, `open`, `partially_filled`, `filled`, `expired`, `cancelled`, `completed`) implementados como choices/state machine simples.
- Model `Interest` com seus estados (`applied`, `shortlisted`, `selected`, `not_selected`, `withdrawn`, `expired`).
- Regra: a janela nunca ultrapassa o horário de início do serviço; perto demais do horário, o formulário sugere uma opção de janela mais curta.
- CRUD de chamado: criar, editar, encerrar manualmente a qualquer momento, cancelar (com motivo).
- Formulário de publicação otimizado para ser rápido (meta: menos de 30s — AGENTS.md).
- Profissional visualiza chamados compatíveis com sua categoria/região e demonstra interesse.
- Contratante visualiza lista de interessados (atualizada via HTMX + polling/recarregamento parcial — sem WebSocket nesta etapa, ver stack.md §3) e seleciona manualmente.
- Celery + Redis (stack.md §5) com `beat` agendando a expiração automática do chamado ao fim da janela escolhida.
- Respostas claras para todos os envolvidos ao final: selecionado, não selecionado, expirado, cancelado (AGENTS.md).
- Registro de auditoria (`AuditEvent`) para publicação, interesse, seleção, retirada, expiração, cancelamento.
- Limite de notificações repetidas e chamados duplicados (mesmo contratante, mesma categoria/janela) — regra anti-spam mínima.

DoD:
- Fluxo completo publicar → interessar-se → selecionar → atualizar posições restantes funciona ponta a ponta para qualquer uma das quatro janelas.
- Selecionar uma posição não afasta ninguém das posições restantes, se houver mais de uma (AGENTS.md).
- Um chamado sem seleção expira automaticamente via Celery beat, sem intervenção manual, mesmo com o processo web reiniciado.
- Testes cobrindo transições de estado de `ServiceRequest` e `Interest`, incluindo casos de abuso (ex.: selecionar além da quantidade de posições, janela que ultrapassa o horário do serviço).
- Auditoria consultável no Admin para um chamado de teste ponta a ponta.

---

## Etapa 4 — Conversa entre as partes (chat)

**Objetivo:** contratante e profissional trocam mensagens em tempo real após interesse/seleção. É aqui que a infraestrutura de tempo real (Channels/Redis) entra no projeto pela primeira vez.

Entregáveis:
- `channels` + `channels_redis` integrados (stack.md §3); `web` já roda em Daphne desde a Etapa 0.
- App `chat`: model `Conversation` + mensagens, com WebSocket para entrega em tempo real.
- Conversa é aberta automaticamente ao selecionar um profissional (AGENTS.md — "selecionado: ... abertura da conversa").
- Proteção básica contra spam: limite de mensagens/tempo, bloqueio de usuário.
- UI de chat via templates + HTMX/WebSocket, mobile-first.

DoD:
- Mensagens chegam em tempo real nos dois lados.
- Limite anti-spam testado (ex.: N mensagens por minuto).
- Um usuário bloqueado não consegue enviar mensagem para quem o bloqueou.
- (Opcional, não bloqueador) avaliar migrar o contador de interessados da Etapa 3 para essa mesma infraestrutura de WebSocket, se o volume de uso já justificar.

---

## Etapa 5 — Notificações em camadas

**Objetivo:** avisar profissionais e contratantes fora da aba aberta, especialmente para chamados com janela curta.

Entregáveis:
- Web Push via PWA (service worker + Push API) para Android e iOS 16.4+ com app instalado (stack.md §6).
- Fallback WhatsApp/SMS (Twilio, Zenvia ou API do WhatsApp Business) para chamados de janela curta e usuários iOS sem o PWA instalado.
- E-mail para eventos não urgentes (confirmação, avaliação recebida, mudança de plano).
- Jobs Celery disparando cada canal nos eventos certos: novo chamado compatível, seleção, não seleção, expiração, cancelamento.
- Registro de consentimento por canal (LGPD — AGENTS.md "Privacidade e segurança").

DoD:
- Um chamado com janela de 2h dispara push (ou fallback) em menos de X segundos após publicação (definir X junto ao time, é o requisito mais sensível do produto para janelas curtas).
- Usuário consegue desativar cada canal individualmente.
- Nenhum segredo/token de notificação aparece em log.

---

## Etapa 6 — PWA instalável

**Objetivo:** app instalável sem loja, cobrindo o gap de push nativo em iOS.

Entregáveis:
- `manifest.json` (nome, ícones, cor de tema, `display: standalone`).
- Service worker com cache de assets estáticos (stack.md §7), usando `django-pwa` ou implementação manual.
- Onboarding explicando "Adicionar à Tela de Início" para iOS, condicionado à detecção de plataforma.

DoD:
- App instalável no Android via banner nativo e no iOS via instrução manual testada em dispositivo real ou emulador.
- Telas já visitadas abrem offline (cache básico).

---

## Etapa 7 — Confirmação pós-serviço e avaliação bilateral

**Objetivo:** fechar o ciclo de confiança do marketplace.

Entregáveis:
- Model `ServiceConfirmation`: job Celery pergunta a ambas as partes, separadamente, após a data prevista, se o serviço ocorreu.
- Model `Review`: avaliação bilateral, só liberada após confirmação legítima de interação (nunca antes).
- Mecanismos anti-retaliação e anti-fraude mínimos: ex. avaliações reveladas simultaneamente após ambas enviadas, ou janela para edição/contestação.
- Reputação alimentada também por cancelamentos, no-show e ausência de resposta, com direito a contestação (AGENTS.md).

DoD:
- Avaliação só é possível para interações com confirmação registrada de ambos os lados (ou processo definido para confirmação unilateral, se essa hipótese for adotada — registrar a decisão).
- Teste cobrindo tentativa de avaliar sem confirmação (deve falhar).
- Teste cobrindo fluxo de contestação básico.

---

## Etapa 8 — Favoritos e recontratação

**Objetivo:** suportar recorrência, parte central do valor do produto.

Entregáveis:
- Model `Favorite` (contratante → profissional).
- Reutilização de dados de um favorito para novo contato ou novo chamado direcionado.

DoD:
- Contratante salva, lista e remove favoritos.
- Fluxo de "chamar novamente" pré-preenche dados do chamado anterior.

---

## Etapa 9 — Moderação, denúncia, bloqueio e verificação

**Objetivo:** confiança e segurança administradas com trilha de auditoria.

Entregáveis:
- App `moderation`: models `ModerationCase` (denúncia, análise, decisão, recurso) e `Verification` (identidade/documentos, estado, consentimento e finalidade claros).
- Denúncia e bloqueio disponíveis a partir de perfil e chat.
- Django Admin cobrindo fila de moderação e verificação (stack.md §1 — "de graça").
- Processo de contestação/recurso para suspensão de conta.
- Selo de verificação nunca vendável, sempre atrelado a checagem real (AGENTS.md).

DoD:
- Um caso de denúncia percorre o ciclo completo: aberto → analisado → decidido → (opcional) recurso, tudo auditável.
- Suspensão de conta bloqueia acesso e é reversível via recurso aprovado.

---

## Etapa 10 — Monetização: assinatura Premium e boosts

**Objetivo:** freemium funcionando, sem comprometer a relevância orgânica.

Entregáveis:
- App `subscriptions`: model `Subscription` integrado ao Mercado Pago (assinatura recorrente, Pix/cartão — stack.md §9).
- Model `Boost`: promoção com início, fim e critérios, sempre rotulada ("Destaque"/"Patrocinado") na UI — nunca disfarçada de resultado orgânico (AGENTS.md).
- Limites do plano gratuito implementados (categoria única, chamados limitados etc. — conforme "Modelo freemium" do AGENTS.md; preços/limites definitivos ficam como hipótese configurável, não hardcoded).
- Ranking da Etapa 2 revisado para intercalar boost apenas entre resultados já relevantes, nunca promovendo incompatíveis (AGENTS.md — "Encontrar profissionais").
- Cancelamento de assinatura self-service.

DoD:
- Teste garante que um perfil incompatível nunca aparece à frente de um compatível só por causa de boost.
- Assinatura, cobrança recorrente e cancelamento testados em sandbox do Mercado Pago.
- Rótulo de patrocinado visível em todo resultado impulsionado, sem exceção.

---

## Etapa 11 — Hardening, observabilidade e deploy de produção

**Objetivo:** operar com segurança e resiliência na VPS.

Entregáveis:
- Caddy como proxy reverso com TLS automático (stack.md §10).
- Backup automatizado de Postgres (`pg_dump` agendado + retenção) — dado sensível (CPF, localização, avaliações) exige isso desde o primeiro dia.
- Logs estruturados sem dados pessoais/segredos.
- Rate limiting e proteção em autenticação, upload, chat, assinatura e painel administrativo (AGENTS.md — "Princípios de engenharia").
- Paginação e limites em busca, chat e avaliações (verificar que todas as etapas anteriores já cobriram isso; esta etapa é a auditoria final).
- Feature flags para experimentos de ranking e Premium.

DoD:
- Restauração de backup testada manualmente ao menos uma vez.
- Checklist de segurança (autenticação, upload, chat, admin) revisado item a item.
- Nenhum dado sensível encontrado em logs de produção durante amostragem.

---

## Etapa 12 — Testes e qualidade contínua (transversal)

Não é uma etapa isolada no tempo — cada etapa acima já deve sair com testes proporcionais ao risco (`pytest-django`, stack.md §11). Esta etapa é o checkpoint final antes de abrir para usuários reais:

- Cobertura garantida nos fluxos de maior risco: permissões, seleção/expiração de chamado, ranking, boosts, estados de assinatura (AGENTS.md + stack.md §11).
- Revisão de acessibilidade básica nas telas mobile.
- Revisão jurídica dos termos (profissional, contratante, privacidade, avaliações, Premium) e da lista de categorias excluídas/incluídas do AGENTS.md — fora do escopo de engenharia, mas é bloqueador de lançamento (AGENTS.md).

---

## Caminho de evolução (pós-MVP, fora do roteiro acima)

Ver stack.md §12: `djangorestframework` sobre os mesmos models para viabilizar app nativo (Expo/React Native) sem reescrever regra de negócio; separar banco de app só quando a VPS única virar gargalo real; trocar storage local por bucket S3-compatível só quando o volume de mídia justificar. Nenhum desses itens deve ser antecipado sem necessidade concreta (AGENTS.md — "Princípios de engenharia").

## Fora de escopo em qualquer etapa

Ver "Fora do escopo inicial" no AGENTS.md — carteira digital, split de pagamento, comissão por serviço, garantia/reembolso do serviço, folha de pagamento, gestão de jornada/escala, contratação trabalhista, IA complexa prematura, gamificação coercitiva, penalidade automática por recusa. Ver também "Foco inicial recomendado" para a lista de categorias excluídas por risco jurídico (saúde/medicina clínica, advocacia, segurança privada autônoma, consultoria de investimento). Se uma etapa parecer exigir um desses itens, pare e questione o design antes de implementar.

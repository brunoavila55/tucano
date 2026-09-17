# Tucano

Marketplace nacional e freemium que conecta contratantes a profissionais autônomos disponíveis para serviços pontuais (eventos, gastronomia, casa, manutenção, estética/beleza, engenharia/arquitetura, contabilidade e outras categorias, respeitando as exclusões jurídicas do produto).

`tucano` é o codinome de desenvolvimento — o branding final é uma decisão separada e não afeta nomes de módulo/pacote.

A plataforma **não** processa o pagamento do serviço, não cobra comissão e não é empregadora dos profissionais: ela cuida de descoberta local, disponibilidade, reputação e contato direto entre as partes.

## Documentação de referência

Antes de mexer em qualquer código, leia nesta ordem:

1. **[AGENTS.md](AGENTS.md)** — regras de produto: visão, posicionamento, decisões já tomadas, fluxos essenciais (chamado, janela de interesse, seleção), entidades do domínio, limites jurídicos, privacidade e critério de qualidade.
2. **[stack.md](stack.md)** — decisões técnicas e o porquê de cada uma.
3. **[CLAUDE.md](CLAUDE.md)** — roteiro de desenvolvimento do MVP, dividido em etapas sequenciais (cada uma depende dos models/dados da anterior).

Qualquer ambiguidade de produto (stack, preços/limites de planos, ranking, localização/contato, verificação de identidade, moderação, termos jurídicos) deve virar uma hipótese registrada ou uma pergunta — nunca uma decisão silenciosa. Ver "Como trabalhar neste repositório" em AGENTS.md.

## Stack

- **Backend:** Django 5.2 (Python 3.12), monólito modular, ASGI via Daphne.
- **Apps por domínio:** `accounts`, `professionals`, `clients`, `requests`, `chat`, `reviews`, `subscriptions`, `moderation`.
- **Frontend:** Django Templates + HTMX (+ Alpine.js pontual) + Tailwind CSS, mobile-first.
- **Tempo real:** Django Channels + Redis (chat).
- **Banco de dados:** PostgreSQL 16 + PostGIS 3.4 (`django.contrib.gis`) para região atendida e distância aproximada.
- **Jobs assíncronos:** Celery + Redis, com `beat` para expiração automática de chamados e outras tarefas agendadas.
- **Notificações:** Web Push (PWA), fallback WhatsApp/SMS (Twilio) e e-mail.
- **Pagamentos:** Mercado Pago, apenas para a assinatura Premium (nunca para o valor do serviço).
- **Infra:** Docker Compose (`web`, `worker`, `beat`, `postgres`, `redis`, `caddy`), Caddy como proxy reverso com TLS automático.
- **Testes:** `pytest-django`.

Detalhes e justificativas de cada escolha em [stack.md](stack.md).

## Estrutura do repositório

```
apps/            # apps Django por domínio de produto
  accounts/      # User, autenticação (django-allauth)
  professionals/ # ProfessionalProfile, categorias, disponibilidade
  clients/       # ClientProfile
  requests/      # ServiceRequest, Interest, janela de interesse
  chat/          # Conversation, mensagens em tempo real
  reviews/       # avaliação bilateral, confirmação pós-serviço
  subscriptions/ # assinatura Premium, boosts
  moderation/    # denúncia, bloqueio, verificação
config/          # settings, urls, asgi/wsgi, Celery
docker/          # configuração auxiliar (ex.: Caddyfile)
templates/       # templates Django
static/          # assets estáticos versionados
media/           # uploads (dev local)
```

## Como rodar localmente

Pré-requisitos: [`uv`](https://docs.astral.sh/uv/) e Docker (com Compose).

```bash
cp .env.example .env
# ajuste DJANGO_SECRET_KEY e demais variáveis conforme necessário

docker compose up
```

Isso sobe `web` (Daphne), `worker` e `beat` (Celery), `postgres` (PostGIS) e `redis`, atrás do `caddy` como proxy reverso (em dev, exposto em `http://localhost:8080`).

Canais de notificação (Web Push, WhatsApp/SMS, Mercado Pago) ficam desabilitados enquanto as variáveis correspondentes em `.env` estiverem em branco — o envio é apenas registrado em vez de chamar o provedor real.

### Rodando sem Docker

```bash
uv sync
uv run manage.py migrate
uv run manage.py createsuperuser
uv run manage.py runserver
```

Requer PostgreSQL com PostGIS e Redis acessíveis localmente (ajuste `DATABASE_URL` e `REDIS_URL` em `.env`).

### Testes

```bash
uv run pytest
```

ou, dentro do container:

```bash
docker compose exec web pytest
```

## Roteiro de desenvolvimento

O MVP é construído em etapas sequenciais definidas em [CLAUDE.md](CLAUDE.md): fundação do projeto → identidade e perfis → categorias/região/disponibilidade → chamados e janela de interesse → chat → notificações → PWA → confirmação e avaliação → favoritos → moderação → monetização → hardening/observabilidade → testes e qualidade contínua. Não pule etapas: cada uma depende de models/dados criados na anterior.

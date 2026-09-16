# Stack técnica — MVP Marketplace de Profissionais

## Contexto e restrições que definiram a stack

- Infraestrutura em **VPS própria** (sem BaaS tipo Supabase/Firebase).
- **Sem publicação em App Store/Play Store** na fase de validação — nada de custo de loja nem tempo de revisão.
- Mobile first, mas via **web/PWA**, não app nativo, por enquanto.
- Fluxo central (chamado urgente, janela de 2h) depende de notificação chegando rápido.
- Migrações versionadas, permissões tratadas no servidor, monólito modular — princípios já definidos no AGENTS.md do produto.

---

## 0. Versões e ferramentas de projeto

- **Python 3.12**, **Django 5.2** (LTS, suporte até 2028).
- **PostgreSQL 16 + PostGIS 3.4**.
- **`uv`** como gerenciador de dependências e ambiente virtual (lockfile determinístico, instalação rápida).
- Repositório: `github.com/brunoavila55/tucano` (`tucano` é codinome de desenvolvimento; o branding final do produto é decisão separada e não afeta nomes de módulo/pacote).

## 1. Backend: Django

**Django (modo full, não só API)** é o núcleo do sistema.

- **Apps Django** organizados por domínio, não por camada técnica: `accounts`, `professionals`, `clients`, `requests` (ServiceRequest/Interest), `chat`, `reviews`, `subscriptions`, `moderation`.
- **Django Admin** cobre, de graça:
  - Moderação (`ModerationCase`, denúncias, suspensão de conta).
  - Verificação de identidade/documentos.
  - Visualização de assinaturas Premium e boosts.
- **Django ORM + migrações** — versionamento de schema nativo, sem ferramenta externa.
- **Autenticação**: `django-allauth` (login, cadastro, verificação de e-mail, recuperação de senha).
- **Autorização no servidor**: permissões por papel (contratante/profissional) via mixins/decorators de view + regras explícitas nos querysets — nunca confiar em esconder botão no template.

## 2. Frontend: Templates + HTMX

- **Django Templates** para toda a renderização.
- **HTMX** para interatividade sem SPA:
  - Atualizar contador de interessados no chamado urgente sem recarregar página.
  - Abrir/fechar modais de perfil, portfólio, chat.
  - Paginação e filtros de busca via partial swap.
- **Alpine.js** (opcional, leve) para pequenas interações puramente client-side que não precisam ir ao servidor (abrir/fechar menu, toggle de disponibilidade antes de confirmar).
- **Tailwind CSS** para estilização rápida e consistente, mobile-first por padrão (utility classes já pensadas em breakpoints).

## 3. Tempo real: Django Channels + Redis

O chat é o único ponto do MVP que exige push real desde o início — introduzido junto com ele (ver roteiro em CLAUDE.md), não na Etapa 0.

A atualização do chamado (contador de interessados, posições preenchidas, expiração da janela de interesse) começa simples, com HTMX + polling/recarregamento parcial; migrar essa parte para WebSocket é um incremento posterior, só quando o volume justificar — não é um requisito de lançamento, já que não existe mais um fluxo especial de "chamado urgente" com exigência de sub-segundo.

Implementação (a partir da introdução do chat):
- `channels` + `channels_redis` como camada de canal.
- Redis também serve como **broker de fila** (ver item 5) e cache de sessão, evitando subir mais um serviço além do Postgres.
- No template, HTMX pode se conectar a um endpoint WebSocket via extensão `htmx-ws`, ou usar JS puro para os poucos pontos que precisam de push real.

## 4. Banco de dados: PostgreSQL + PostGIS

- **PostgreSQL** como banco único (sem separar leitura/escrita nesta fase).
- **PostGIS** (`django.contrib.gis` + `GeoDjango`) para:
  - Região atendida pelo profissional.
  - Distância aproximada entre contratante e profissional na busca/ranking.
- Índices geoespaciais desde o início — é mais barato habilitar agora do que migrar depois com dados reais.

## 5. Jobs em background: Celery + Redis (ou Django-Q como alternativa mais simples)

Necessário para:
- Expirar chamados automaticamente após a janela de 2h (ou o prazo definido).
- Disparar notificações (push, WhatsApp) quando surge um chamado compatível.
- Calcular/atualizar métricas de ranking periodicamente.
- Confirmação pós-serviço (pergunta agendada para depois da data prevista).

**Celery** é a escolha para o MVP — mais robusto e testado com Django, com melhor observabilidade (Flower), o que importa especialmente para o job de expiração automática de chamados, que não pode falhar silenciosamente.

## 6. Notificações

Como push nativo não existe sem app na loja, a estratégia é em camadas:

- **Web Push (PWA)**:
  - Android: funciona plenamente e de graça via service worker + Push API.
  - iOS 16.4+: funciona, mas só depois que o usuário faz "Adicionar à Tela de Início" manualmente — desenhar esse passo no onboarding.
- **Fallback via WhatsApp/SMS** para o alerta de chamado urgente (o ponto mais sensível a atraso):
  - Twilio, Zenvia ou API do WhatsApp Business — custo por mensagem enviada, sem custo de publicação.
  - Usado principalmente para iOS antes de o usuário instalar o PWA, ou como reforço em chamados com urgência alta.
- **E-mail** como canal secundário para eventos não urgentes (confirmação, avaliação recebida, mudança de plano).

## 7. PWA

- `manifest.json` (nome, ícones, cor de tema, `display: standalone`).
- **Service Worker** para:
  - Cache de assets estáticos (funcionamento offline básico de telas já visitadas).
  - Registro de push notifications.
- Sem necessidade de framework JS pesado — o service worker pode ser escrito à mão ou com `django-pwa` para simplificar o setup inicial.

## 8. Armazenamento de mídia

- **Django Storages** apontando para disco local da VPS no início (fotos de perfil, portfólio).
- Migração futura simples para um bucket S3-compatível (Backblaze B2, Wasabi, ou S3 mesmo) quando o volume de mídia justificar — trocar o `STORAGES` backend sem mudar código de aplicação.

## 9. Pagamentos (somente assinatura Premium)

- **Mercado Pago** (assinatura recorrente / Pix / cartão) — maior familiaridade do usuário brasileiro.
- Importante: isso é **só a cobrança do plano Premium**. O valor do serviço entre contratante e profissional nunca passa pela plataforma (decisão já fixada no AGENTS.md).

## 10. Infraestrutura na VPS

```
┌─────────────────────────────────────────────┐
│                   VPS                        │
│                                               │
│  ┌───────────┐   ┌───────────┐  ┌─────────┐  │
│  │  Caddy    │──▶│  Django   │─▶│ Postgres│  │
│  │ (proxy +  │   │  (Gunicorn/│  │+ PostGIS│  │
│  │  TLS auto)│   │  Daphne)  │  └─────────┘  │
│  └───────────┘   └───────────┘               │
│                       │                       │
│                  ┌────┴────┐                  │
│                  │  Redis  │                  │
│                  └────┬────┘                  │
│                       │                       │
│                ┌──────┴──────┐                │
│                │ Celery      │                │
│                │ worker+beat │                │
│                └─────────────┘                │
└─────────────────────────────────────────────┘
```

- **Docker Compose** orquestrando: `web` (Django via Daphne, já que Channels precisa de ASGI), `worker` (Celery), `beat` (agendador do Celery), `postgres`, `redis`, `caddy`.
- **Caddy** como proxy reverso — TLS automático via Let's Encrypt sem configuração manual.
- Servidor único (4 vCPU / 8GB de RAM é um ponto de partida razoável) até haver tração real que justifique separar banco de app.
- **Backup automatizado** de Postgres (`pg_dump` agendado + retenção) desde o primeiro dia — há dado sensível (CPF, localização, avaliações) que a LGPD e o bom senso exigem proteger.

## 11. Testes

- `pytest-django` para testes de regra de negócio: permissões, estados do chamado/interesse, ranking, boosts, assinatura.
- Cobertura proporcional ao risco, como já orienta o AGENTS.md — não é necessário 100%, mas os fluxos de seleção/expiração e as regras de autorização precisam de teste.

## 12. Caminho de evolução (quando fizer sentido)

Nada aqui é definitivo — só o necessário para o MVP:

- **App nativo depois**: adicionar `djangorestframework` por cima dos mesmos models/regras de negócio, sem reescrever domínio, e então um cliente React Native (Expo) consumindo essa API. A camada de apresentação muda; a regra de negócio não.
- **Separar banco de app**: só quando a VPS única virar gargalo real.
- **Trocar armazenamento local por bucket**: só quando o volume de mídia justificar.

## Resumo em uma linha

Django (templates + HTMX + Channels) sobre PostgreSQL/PostGIS, rodando em Docker Compose numa única VPS atrás de Caddy, com Celery+Redis para jobs assíncronos, PWA para instalação sem loja, e WhatsApp/SMS como reforço de notificação enquanto push em iOS depende de instalação manual do usuário.

# Roadmap do Tucano

Este arquivo mostra o progresso da reconstrução do Tucano em Go + SvelteKit. O detalhamento técnico e os critérios de conclusão continuam no [CODEX.md](CODEX.md); as decisões de produto permanecem no [AGENTS.md](AGENTS.md).

## Progresso atual

**Etapa atual: 3 — Chamados e janela de interesse**

```text
Etapas de implementação concluídas: 3 de 12
[█████░░░░░░░░░░░░░░░] 25%
```

O percentual acima conta as macroetapas de implementação de 0 a 11 com o mesmo peso. Ele serve para localização no roteiro, não como estimativa de esforço ou prazo. A Etapa 12 é transversal e acontece durante todo o desenvolvimento.

Neste momento, o app permite criar contas, manter os dois tipos de perfil, configurar um perfil profissional e encontrar profissionais por categoria e distância aproximada. O próximo marco transforma essa base pesquisável no fluxo central do marketplace: publicar um chamado, receber interesses, selecionar profissionais e expirar a janela automaticamente.

## Status por etapa

| Etapa | Entrega | Status | Progresso verificável |
|---:|---|---|---|
| 0 | Fundação do projeto | ✅ Concluída | API Go, SvelteKit, PostGIS, Redis, Asynq, Traefik, CI e Docker Compose funcionando. |
| 1 | Identidade e perfis | ✅ Concluída | Cadastro, confirmação de e-mail, login, refresh, recuperação de senha e perfis coexistentes. |
| 2 | Categorias, região e disponibilidade | ✅ Concluída | Catálogo, perfil profissional, agenda, portfólio e busca geoespacial sem exposição de coordenadas. |
| 3 | Chamados e janela de interesse | ⏭️ Próxima | Ainda não iniciada. É o próximo foco de implementação. |
| 4 | Conversa entre as partes | ⬜ Pendente | Chat WebSocket, Redis Pub/Sub, reconexão, bloqueio e limite contra spam. |
| 5 | Notificações em camadas | ⬜ Pendente | Web Push, e-mail, consentimentos e definição do fallback WhatsApp/SMS. |
| 6 | PWA instalável | ⬜ Pendente | Manifest, service worker, cache offline e orientação de instalação no iOS. |
| 7 | Confirmação e avaliação bilateral | ⬜ Pendente | Confirmação pós-serviço, avaliações legítimas, proteção contra retaliação e contestação. |
| 8 | Favoritos e recontratação | ⬜ Pendente | Salvar profissionais e reutilizar dados em um novo chamado. |
| 9 | Moderação e verificação | ⬜ Pendente | Denúncia, bloqueio, análise, recurso, verificações reais e painel administrativo. |
| 10 | Premium e boosts | ⬜ Pendente | Assinatura do software, cancelamento e promoções transparentes sem substituir relevância. |
| 11 | Produção e observabilidade | ⬜ Pendente | TLS, backups testados, métricas, dashboards, hardening e feature flags. |
| 12 | Qualidade contínua | 🔄 Em andamento | Testes, lint, detector de corrida, contrato OpenAPI e validações acompanham cada etapa. |

## Entregas já disponíveis

### Fundação

- monólito modular em Go 1.23 com `chi` e SQL tipado por `sqlc`;
- PostgreSQL 16 com PostGIS e migrações versionadas;
- Redis e worker Asynq;
- frontend SvelteKit/TypeScript mobile first;
- ambiente completo em Docker Compose com Traefik;
- respostas de erro padronizadas, logs estruturados e auditoria transversal.

### Conta e autenticação

- cadastro e confirmação de e-mail;
- login com JWT curto e refresh token rotativo em cookie `HttpOnly`;
- logout e recuperação de senha;
- conta única com perfis profissional e contratante simultâneos;
- autorização por perfil validada no servidor.

### Descoberta de profissionais

- catálogo inicial com categorias permitidas pelas decisões de produto;
- bio, habilidades, região, raio de atuação e preço de referência opcional;
- disponibilidade semanal e opção “Disponível agora”;
- portfólio básico em JPEG/PNG;
- busca paginada com `ST_DWithin` e `ST_Distance`;
- respostas públicas somente com região e distância aproximada, nunca coordenadas exatas.

## Próximo marco — Etapa 3

O próximo incremento deve entregar o seguinte fluxo ponta a ponta:

```text
Contratante publica chamado
          ↓
Profissionais compatíveis demonstram interesse
          ↓
Contratante analisa e seleciona um ou mais profissionais
          ↓
Posições são preenchidas ou a janela expira automaticamente
```

Entregas previstas:

- chamados com estados `draft`, `open`, `partially_filled`, `filled`, `expired`, `cancelled` e `completed`;
- interesses com estados `applied`, `shortlisted`, `selected`, `not_selected`, `withdrawn` e `expired`;
- janelas fixas de 2 horas, 5 horas, 24 horas e 3 dias;
- validação para que a janela nunca ultrapasse o início do serviço;
- publicação e acompanhamento mobile first;
- listagem paginada de chamados compatíveis e interessados;
- seleção atômica para impedir preenchimento além da quantidade solicitada;
- expiração persistente por job Asynq;
- proteção contra chamados duplicados e spam;
- auditoria de publicação, interesse, retirada, seleção, cancelamento e expiração;
- testes de transição de estado, concorrência e reinício do worker.

## Decisões que serão necessárias mais adiante

Algumas etapas dependem de validação de produto ou operação e não devem ser decididas silenciosamente:

- prazo máximo aceitável para entrega de notificações em chamados com janela de 2 horas;
- provedor para fallback por WhatsApp ou SMS;
- regra anti-retaliação das avaliações;
- processo e fornecedor de verificação de identidade;
- preços, limites e benefícios dos planos Premium;
- critérios exatos de boost sem prejudicar a relevância orgânica;
- revisão jurídica dos termos, privacidade, avaliações e categorias antes do lançamento.

## Critério para atualizar este arquivo

Uma etapa só deve ser marcada como concluída quando seu fluxo funciona ponta a ponta, permissões e privacidade foram verificadas, testes proporcionais ao risco passaram e a documentação foi atualizada. Trabalho iniciado, mas ainda não validado, deve aparecer como “Em andamento”, nunca como concluído.

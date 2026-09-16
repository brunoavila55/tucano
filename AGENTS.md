# AGENTS.md — Marketplace de profissionais sob demanda

## Objetivo deste arquivo

Este documento é a fonte de contexto para qualquer agente de IA ou pessoa que trabalhe neste repositório. Antes de propor, implementar ou revisar uma mudança, entenda as decisões de produto abaixo e preserve-as, salvo quando houver uma solicitação explícita para alterá-las.

## Visão do produto

O app é um marketplace para encontrar e contatar profissionais autônomos disponíveis para serviços pontuais.

A proposta central é:

> Preciso de alguém para fazer um serviço, em determinado lugar e momento. Quero encontrar rapidamente profissionais compatíveis e falar diretamente com eles.

O produto combina descoberta local, disponibilidade, reputação e contato. A referência informal pode ser “Tinder de serviços”, mas o valor não está no gesto de deslizar cards. O valor está em reduzir o tempo entre a necessidade e o contato com um profissional adequado.

Exemplos de uso:

- uma cafeteria procura um barista para sábado;
- um evento precisa de garçons ou bartenders;
- uma empresa procura fotógrafo, videomaker ou DJ;
- um pequeno negócio procura designer ou social media;
- um contratante encontra um profissional e volta a chamá-lo depois.

## Posicionamento

O app não é uma agência de empregos, empresa de trabalho temporário ou empregador dos profissionais. É uma plataforma de divulgação, busca, compatibilidade e comunicação entre contratantes e prestadores independentes.

Evite descrever o produto como fornecedor de mão de obra. Prefira expressões como:

- profissionais autônomos;
- serviços;
- oportunidades;
- pedidos;
- chamados;
- demonstrar interesse;
- entrar em contato.

Evite usar “vaga”, “candidato”, “funcionário”, “salário”, “escala” ou “contratado pela plataforma” quando o contexto for um serviço autônomo.

Uma frase de posicionamento possível é:

> Profissionais disponíveis quando você precisa.

## Decisões de produto já tomadas

Estas são decisões atuais, não perguntas em aberto:

1. O MVP não processa o pagamento do serviço.
2. Contratante e profissional combinam diretamente valor, forma de pagamento, nota fiscal e demais condições.
3. A plataforma não cobra comissão sobre o valor do serviço.
4. A monetização inicial é freemium, com planos Premium opcionais.
5. O Premium pode aumentar a exposição, mas não pode substituir relevância por dinheiro nem comprometer a confiança na busca.
6. Resultados patrocinados ou impulsionados devem ser identificados claramente.
7. A plataforma deve permitir avaliação bilateral: o contratante avalia o profissional e o profissional avalia o contratante.
8. O profissional controla sua disponibilidade e pode aceitar, ignorar ou recusar qualquer oportunidade sem punição por isso.
9. O MVP é um marketplace nacional e geral de serviços autônomos, sem recorte por cidade nem por segmento; o pareamento local acontece via geolocalização (região e distância aproximada), não por restrição de cadastro a uma cidade ou nicho.
10. Todo chamado publicado tem uma janela de interesse, escolhida pelo contratante entre opções fixas (2 horas, 5 horas, 24 horas, 3 dias), durante a qual profissionais compatíveis podem se manifestar. O contratante pode escolher alguém e encerrar o chamado antes do fim da janela, a qualquer momento.

## Público do MVP

### Profissional

Pessoa autônoma que oferece serviços pontuais e quer:

- criar um perfil confiável;
- mostrar experiência e portfólio;
- informar localização aproximada e disponibilidade;
- receber oportunidades compatíveis;
- conversar com contratantes;
- construir reputação;
- ser chamada novamente por bons clientes.

### Contratante

Pessoa ou empresa que precisa encontrar profissionais com rapidez e quer:

- publicar um chamado em poucos segundos;
- buscar por categoria, região e disponibilidade;
- comparar perfis, portfólios e avaliações;
- falar diretamente com os profissionais;
- salvar favoritos;
- repetir uma contratação anterior.

## Foco inicial recomendado

O produto é um marketplace geral de serviços autônomos, sem recorte por segmento nem por cidade — o alcance é nacional desde o início, e o pareamento local acontece via geolocalização (região do profissional, distância aproximada na busca), não por restrição de cadastro a uma cidade específica.

Categorias não seguem uma lista fechada por segmento: contratantes e profissionais podem cobrir qualquer serviço autônomo pontual, dentro dos limites abaixo.

Não incluir no MVP:

- saúde e medicina clínica (procedimentos que exigem licença de profissional de saúde);
- advocacia — o Código de Ética da OAB restringe publicidade e captação de clientela de forma incompatível com exposição competitiva entre profissionais, preço público e avaliação aberta;
- segurança privada prestada por pessoa física autônoma — a Lei 7.102/1983 exige prestação por empresa licenciada pela Polícia Federal, não por autônomo individual;
- consultoria de investimento e produtos financeiros regulados (CVM/BACEN).

Podem ser incluídas desde o início, mesmo sendo profissões com conselho de classe, desde que sigam as mesmas regras de autonomia e ausência de intermediação financeira do restante da plataforma:

- estética e beleza (limpeza de pele, sobrancelha, manicure, cabelo, maquiagem);
- engenharia e arquitetura;
- contabilidade;
- e demais categorias de eventos, gastronomia, casa, manutenção, projetos pontuais etc., conforme demanda validada com usuários.

Esta lista de exclusões/inclusões é uma decisão de produto, não parecer jurídico — deve ser revisada por profissionais jurídicos no Brasil antes do lançamento (ver "Limites jurídicos e operacionais").

## Fluxos essenciais

### Publicar um chamado

O contratante informa:

- categoria do serviço;
- data e horário (ou período estimado, quando for um projeto sem data fixa);
- região ou endereço aproximado;
- quantidade de profissionais;
- descrição objetiva;
- valor ou faixa sugerida, quando desejar;
- requisitos relevantes;
- janela de interesse: por quanto tempo o chamado fica aberto para manifestações, escolhida entre opções fixas (2 horas, 5 horas, 24 horas, 3 dias).

Publicar deve levar menos de 30 segundos sempre que possível.

### Janela de interesse e seleção

Todo chamado publicado abre uma janela de tempo — não existe um fluxo separado de "chamado urgente"; a urgência é apenas o reflexo de o contratante escolher uma janela curta (2 horas) para uma necessidade de curto prazo, usando a mesma mecânica de qualquer outro chamado.

Exemplo de janela curta:

> Preciso de um garçom hoje, das 19h às 23h, na região central — janela de interesse de 2 horas.

Durante a janela, profissionais compatíveis e disponíveis recebem a oportunidade e podem demonstrar interesse. Essa manifestação deve ser leve: confirmar disponibilidade, aceitar o valor proposto ou informar sua condição e enviar uma mensagem curta opcional. Não exigir carta de apresentação.

O contratante acompanha os interessados e pode:

- abrir o perfil e as avaliações;
- conversar para esclarecer detalhes;
- selecionar um ou mais profissionais, conforme a quantidade solicitada;
- encerrar o chamado manualmente a qualquer momento, antes do fim da janela escolhida;
- cancelar o chamado com motivo;
- deixar a janela expirar sem escolher ninguém;
- prorrogar ou republicar quando ainda houver tempo útil antes do serviço.

Selecionar um profissional encerra imediatamente aquela posição, sem esperar o fim da janela. Se houver várias posições, o chamado permanece aberto apenas para as posições restantes. A seleção representa a escolha de um prestador para contato e combinação direta; não cria pagamento dentro do app nem vínculo com a plataforma.

Todos os envolvidos devem receber uma resposta clara:

- selecionado: confirmação, próximos passos e abertura da conversa;
- não selecionado: aviso respeitoso sem expor quem foi escolhido;
- expirado: aviso de que o prazo terminou sem seleção;
- cancelado: aviso e motivo, quando apropriado.

Estados mínimos do chamado:

1. `draft`: ainda não publicado;
2. `open`: recebendo interessados;
3. `partially_filled`: parte das posições foi preenchida;
4. `filled`: todas as posições foram preenchidas;
5. `expired`: prazo encerrado sem preenchimento completo;
6. `cancelled`: cancelado pelo contratante ou pela moderação;
7. `completed`: serviço posteriormente confirmado como realizado.

Estados mínimos do interesse:

1. `applied`: interesse enviado;
2. `shortlisted`: contratante está considerando o perfil;
3. `selected`: profissional escolhido;
4. `not_selected`: outro profissional foi escolhido ou a posição acabou;
5. `withdrawn`: profissional retirou o interesse antes da seleção;
6. `expired`: chamado terminou sem decisão para aquele interesse.

Regras importantes:

- a janela de interesse nunca pode ultrapassar o início do serviço; perto demais do horário de início, o sistema deve sugerir uma opção de janela mais curta;
- o contratante pode selecionar antes do fim da janela, sem ser obrigado a esperar o prazo completo;
- o sistema não escolhe automaticamente um profissional no MVP;
- o Premium não pode esconder nem rebaixar injustamente interessados gratuitos compatíveis;
- a ordem dos interessados deve considerar compatibilidade e confiança, identificando qualquer destaque pago;
- limitar notificações repetidas e chamados duplicados para evitar spam;
- cancelamentos, ausência de resposta e no-show devem alimentar reputação e mecanismos de segurança, com direito a contestação;
- o app deve registrar publicação, manifestação de interesse, seleção, retirada, expiração e cancelamento para auditoria e resolução de conflitos.

### Encontrar profissionais

O sistema mostra profissionais compatíveis com o chamado. O ranking orgânico deve priorizar:

1. compatibilidade de categoria e habilidades;
2. disponibilidade;
3. distância ou região atendida;
4. reputação e confiabilidade;
5. tempo de resposta;
6. experiência relevante;
7. completude e qualidade do perfil.

Um boost Premium pode aumentar a exposição apenas entre resultados que já sejam relevantes. Ele nunca deve transformar um perfil incompatível em melhor resultado. Toda promoção deve aparecer com rótulo como “Destaque” ou “Patrocinado”.

### Demonstrar interesse e conversar

O profissional pode demonstrar interesse em um chamado. O contratante pode abrir o perfil e iniciar conversa. O app facilita o contato, mas não fecha nem liquida financeiramente o serviço.

### Confirmar realização e avaliar

Após a data prevista, o app pergunta separadamente às partes se o serviço ocorreu. Somente interações legítimas devem gerar avaliações. A avaliação deve ser bilateral e ter mecanismos contra retaliação, fraude e abuso.

### Contratar novamente

O contratante pode salvar o profissional como favorito e reutilizar seus dados em um novo contato ou chamado. Recorrência é parte central do valor do produto.

## Experiência do profissional

O perfil deve ser simples, confiável e orientado à decisão, não um currículo longo. Pode conter:

- nome e foto;
- categoria principal e habilidades;
- biografia curta;
- região atendida e distância aproximada;
- preço de referência opcional;
- disponibilidade;
- fotos ou vídeos de portfólio;
- avaliações;
- quantidade de serviços confirmados;
- tempo médio de resposta;
- verificações reais de identidade ou documentos;
- botão “Disponível agora”, quando aplicável.

Nunca venda um selo de verificação. Verificação precisa representar uma checagem real e ter significado claro.

## Modelo freemium

### Profissional gratuito

- perfil público funcional;
- uma categoria principal;
- portfólio básico;
- disponibilidade básica;
- recebimento de contatos;
- avaliações;
- acesso suficiente para conseguir serviços de verdade.

### Profissional Premium

Possíveis benefícios:

- boost transparente em resultados relevantes;
- perfil destacado;
- mais itens no portfólio;
- vídeos;
- categorias adicionais;
- agenda avançada;
- respostas rápidas ou automáticas;
- métricas de visualização, clique e contato;
- link personalizado;
- raio de atuação ampliado.

### Contratante gratuito

- publicar uma quantidade limitada de chamados;
- buscar profissionais;
- conversar;
- salvar favoritos;
- avaliar serviços confirmados.

### Contratante Premium

Possíveis benefícios:

- mais chamados ou chamados ilimitados;
- filtros avançados;
- múltiplos usuários da empresa;
- listas privadas de profissionais favoritos;
- histórico e contratação recorrente;
- banco próprio de profissionais;
- métricas e relatórios;
- ferramentas para contatar vários favoritos com consentimento e sem spam.

Preços, limites e benefícios definitivos devem ser tratados como hipóteses e validados com usuários antes de serem fixados no código.

## Limites jurídicos e operacionais

O desenho do produto deve preservar autonomia real do profissional. Não basta declarar autonomia nos Termos de Uso.

### A plataforma não deve

- exigir jornada mínima;
- obrigar o profissional a ficar online;
- punir a recusa de oportunidades;
- exigir exclusividade;
- determinar unilateralmente como o serviço será executado;
- chamar o profissional de funcionário ou integrante da equipe da plataforma;
- receber e repassar o valor do serviço no MVP;
- prometer que o serviço será executado pela própria plataforma;
- vender acesso a emprego ou cobrar para que alguém se candidate a uma vaga empregatícia;
- expor localização exata antes que isso seja necessário e consentido;
- permitir avaliações de quem não teve uma interação confirmada.

### A plataforma pode

- definir regras de convivência, segurança e uso;
- moderar fraude, assédio e conteúdo ilegal;
- verificar identidade e documentos com consentimento e finalidade clara;
- recomendar oportunidades compatíveis;
- ordenar resultados por relevância e confiança;
- vender recursos opcionais de software e divulgação;
- suspender contas por fraude, risco ou violação das regras, com processo transparente de contestação.

Antes do lançamento, termos do profissional, termos do contratante, política de privacidade, política de avaliações e regras do Premium devem ser revisados por profissionais jurídicos no Brasil. Este arquivo orienta produto e engenharia; não substitui parecer jurídico.

## Privacidade e segurança

Aplicar minimização de dados desde o início:

- mostrar distância ou região, não a posição exata do profissional;
- revelar endereço exato apenas quando necessário para o serviço;
- coletar somente dados necessários para a funcionalidade atual;
- proteger CPF, CNPJ, telefone, documentos e dados de localização;
- separar dados públicos de dados privados;
- registrar consentimentos e aceites relevantes;
- oferecer correção e exclusão de dados nos limites legais;
- definir retenção e descarte de dados;
- manter trilhas de auditoria para moderação e segurança;
- limitar acesso interno por função;
- nunca registrar segredos, tokens ou documentos pessoais em logs.

Biometria não deve ser implementada no MVP sem necessidade comprovada, fornecedor adequado e revisão jurídica e de segurança.

## Entidades conceituais

Os nomes podem mudar conforme a stack, mas o domínio deve prever:

- `User`: identidade e autenticação;
- `ProfessionalProfile`: apresentação, categorias, região e configurações do profissional;
- `ClientProfile`: pessoa ou empresa contratante;
- `ServiceCategory`: categoria e requisitos próprios;
- `Availability`: períodos e estado de disponibilidade;
- `ServiceRequest`: chamado publicado pelo contratante, quantidade de posições, prazo de candidatura e estado de preenchimento;
- `Interest`: manifestação de interesse do profissional, condições informadas, estado e horário de envio;
- `Conversation`: comunicação entre as partes;
- `Favorite`: profissional salvo por um contratante;
- `ServiceConfirmation`: confirmação de que uma interação ocorreu;
- `Review`: avaliação bilateral vinculada a uma interação legítima;
- `Verification`: checagens realizadas e seus estados;
- `Subscription`: plano e status de cobrança pelo software;
- `Boost`: promoção identificada, com início, fim e critérios;
- `ModerationCase`: denúncia, análise, decisão e recurso;
- `AuditEvent`: eventos sensíveis relevantes para segurança e conformidade.

Não modele pagamento do serviço como responsabilidade da plataforma no MVP. A cobrança de assinatura Premium é uma transação separada do valor combinado entre contratante e profissional.

## Requisitos funcionais mínimos

O primeiro produto utilizável deve permitir:

- cadastro e autenticação;
- escolha entre perfil profissional e contratante, permitindo ambos quando necessário;
- criação e edição de perfil;
- seleção de categoria e região atendida;
- gestão de disponibilidade;
- publicação, edição, encerramento e expiração de chamado;
- chamado urgente com janela padrão de duas horas e encerramento antecipado;
- busca e filtros essenciais;
- ranking por compatibilidade;
- demonstração de interesse;
- escolha de um ou mais profissionais e atualização das posições restantes;
- notificações de seleção, não seleção, expiração e cancelamento;
- conversa com proteção contra spam;
- favoritos;
- confirmação pós-serviço;
- avaliação bilateral;
- denúncia e bloqueio;
- moderação administrativa;
- assinatura e cancelamento do Premium;
- identificação clara de boosts;
- controles básicos de privacidade e exclusão de conta.

## Fora do escopo inicial

- carteira digital;
- split de pagamento;
- comissão por serviço;
- garantia financeira ou reembolso do serviço;
- folha de pagamento;
- gestão de jornada ou escala de funcionários;
- contratação trabalhista;
- cobertura nacional desde o lançamento;
- todas as categorias profissionais;
- algoritmo de IA complexo antes de haver dados suficientes;
- gamificação que pressione profissionais a aceitar chamados;
- penalidade automática por recusa de oportunidades.

## Princípios de UX

- Mobile first.
- Clareza vence esperteza.
- Publicar um chamado deve ser rápido.
- Aceitar, recusar ou ignorar deve ser fácil.
- Disponibilidade deve estar visível e sob controle do profissional.
- Distância deve ser aproximada até existir motivo para compartilhar o endereço.
- Promoção paga nunca pode parecer recomendação orgânica.
- A interface deve explicar por que um resultado é compatível.
- A reputação deve ser compreensível e difícil de manipular.
- Fluxos críticos devem incluir estados vazios, carregamento, erro, bloqueio e recuperação.
- Acessibilidade não é acabamento; é requisito.

## Princípios de engenharia

Enquanto a stack não estiver definida:

- não introduza frameworks ou serviços externos sem necessidade clara;
- prefira um monólito modular no MVP;
- mantenha regras de domínio separadas da interface;
- trate permissões no servidor, não apenas no cliente;
- valide e sanitize toda entrada;
- use migrações versionadas para banco de dados;
- mantenha segredos fora do repositório;
- crie logs estruturados sem dados pessoais desnecessários;
- torne operações sensíveis auditáveis;
- proteja autenticação, upload, chat, assinatura e painel administrativo;
- implemente paginação e limites desde cedo em busca, chat e avaliações;
- use feature flags para experimentos de ranking e Premium;
- escreva testes para regras de permissão, ranking, avaliações, boosts e estados de assinatura.

Não adicione dependência, abstração ou microserviço “para o futuro” sem uma necessidade concreta do MVP.

## Métricas do produto

Não otimize apenas cadastros. As métricas mais úteis são:

- tempo entre publicação e primeiro contato relevante;
- porcentagem de chamados com pelo menos um profissional compatível;
- taxa de resposta;
- taxa de confirmação de serviço realizado;
- contratação ou contato recorrente;
- retenção por cidade e categoria;
- denúncias, bloqueios e avaliações contestadas;
- conversão e cancelamento do Premium;
- diferença de resultado entre perfis gratuitos e Premium sem destruir a experiência gratuita.

O objetivo principal do marketplace é liquidez local: uma necessidade válida deve encontrar oferta relevante em tempo útil.

## Como trabalhar neste repositório

Antes de implementar qualquer tarefa:

1. leia este arquivo por completo;
2. inspecione a estrutura e os padrões já existentes;
3. identifique qual fluxo do produto será afetado;
4. verifique privacidade, autonomia do profissional e transparência do Premium;
5. faça a menor mudança coerente que resolva o problema;
6. cubra caminhos felizes, erros e abuso previsível;
7. execute os testes e verificações relevantes;
8. documente decisões novas que alterem o domínio ou o escopo.

Ao encontrar ambiguidade relevante, não invente silenciosamente. Registre a hipótese ou peça uma decisão, principalmente quando envolver:

- stack técnica;
- cidade e categorias de lançamento;
- limites e preço dos planos;
- regras de ranking;
- compartilhamento de localização e contato;
- verificação de identidade;
- moderação;
- termos jurídicos;
- inclusão de pagamentos do serviço.

## Critério de qualidade

Uma funcionalidade só está pronta quando:

- resolve o caso de uso sem contrariar as decisões deste documento;
- funciona em telas móveis;
- contempla permissões e privacidade;
- tem mensagens e estados de erro úteis;
- não confunde promoção paga com relevância orgânica;
- não cria controle indevido sobre o profissional;
- possui testes proporcionais ao risco;
- não expõe dados sensíveis em interface, logs ou respostas de API;
- tem documentação atualizada quando muda uma regra do produto.

## Resumo em uma linha

Estamos construindo um marketplace nacional e freemium, com busca por proximidade, que aproxima contratantes de profissionais autônomos disponíveis, sem intermediar o pagamento do serviço e sem controlar a forma de trabalho.

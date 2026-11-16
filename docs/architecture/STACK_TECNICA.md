VISÃO GERAL

O AstroKatu é um sistema experimental de acompanhamento da saúde e do bem-estar de astronautas, projetado para funcionar de maneira autônoma durante missões espaciais de longa duração. A arquitetura proposta utiliza processamento local para análise de dados, permitindo que o sistema continue funcionando mesmo na ausência de comunicação com a Terra. O projeto adota uma arquitetura híbrida, combinando processamento local e sincronização eventual com sistemas terrestres.

ARQUITETURA PROPOSTA

A arquitetura é organizada em cinco camadas principais: Coleta de dados; Processamento e armazenamento local; Inferência de inteligência artificial; Interface de interação com o astronauta; Comunicação e sincronização com a Terra.

FLUXO DE DADOS

Sensores e Wearables -- > Coleta de dados --> Processamento local --> Armazenamento local, e Análise e inferência de IA --> Análise e inferência de IA --> Identificação de padrões --> Interface do AstroKatu --> Recomendações e acompanhamento --> Sincronização com a Terra (quando disponível)

TECNOLOGIAS PROPOSTAS

| Componente | Tecnologia | Finalidade |
|---|---|---|
| Linguagem principal | Python | Desenvolvimento do protótipo |
| Runtime de IA | Ollama | Execução local de modelos |
| Modelo de linguagem | Gemma 3 1B | Interação textual |
| API local | FastAPI | Comunicação entre componentes |
| Armazenamento | SQLite | Persistência local |
| Formato de dados | JSON | Representação de dados |
| Versionamento | Git | Controle de versões |
| Hospedagem | GitHub | Colaboração |

As tecnologias acima representam a stack proposta para o protótipo.

INTELIGÊNCIA ARTIFICIAL

Modelo de linguagem -- O protótipo utiliza o modelo Gemma 3 1B executado localmente por meio do Ollama. O modelo foi escolhido inicialmente por permitir experimentação com inferência local e por apresentar requisitos computacionais menores que modelos de maior porte.

Funções previstas -- Interpretar relatos textuais do astronauta; Auxiliar na interação com o companheiro virtual; Organizar informações em respostas estruturadas; Apoiar a identificação de padrões comportamentais; Produzir respostas contextualizadas a partir de informações fornecidas pelo sistema; O modelo de linguagem não deverá ser considerado um sistema de diagnóstico médico; A identificação de alterações relevantes deverá considerar critérios previamente definidos e validados, com supervisão especializada quando aplicável.

Inferência local -- O Ollama disponibiliza uma API local que permite que aplicações enviem solicitações ao modelo executado no computador.A inferência local permite que o sistema utilize o modelo sem depender de uma API externa durante o processamento por enquanto.

COLETA DE DADOS

O AstroKatu prevê a utilização de três categorias principais de informações: dados fisiológicos, dados ambientais e autorrelatos do astronauta.

DADOS FISIOLÓGICOS

Os dados fisiológicos poderão ser obtidos por meio de sensores e dispositivos vestíveis, permitindo o acompanhamento de indicadores relacionados à saúde e à adaptação do astronauta ao ambiente espacial.

| Variável | Finalidade |
|---|---|
| Frequência cardíaca | Acompanhamento cardiovascular |
| Variabilidade da frequência cardíaca | Análise de variações cardiovasculares |
| Saturação de oxigênio | Monitoramento da oxigenação |
| Qualidade do sono | Acompanhamento do descanso |
| Duração do sono | Análise da regularidade do sono |
| Temperatura corporal | Acompanhamento fisiológico |
| Atividade física | Monitoramento da movimentação |
| Condutância da pele | Indicador fisiológico associado à ativação autonômica |

A disponibilidade e a precisão dessas medidas dependerão dos sensores utilizados e de sua compatibilidade com o ambiente de missão.

DADOS AMBIENTAIS

O sistema poderá utilizar informações ambientais para contextualizar alterações fisiológicas e comportamentais. Entre as variáveis consideradas estão concentração de CO₂, nível de ruído e condições ambientais da nave. Essas informações poderão contribuir para a análise de fatores que influenciam o sono, o estresse e o bem-estar da tripulação.

AUTORRELATOS

O astronauta poderá registrar informações por meio de conversas com o companheiro virtual, questionários estruturados e relatos sobre humor, fadiga, sono e percepção de estresse. Os autorrelatos complementam os dados fisiológicos e ambientais, permitindo que o sistema considere a percepção individual do astronauta em suas análises.

PROCESSAMENTO E ARMAZENAMENTO

O processamento será realizado localmente sempre que possível, reduzindo a dependência de comunicação externa. Os dados poderão ser organizados e armazenados utilizando SQLite, enquanto JSON poderá ser utilizado para representar informações estruturadas e facilitar a comunicação entre componentes. O armazenamento poderá incluir séries temporais de medidas, indicadores derivados, histórico de acompanhamento e resultados de análises. A estrutura definitiva deverá considerar minimização de dados, controle de acesso e proteção das informações pessoais.

API E INTEGRAÇÃO

A API local poderá ser desenvolvida utilizando FastAPI, permitindo que a interface do AstroKatu e outros componentes enviem solicitações ao sistema de inteligência artificial. A API será responsável por receber entradas, encaminhar solicitações ao modelo local e retornar respostas estruturadas. A integração com sensores poderá utilizar interfaces e protocolos compatíveis com os dispositivos selecionados. A escolha definitiva dependerá das especificações dos sensores e dos requisitos de aquisição de dados.

COMUNICAÇÃO COM A TERRA

A comunicação com sistemas terrestres será realizada de maneira eventual, conforme a disponibilidade do enlace. A arquitetura prevê funcionamento local independente, armazenamento temporário de informações e sincronização quando houver conexão. A transmissão deverá priorizar informações necessárias para acompanhamento e análise, evitando o envio indiscriminado de dados pessoais.

PRIVACIDADE E SEGURANÇA

O AstroKatu prevê processamento local de informações sensíveis, minimização da coleta de dados, controle de acesso, proteção do armazenamento e comunicação criptografada. Relatos textuais poderão ser processados localmente e descartados após a inferência, conforme a política de privacidade definida para o sistema. A implementação deverá considerar proteção de dados em repouso e em trânsito, autenticação e mecanismos de recuperação em caso de falhas.

ESTADO ATUAL

| Componente | Situação |
|---|---|
| Ollama | Instalado e testado |
| Gemma 3 1B | Executado localmente |
| Inferência online | Testada |
| Inferência offline | Testada |
| API FastAPI | Proposta |
| Banco SQLite | Proposto |
| Integração com sensores | Em planejamento |
| Interface do companheiro virtual | Em planejamento |
| Sincronização com a Terra | Em planejamento |

PRÓXIMAS ETAPAS

As próximas etapas incluem implementar uma API de inferência local, definir formatos de entrada e saída do modelo, desenvolver armazenamento estruturado, simular dados fisiológicos e avaliar o comportamento do sistema em cenários experimentais. Também será necessário implementar mecanismos de privacidade, integração com sensores e sincronização de dados, considerando as limitações de comunicação das missões espaciais.


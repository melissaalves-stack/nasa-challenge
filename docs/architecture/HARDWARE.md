## HARDWARE -- ASTROKATU

VISÃO GERAL

O AstroKatu necessita de uma plataforma computacional capaz de executar modelos de inteligência artificial localmente, processar dados fisiológicos e armazenar informações durante missões espaciais de longa duração. A escolha do hardware deve considerar capacidade computacional, memória, consumo energético, dimensões físicas e confiabilidade operacional. Durante o desenvolvimento do protótipo, será utilizado um computador pessoal para experimentação e execução dos modelos. Entretanto, para uma implementação embarcada, serão avaliadas plataformas compactas capazes de realizar inferência local sem depender continuamente da comunicação com a Terra.

REQUISITOS DO SISTEMA

O hardware deverá permitir a execução de modelos de inteligência artificial localmente, processamento de dados fisiológicos, armazenamento de informações e integração com sensores. Também deverá apresentar consumo energético controlado e capacidade de funcionamento independente da conexão com a internet. A escolha definitiva dependerá dos modelos utilizados, da quantidade de dados processados e das funcionalidades implementadas no sistema.

HARDWARE DE REFERÊNCIA -- NVIDIA JETSON ORIN NANO SUPER

O NVIDIA Jetson Orin Nano Super é uma plataforma compacta voltada para aplicações de inteligência artificial embarcada, robótica e processamento local. Possui CPU ARM Cortex-A78AE de seis núcleos, GPU NVIDIA Ampere, 8 GB de memória LPDDR5 e desempenho de inteligência artificial de até 67 TOPS INT8. Seu consumo energético configurável varia entre 7 W e 25 W. A plataforma apresenta capacidade para aplicações de IA embarcada e compatibilidade com ferramentas do ecossistema NVIDIA. Entretanto, possui memória limitada e exige avaliação de consumo energético, gerenciamento térmico e compatibilidade com os modelos utilizados.

No AstroKatu, poderá ser considerada uma alternativa para execução de inferência local, integração com sensores e processamento de dados fisiológicos.

RASPBERRY PI 5 + AI HAT+ 2

O Raspberry Pi 5 combinado com AI HAT+ 2 constitui uma alternativa compacta para desenvolvimento de aplicações embarcadas com aceleração de inteligência artificial. O conjunto utiliza um acelerador Hailo-10H de 40 TOPS INT4 e 8 GB de memória dedicada na AI HAT+ 2. A plataforma permite experimentação com aplicações de IA local e oferece um ecossistema acessível para prototipação. Entretanto, depende de compatibilidade entre os modelos utilizados e o software do acelerador, além de exigir avaliação de consumo energético e condições térmicas.
No AstroKatu, poderá ser utilizado como alternativa para experimentação de processamento embarcado.

COMPARAÇÃO ENTRE PLATAFORMAS

| Característica | Jetson Orin Nano Super | Raspberry Pi 5 + AI HAT+ 2 |
|---|---|---|
| Memória | 8 GB LPDDR5 | 8 GB na AI HAT+ 2 |
| Desempenho de IA | Até 67 TOPS INT8 | 40 TOPS INT4 |
| Processamento | CPU ARM + GPU NVIDIA | CPU ARM + acelerador Hailo |
| Aplicação | IA embarcada e robótica | IA embarcada e prototipação |
| Inferência local | Compatível com ferramentas adequadas | Compatível com modelos suportados |

Os valores de TOPS apresentados utilizam precisões numéricas diferentes, portanto não representam uma comparação direta de desempenho entre os modelos executados.

HARDWARE DE PROTOTIPAÇÃO

Durante o desenvolvimento do AstroKatu, será utilizado um computador pessoal para executar o Ollama, testar modelos de linguagem, simular inferência offline, desenvolver APIs e avaliar o funcionamento do protótipo. Essa abordagem permite realizar experimentos sem adquirir inicialmente hardware adicional. O equipamento utilizado na prototipação não representa necessariamente a configuração definitiva de uma missão espacial.

ARQUITETURA DE HARDWARE PROPOSTA

A arquitetura de hardware prevê a integração de sensores fisiológicos a uma plataforma computacional embarcada. Os dados coletados serão encaminhados para processamento local, armazenamento e inferência de inteligência artificial. O computador embarcado será responsável por executar os componentes de software do AstroKatu e disponibilizar informações ao astronauta por meio da interface do sistema. A comunicação com sistemas terrestres ocorrerá quando houver disponibilidade de conexão.

CONSIDERAÇÕES PARA MISSÕES ESPACIAIS

A utilização de hardware comercial em missões espaciais exige avaliações adicionais relacionadas à resistência à radiação, confiabilidade operacional, gerenciamento térmico, consumo energético, redundância, compatibilidade eletromagnética e segurança dos dados. Os equipamentos apresentados neste documento são plataformas comerciais de desenvolvimento e não devem ser considerados automaticamente adequados para voo espacial. Uma implementação real exigiria seleção e qualificação de componentes apropriados ao ambiente da missão.

CONCLUSÃO

O NVIDIA Jetson Orin Nano Super e o Raspberry Pi 5 com AI HAT+ 2 representam alternativas relevantes para experimentação de inferência local no AstroKatu. Para o protótipo inicial, recomenda-se utilizar o computador pessoal disponível, evitando custos adicionais durante a fase de desenvolvimento. A escolha definitiva de hardware embarcado deverá ocorrer após avaliação dos modelos de inteligência artificial, requisitos de memória, consumo energético e funcionalidades implementadas.
# AstroKatu

**Sistema experimental de acompanhamento da saúde e do bem-estar de astronautas em missões espaciais de longa duração.**

## SOBRE O PROJETO

O AstroKatu é um projeto desenvolvido pela equipe Pindorama no contexto do NASA Space Apps Challenge. A proposta consiste em desenvolver um sistema inteligente capaz de acompanhar indicadores físicos e comportamentais de astronautas, auxiliando na identificação de alterações relevantes durante missões espaciais de longa duração.

Considerando os desafios de isolamento, confinamento, comunicação limitada e ausência de assistência médica imediata, o AstroKatu busca oferecer acompanhamento contínuo e interação personalizada por meio de um companheiro virtual.

## PROBLEMA

Missões espaciais de longa duração, especialmente aquelas destinadas a Marte, apresentam desafios relacionados à saúde física e mental dos astronautas. O isolamento, a distância da Terra, as alterações fisiológicas e os atrasos de comunicação dificultam o acompanhamento contínuo e a assistência imediata.

O AstroKatu busca contribuir para esse cenário por meio de processamento local, acompanhamento individualizado e funcionamento independente da comunicação terrestre.

## SOLUÇÃO PROPOSTA

A solução consiste em um sistema híbrido que combina inteligência artificial local, análise de dados fisiológicos e interação com o astronauta por meio de um companheiro virtual.

O sistema poderá utilizar sensores, dispositivos vestíveis e autorrelatos para acompanhar padrões individuais e identificar possíveis alterações relevantes. A inferência local permite que o AstroKatu continue funcionando mesmo quando não há conexão com a Terra.

Quando houver disponibilidade de comunicação, informações selecionadas poderão ser sincronizadas com sistemas terrestres.

## FUNCIONALIDADES PREVISTAS

- Acompanhamento de indicadores fisiológicos.
- Monitoramento de sono e atividade física.
- Registro de autorrelatos e percepção de bem-estar.
- Identificação de alterações em padrões individuais.
- Interação com um companheiro virtual.
- Processamento local de informações.
- Funcionamento independente da internet.
- Sincronização eventual com sistemas terrestres.
- Recomendações de acompanhamento e bem-estar.

## ARQUITETURA

O AstroKatu adota uma arquitetura híbrida, composta por coleta de dados, processamento local, inferência de inteligência artificial, interface de interação e comunicação com sistemas terrestres.

```text
Sensores e Wearables
        |
        v
Coleta de dados
        |
        v
Processamento local
        |
        v
Inferência de IA
        |
        v
Identificação de padrões
        |
        v
Companheiro virtual
        |
        v
Acompanhamento
        |
        v
Sincronização com a Terra
```

## STACK TECNOLÓGICA

| Componente | Tecnologia |
|---|---|
| Linguagem | Python |
| Runtime de IA | Ollama |
| Modelo de linguagem | Gemma 3 1B |
| API | FastAPI |
| Banco de dados | SQLite |
| Formato de dados | JSON |
| Versionamento | Git |
| Repositório | GitHub |

As tecnologias representam a stack proposta para o protótipo, com execução local do modelo de linguagem já testada.

## TESTES REALIZADOS

Foi realizado um teste experimental utilizando o modelo Gemma 3 1B por meio do Ollama.

| Teste | Resultado |
|---|---|
| Execução com internet | Aprovado |
| Execução sem internet | Aprovado |

Os resultados demonstraram que o modelo pode produzir respostas localmente após o download dos arquivos necessários, sem depender de conexão contínua com a internet.

## ESTRUTURA DO REPOSITÓRIO

```text
AstroKatu-IA/
├── docs/
│   ├── HARDWARE.md
│   ├── STACK_TECNICA.md
│   └── TESTE_INFERENCIA.md
├── ia-local/
│   └── README.md
├── .gitignore
└── README.md
```

## DOCUMENTAÇÃO

| Documento | Descrição |
|---|---|
| [HARDWARE.md](docs/HARDWARE.md) | Análise de hardware para inferência local |
| [STACK_TECNICA.md](docs/STACK_TECNICA.md) | Arquitetura e tecnologias propostas |
| [TESTE_INFERENCIA.md](docs/TESTE_INFERENCIA.md) | Registro dos testes de inferência local |

EQUIPE

**Equipe:** Pindorama

**Projeto:** AstroKatu

Desenvolvido no contexto do NASA Space Apps Challenge.

## LIMITAÇÕES

O AstroKatu é um protótipo experimental. As funcionalidades propostas não representam um sistema médico certificado e não devem ser utilizadas para diagnóstico ou tratamento de condições de saúde.

A utilização em missões espaciais reais exigiria validação clínica, avaliação de segurança, qualificação de hardware e testes em condições apropriadas.
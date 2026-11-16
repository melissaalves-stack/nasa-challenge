# AstroKatu — Dados

Esta pasta descobre quando um astronauta está **saindo do próprio normal** e avisa o que fazer.

Ela compara cada tripulante com ele mesmo, não com uma média geral.
Uma noite ruim sozinha não gera alerta: só tendências que duram alguns dias.

## Como rodar

```bash
pip install -r requirements.txt
python simulate.py           # 1. cria os dados da missão
python report.py --dia 46    # 2. analisa e gera um relatório por tripulante
python evaluate.py           # 3. confere se o sistema acertou
```

Os resultados aparecem na pasta `output/`.

## O que cada arquivo faz

| Arquivo | Função |
| --- | --- |
| `params.yaml` | Configurações: tripulantes, dias, valores dos sinais e regras de alerta |
| `simulate.py` | Cria uma missão de 180 dias com 7 tripulantes e alguns problemas escondidos |
| `features.py` | Lê e confere os dados |
| `baseline.py` | Calcula o "normal" de cada tripulante |
| `detect.py` | Compara o dia com o normal e decide se há alerta |
| `report.py` | Gera o `relatorio_<id>.json` que o back-end usa |
| `evaluate.py` | Mostra se os problemas escondidos foram encontrados |

## O que é medido

- **Recuperação:** sono, eficiência do sono, HRV, frequência cardíaca, oxigenação
- **Cognitivo:** tempo de reação (teste PVT)
- **Bem-estar:** humor, energia e estresse (3 perguntas do bichinho) + atividade física

## Níveis de alerta

| Nível | Cor | O que acontece |
| --- | --- | --- |
| Nenhum | verde | Tudo dentro do normal |
| Leve | amarelo | Sugestão de autocuidado |
| Moderado | amarelo | Recomenda falar com a equipe ou a tripulação |
| Grave | vermelho | Aciona o protocolo combinado antes da missão |

O sistema descreve mudanças ("HRV 38% abaixo do seu normal"). Ele **não faz diagnóstico**.

## Dados reais da NASA

`nasa_osdr.py` baixa os exames de sangue reais da tripulação do **Inspiration4**
(estudo [OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575) do OSDR):
painel metabólico e painéis imune e cardiovascular, antes e depois do voo.

Ele aplica a mesma lógica do AstroKatu: compara o pós-voo de cada tripulante com o **pré-voo dele mesmo**.

```bash
python nasa_osdr.py          # baixa e analisa (precisa de internet)
```

Resultados em `output/nasa/`.

## Observações

- A missão diária da demo é **simulada**. Valores marcados `CALIBRAR` no `params.yaml` ainda precisam de fonte da NASA.
- As regras de alerta são uma proposta inicial e precisam da validação da Isa.

## V1
Preciso alinhar as metricas de saúde para ter certeza do que é correto.
Dados durante a expedição não existem. Portanto, a unica metrica que temos é o exame antes e depois, na terra mesmo, dos astronautas.
simulate.py, na teoria faria essa simulaçao do que seria o durante, usando os parametros usuais de saude que ainda precisam ser ajustados.

report.py da o relatório diario, ele mede o quanto o astronauta está diferente do próprio normal, em três dimensões: recuperação física, cognitivo e bem-estar. A partir disso, decide se há alerta.
O baseline.py quantifica: transforma cada sinal em “quantos desvios longe do normal dele
O detect.py interpreta: junta os sinais em índices, decide o nível e escreve a frase.

## AJUSTES V2
O que foi feito
1. Dados reais da NASA: nasa_osdr.py

O download do OSD-575 funcionou e o formato real dos arquivos está confirmado. A versão anterior lia faixas de referência como se fossem medidas, contava cada citocina duas vezes e gerava z absurdos (z = -919 trilhões). Corrigi as três coisas.
Agora o script lê 99 analitos de 4 tripulantes e informa em que coleta cada valor voltou ao normal e se o resultado saiu da faixa clínica.
Achado para o pitch: a IL-6, marcador de inflamação, sobe em 3 dos 4 tripulantes logo após o voo, com mediana de +59%. A IL-27 também sobe. A maioria das mudanças volta ao normal até o R+45. Isso bate com o que o estudo SOMA publicou sobre o Inspiration4.
2. Detector: detect.py
Resolvi as pendências 1 a 6:

O índice cognitivo não aciona mais "grave" sozinho.
A frase usa a média de 3 dias e valores absolutos. Exemplo do T02 no dia 46: "HRV 25 ms (seu normal: 41 ms) há 3 dias", em vez de "38% abaixo".
O "há X dias" conta só os dias no nível atual.
Existe agora o tipo misto, para corpo e bem-estar piorando juntos.
O alerta tem histerese: só baixa de nível depois de 2 dias bons seguidos.
Em 30 seeds, o desempenho ficou igual ao da versão antiga: 85 de 90 eventos detectados e cerca de 8,5 falsos alarmes por missão. Ganhei clareza sem piorar a detecção.

3. Parâmetros com fonte: params.yaml

Sono: 6,09 h por noite na ISS (Barger 2014).
Eficiência do sono: 88%, de estudos de actigrafia da NASA na ISS.
Frequência cardíaca de repouso: 56 bpm (Otsuka, Holter noturno, cerca de 55 bpm).
4. O atraso do T05 vem da simulação
O evento sobe aos poucos, e na escala de 1 a 5 só fica visível no dia 96. O alerta sai no dia 98, 2 dias depois. Não mexi nos limites.

O que falta
Depende de outras pessoas:

Isa: validar a tabela de ações, que agora inclui as do tipo misto, e responder a uma pergunta: humor baixo sozinho deve chegar a vermelho e acionar o protocolo? Hoje o T05 chega a vermelho nos dias 100 e 101.
Joca: o campo tipo pode vir como "misto", e a explicacao mudou de porcentagem para valor absoluto. Os nomes dos campos não mudaram.
Comigo ou com você:

HRV: o valor de ~42 ms veio de uma fonte secundária. Falta conferir no texto completo de Nunan 2010.
SpO2 e PVT: ainda estão sem fonte de voo.
Gráficos do pitch: o pós-voo real (IL-6) e um tripulante simulado ao longo dos 180 dias. É o próximo passo natural.
Ponte entre dado real e simulação: fazer T01 a T04 partirem do pré-voo real de C001 a C004 e usar a inflamação como sinal semanal.
T07: o evento mais fraco escapa em cerca de 1 a cada 6 missões simuladas. Isso é aceitável, mas vale citar como limitação no pitch.
API FastAPI: só se o Joca pedir.
Quer que eu faça o commit dessas mudanças na Dados-Aredes e siga para os gráficos do pitch?

Fontes consultadas:

Barger et al. 2014 (PMC4188436)
NASA – actigrafia contínua vs. intermitente em missões longas
Otsuka et al. – FC noturna em voo (IAC)
Nunan et al. 2010 e fonte secundária do valor de RMSSD
Basner et al. 2011 – PVT-B
Weill Cornell – resultados do SOMA/Inspiration4
OSD-575
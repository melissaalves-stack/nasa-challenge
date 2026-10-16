Preciso alinhar as metricas de saúde para ter certeza do que é correto.
Dados durante a expedição não existem. Portanto, a unica metrica que temos é o exame antes e depois, na terra mesmo, dos astronautas.
simulate.py, na teoria faria essa simulaçao do que seria o durante, usando os parametros usuais de saude que ainda precisam ser ajustados.

report.py da o relatório diario, ele mede o quanto o astronauta está diferente do próprio normal, em três dimensões: recuperação física, cognitivo e bem-estar. A partir disso, decide se há alerta.
O baseline.py quantifica: transforma cada sinal em “quantos desvios longe do normal dele
O detect.py interpreta: junta os sinais em índices, decide o nível e escreve a frase.
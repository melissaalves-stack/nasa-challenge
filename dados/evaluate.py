"""Compara os alertas com os eventos injetados (o gabarito).

Mede: eventos detectados, dias até o primeiro alerta e falsos alarmes.
Uso:  python evaluate.py   (depois de simulate.py e report.py)
"""
import json
from pathlib import Path

import pandas as pd

TOLERANCIA = 3  # dias depois do fim do evento em que um alerta ainda conta
NIVEL_MIN = 2   # 1 = leve (só sugestão de autocuidado), 2 = moderado: conta como alerta


def episodios(g, nivel_min=NIVEL_MIN):
    """Trechos contínuos de alerta (nivel >= nivel_min) de um tripulante: (inicio, fim)."""
    dias = g.loc[g.nivel >= nivel_min, "dia"].tolist()
    eps, ini = [], None
    for i, d in enumerate(dias):
        if ini is None:
            ini = d
        if i == len(dias) - 1 or dias[i + 1] != d + 1:
            eps.append((ini, d))
            ini = None
    return eps


def main():
    res = pd.read_csv("output/analise_completa.csv")
    eventos = json.loads(Path("output/eventos_injetados.json").read_text(encoding="utf-8"))

    usados = set()
    print("EVENTOS")
    for e in eventos:
        g = res[res.tripulante_id == e["tripulante"]]
        janela = (e["inicio"], e["inicio"] + e["duracao"] - 1 + TOLERANCIA)
        eps = [ep for ep in episodios(g) if ep[0] <= janela[1] and ep[1] >= janela[0]]
        for ep in eps:
            usados.add((e["tripulante"], ep))
        deve_alertar = e["duracao"] >= 3
        if deve_alertar:
            if eps:
                atraso = max(0, eps[0][0] - e["inicio"])
                print(f"  OK   {e['tripulante']} {e['tipo']}: detectado {atraso} dias após o início")
            else:
                print(f"  FALHOU {e['tripulante']} {e['tipo']}: não detectado")
        else:
            status = "OK  " if not eps else "ERRO"
            print(f"  {status} {e['tripulante']} {e['tipo']} (curto): "
                  + ("sem alerta, como esperado" if not eps else "gerou alerta"))

    falsos = [(tid, ep) for tid, g in res.groupby("tripulante_id")
              for ep in episodios(g) if (tid, ep) not in usados]
    dias_missao = res.dia.max() + 1
    leves = sum(len(episodios(g, 1)) for _, g in res.groupby("tripulante_id"))
    print(f"\nSugestões leves de autocuidado (nível 1, não contam como alerta): {leves} episódios")
    print(f"FALSOS ALARMES (nível >= {NIVEL_MIN}): {len(falsos)} em {res.tripulante_id.nunique()} tripulantes "
          f"× {dias_missao} dias")
    for tid, (a, b) in falsos:
        nivel = res[(res.tripulante_id == tid) & res.dia.between(a, b)].nivel.max()
        print(f"  {tid}: dias {a}-{b} (nível máx. {nivel})")


if __name__ == "__main__":
    main()

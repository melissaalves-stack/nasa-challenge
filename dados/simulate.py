"""Gera uma missão simulada do AstroKatu.

Saídas (em output/):
  missao.csv              um registro por tripulante por dia (dia < 0 = pré-voo)
  eventos_injetados.json  o gabarito para a avaliação

Uso:  python simulate.py [--params params.yaml] [--out output]
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

INTEIROS = ["humor", "energia", "estresse"]


def curva_evento(dia, inicio, duracao):
    """Intensidade do evento no dia (0 a 1): sobe no primeiro terço, depois platô."""
    if dia < inicio or dia >= inicio + duracao:
        return 0.0
    if duracao == 1:
        return 1.0
    subida = max(1, duracao // 3)
    return min(1.0, (dia - inicio + 1) / subida)


def simular(params):
    rng = np.random.default_rng(params["seed"])
    sinais = params["sinais"]
    dias = range(-params["dias_pre_voo"], params["dias_missao"])
    ids = [f"T{i:02d}" for i in range(1, params["tripulantes"] + 1)]

    linhas = []
    for tid in ids:
        # cada tripulante sorteia o próprio normal
        normal = {s: rng.normal(cfg["media"], cfg["entre"]) for s, cfg in sinais.items()}
        eventos = [e for e in params["eventos"] if e["tripulante"] == tid]
        ruido_ar = {s: 0.0 for s in sinais}  # ruído autocorrelacionado (dias seguidos parecidos)

        for dia in dias:
            linha = {"tripulante_id": tid, "dia": dia}
            for s, cfg in sinais.items():
                ruido_ar[s] = 0.5 * ruido_ar[s] + rng.normal(0, cfg["diario"]) * np.sqrt(1 - 0.25)
                valor = normal[s] + ruido_ar[s]
                for e in eventos:
                    k = curva_evento(dia, e["inicio"], e["duracao"])
                    valor += k * e["efeito"].get(s, 0.0) * cfg["diario"]
                valor = float(np.clip(valor, cfg["min"], cfg["max"]))
                linha[s] = int(round(valor)) if s in INTEIROS else round(valor, 3)
            linhas.append(linha)

    return pd.DataFrame(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params.yaml")
    ap.add_argument("--out", default="output")
    args = ap.parse_args()

    params = yaml.safe_load(Path(args.params).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(exist_ok=True)

    df = simular(params)
    df.to_csv(out / "missao.csv", index=False)
    (out / "eventos_injetados.json").write_text(
        json.dumps(params["eventos"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"missao.csv: {len(df)} linhas, {df.tripulante_id.nunique()} tripulantes")


if __name__ == "__main__":
    main()

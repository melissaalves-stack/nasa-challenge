"""Roda o pipeline completo e gera um relatorio_<id>.json por tripulante.

Uso:  python report.py [--dia 47]   (padrão: último dia da missão)
Saídas em output/: relatorio_T01.json ... e analise_completa.csv
"""
import argparse
import json
from pathlib import Path

import yaml

import baseline
import detect
import features


def relatorio(g, dia, cfg):
    hist = g[(g.dia >= 0) & (g.dia <= dia)]
    hoje = hist.iloc[-1]
    nivel = int(hoje["nivel"])
    alertas = []
    if nivel > 0:
        tipo = detect.tipo_alerta(hoje, cfg)
        alertas.append({
            "tipo": tipo,
            "gravidade": detect.NIVEL[nivel],
            "dias_persistente": int(hoje["dias_seguidos"]),
            "sinais": detect.sinais_alterados(hoje),
            "explicacao": detect.explicar(hoje),
            "acao_sugerida": detect.ACOES[(tipo, nivel)],
        })
    return {
        "tripulante_id": hoje["tripulante_id"],
        "dia": int(hoje["dia"]),
        "status": detect.STATUS[nivel],
        "indices": {n: round(float(hoje[f"suav_{n}"]), 2) for n in detect.INDICES},
        "alertas": alertas,
        "historico_indices": [
            {"dia": int(r.dia), **{n: round(float(r[f"suav_{n}"]), 2) for n in detect.INDICES},
             "nivel": detect.NIVEL[int(r.nivel)]}
            for _, r in hist.iterrows()
        ],
    }


def rodar(params, entrada="output/missao.csv"):
    cfg = params["deteccao"]
    df = features.carregar(entrada)
    dfz = baseline.calcular(df, janela=cfg["janela_baseline"])
    return detect.detectar(dfz, cfg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params.yaml")
    ap.add_argument("--entrada", default="output/missao.csv")
    ap.add_argument("--dia", type=int, default=None)
    args = ap.parse_args()

    params = yaml.safe_load(Path(args.params).read_text(encoding="utf-8"))
    res = rodar(params, args.entrada)
    out = Path("output")
    res.to_csv(out / "analise_completa.csv", index=False)

    dia = args.dia if args.dia is not None else int(res.dia.max())
    for tid, g in res.groupby("tripulante_id"):
        rel = relatorio(g.sort_values("dia"), dia, params["deteccao"])
        (out / f"relatorio_{tid}.json").write_text(
            json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{tid} dia {dia}: {rel['status']}"
              + (f" — {rel['alertas'][0]['explicacao']}" if rel["alertas"] else ""))


if __name__ == "__main__":
    main()

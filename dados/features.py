"""Carrega e valida os dados diários (físico + diário do bichinho).

O diário entra SÓ como scores 1-5 — o texto nunca chega aqui.
"""
import pandas as pd

from baseline import SINAIS

COLUNAS = ["tripulante_id", "dia", *SINAIS]


def carregar(caminho):
    df = pd.read_csv(caminho)
    faltando = set(COLUNAS) - set(df.columns)
    if faltando:
        raise ValueError(f"colunas faltando em {caminho}: {sorted(faltando)}")

    df = df[COLUNAS].sort_values(["tripulante_id", "dia"]).drop_duplicates(["tripulante_id", "dia"])
    for s in ("humor", "energia", "estresse"):
        if not df[s].between(1, 5).all():
            raise ValueError(f"{s} fora da escala 1-5")

    # dia sem medição: repete o último valor do mesmo tripulante (no máx. 2 dias)
    df[SINAIS] = df.groupby("tripulante_id")[SINAIS].ffill(limit=2)
    return df.dropna(subset=SINAIS).reset_index(drop=True)

"""Baseline pessoal e z-scores orientados (negativo = pior que o normal do tripulante).

O baseline começa com o pré-voo e depois acompanha a missão devagar:
mediana dos dias [t-janela-7, t-7]. O atraso de 7 dias evita que um problema
em andamento "vire o novo normal" antes de ser detectado.
"""
import numpy as np
import pandas as pd

# +1 = maior é melhor, -1 = maior é pior
SENTIDO = {
    "sono_horas": +1, "sono_eficiencia": +1, "hrv_rmssd": +1, "fc_repouso": -1,
    "spo2": +1, "pvt_ms": -1, "atividade_min": +1,
    "humor": +1, "energia": +1, "estresse": -1,
}
SINAIS = list(SENTIDO)
ATRASO = 7


def _mad_sd(x):
    """Desvio-padrão robusto (MAD * 1,4826)."""
    x = np.asarray(x, dtype=float)
    return 1.4826 * np.nanmedian(np.abs(x - np.nanmedian(x)))


def baseline_tripulante(df, janela=21):
    """Recebe os dias de UM tripulante (ordenados) e devolve base_*, sd_* e z_* por sinal."""
    df = df.sort_values("dia").reset_index(drop=True)
    pre = df[df.dia < 0]
    out = df.copy()

    for s in SINAIS:
        sd = max(_mad_sd(pre[s]), pre[s].std())
        # piso: escalas 1-5 e sinais muito estáveis não podem ter sd ~0
        piso = 0.5 if s in ("humor", "energia", "estresse") else 0.05 * abs(pre[s].median())
        sd = max(sd, piso)

        base = np.empty(len(df))
        desv = np.empty(len(df))
        base_pre = pre[s].median()
        for i, dia in enumerate(df.dia):
            if dia < ATRASO:
                base[i], desv[i] = base_pre, sd
            else:
                jan = df[(df.dia >= dia - janela - ATRASO) & (df.dia < dia - ATRASO)][s]
                base[i] = jan.median()
                # desvio robusto (MAD): poucos dias ruins na janela não o inflam;
                # e ele nunca fica menor que o do pré-voo
                desv[i] = max(sd, _mad_sd(jan))

        out[f"base_{s}"] = base
        out[f"sd_{s}"] = desv
        out[f"z_{s}"] = SENTIDO[s] * (df[s] - base) / desv

    return out


def calcular(df, janela=21):
    partes = [baseline_tripulante(g, janela) for _, g in df.groupby("tripulante_id")]
    return pd.concat(partes, ignore_index=True)

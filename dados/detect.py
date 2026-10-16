"""Índices compostos, regra de persistência, gravidade e explicação em frase.

Regras:
  - nenhum dia isolado gera alerta: o nível precisa se manter `dias_persistencia` dias seguidos
  - leve     = algum índice <= z_leve                      -> só sugestão de autocuidado
  - moderado = algum índice <= z_moderado, ou >= min_indices índices <= z_leve
  - grave    = algum índice <= z_grave
"""
import numpy as np
import pandas as pd

INDICES = {
    "recuperacao": ["sono_horas", "sono_eficiencia", "hrv_rmssd", "fc_repouso", "spo2"],
    "cognitivo": ["pvt_ms"],
    "bem_estar": ["humor", "energia", "estresse", "atividade_min"],
}
NIVEL = {0: "nenhum", 1: "leve", 2: "moderado", 3: "grave"}
STATUS = {0: "verde", 1: "amarelo", 2: "amarelo", 3: "vermelho"}

NOMES = {
    "sono_horas": "sono", "sono_eficiencia": "eficiência do sono", "hrv_rmssd": "HRV",
    "fc_repouso": "frequência cardíaca de repouso", "spo2": "oxigenação",
    "pvt_ms": "tempo de reação", "atividade_min": "atividade física",
    "humor": "humor", "energia": "energia", "estresse": "estresse",
}
ESCALA_1_5 = {"humor", "energia", "estresse"}

# Ações por nível e tipo — PROVISÓRIO, a Isa valida o texto final
ACOES = {
    ("fadiga", 1): "Priorizar o sono hoje e repetir o teste de reação amanhã",
    ("fadiga", 2): "Reduzir a carga de trabalho hoje e registrar para a equipe médica",
    ("fadiga", 3): "Protocolo de fadiga: suspender tarefas críticas e contatar a equipe médica",
    ("bem_estar", 1): "Sugerir uma pausa, conteúdo de lazer ou contato com a família",
    ("bem_estar", 2): "Incentivar conversa com a tripulação ou com o apoio psicológico",
    ("bem_estar", 3): "Protocolo combinado antes da missão: avisar a equipe médica em terra",
}


def calcular_indices(dfz):
    out = dfz.copy()
    for nome, sinais in INDICES.items():
        z = out[[f"z_{s}" for s in sinais]]
        # soma / sqrt(n): mantém o índice na mesma escala de um z-score
        out[f"idx_{nome}"] = z.sum(axis=1) / np.sqrt(len(sinais))
    return out


def _nivel_dia(linha, cfg):
    vals = [linha[f"suav_{n}"] for n in INDICES]
    pior = min(vals)
    if pior <= cfg["z_grave"]:
        return 3
    if pior <= cfg["z_moderado"] or sum(v <= cfg["z_leve"] for v in vals) >= cfg["min_indices"]:
        return 2
    return 1 if pior <= cfg["z_leve"] else 0


def aplicar_persistencia(dfi, cfg):
    """Nível do alerta = menor nível dos últimos N dias (todos precisam estar ruins)."""
    partes = []
    for _, g in dfi.groupby("tripulante_id"):
        g = g.sort_values("dia").copy()
        for nome in INDICES:
            g[f"suav_{nome}"] = g[f"idx_{nome}"].rolling(cfg["suavizacao"], min_periods=1).mean()
        g["nivel_dia"] = g.apply(_nivel_dia, axis=1, cfg=cfg)
        n = cfg["dias_persistencia"]
        g["nivel"] = g["nivel_dia"].rolling(n, min_periods=n).min().fillna(0).astype(int)
        g.loc[g.dia < 0, "nivel"] = 0  # pré-voo não gera alerta
        # quantos dias seguidos com nivel_dia > 0
        seq = (g["nivel_dia"] > 0).astype(int)
        g["dias_seguidos"] = seq.groupby((seq == 0).cumsum()).cumsum()
        partes.append(g)
    return pd.concat(partes, ignore_index=True)


def tipo_alerta(linha):
    fis = min(linha["suav_recuperacao"], linha["suav_cognitivo"])
    return "fadiga" if fis < linha["suav_bem_estar"] else "bem_estar"


def explicar(linha, n=3):
    """Frase com os sinais que mais pioraram em relação ao normal do tripulante."""
    zs = {s: linha[f"z_{s}"] for idx in INDICES.values() for s in idx}
    piores = sorted((s for s in zs if zs[s] < -1), key=lambda s: zs[s])[:n]
    partes = []
    for s in piores:
        val, base = linha[s], linha[f"base_{s}"]
        if s in ESCALA_1_5:
            partes.append(f"{NOMES[s]} em {val:.0f}/5 (seu normal: {base:.1f})")
        else:
            pct = abs(val - base) / base * 100
            direcao = "acima" if val > base else "abaixo"
            partes.append(f"{NOMES[s]} {pct:.0f}% {direcao} do seu normal")
    frase = ", ".join(partes)
    return f"{frase} há {int(linha['dias_seguidos'])} dias" if frase else ""


def detectar(dfz, cfg):
    return aplicar_persistencia(calcular_indices(dfz), cfg)

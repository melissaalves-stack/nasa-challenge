"""Índices compostos, regra de persistência, gravidade e explicação em frase.

Regras:
  - nenhum dia isolado gera alerta: o nível precisa se manter `dias_persistencia` dias seguidos
  - leve     = algum índice <= z_leve                      -> só sugestão de autocuidado
  - moderado = algum índice <= z_moderado, ou >= min_indices índices <= z_leve
  - grave    = algum índice <= z_grave
               (índices em `sem_grave_sozinho` só chegam a grave se outro índice confirmar)
  - histerese: para baixar de nível, o dia precisa ficar abaixo do nível atual
               `dias_saida` dias seguidos (o alerta não some no primeiro dia bom)
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
# formato do valor absoluto na frase: (casas decimais, unidade, fator)
UNIDADES = {
    "sono_horas": (1, " h", 1), "sono_eficiencia": (0, "%", 100), "hrv_rmssd": (0, " ms", 1),
    "fc_repouso": (0, " bpm", 1), "spo2": (1, "%", 1), "pvt_ms": (0, " ms", 1),
    "atividade_min": (0, " min", 1),
}
ESCALA_1_5 = {"humor", "energia", "estresse"}
Z_EXPLICAR = -1.0  # sinal entra na frase se a média dos últimos dias estiver abaixo disso

# Ações por nível e tipo — PROVISÓRIO, a Isa valida o texto final
ACOES = {
    ("fadiga", 1): "Priorizar o sono hoje e repetir o teste de reação amanhã",
    ("fadiga", 2): "Reduzir a carga de trabalho hoje e registrar para a equipe médica",
    ("fadiga", 3): "Protocolo de fadiga: suspender tarefas críticas e contatar a equipe médica",
    ("bem_estar", 1): "Sugerir uma pausa, conteúdo de lazer ou contato com a família",
    ("bem_estar", 2): "Incentivar conversa com a tripulação ou com o apoio psicológico",
    ("bem_estar", 3): "Protocolo combinado antes da missão: avisar a equipe médica em terra",
    # misto = corpo e bem-estar piorando juntos (validar com a Isa)
    ("misto", 1): "Sugerir descanso e uma pausa de lazer hoje",
    ("misto", 2): "Reduzir a carga de trabalho e incentivar conversa com a tripulação ou o apoio psicológico",
    ("misto", 3): "Protocolo combinado antes da missão: suspender tarefas críticas e avisar a equipe médica em terra",
}


def calcular_indices(dfz):
    out = dfz.copy()
    for nome, sinais in INDICES.items():
        z = out[[f"z_{s}" for s in sinais]]
        # soma / sqrt(n): mantém o índice na mesma escala de um z-score
        out[f"idx_{nome}"] = z.sum(axis=1) / np.sqrt(len(sinais))
    return out


def _nivel_dia(linha, cfg):
    vals = {n: linha[f"suav_{n}"] for n in INDICES}
    ruins = [n for n, v in vals.items() if v <= cfg["z_leve"]]
    graves = [n for n, v in vals.items() if v <= cfg["z_grave"]]
    # índice com poucos sinais (ex.: cognitivo = só o PVT) não aciona grave sozinho (validar com a Isa)
    if any(n not in cfg.get("sem_grave_sozinho", []) or len(ruins) >= 2 for n in graves):
        return 3
    if min(vals.values()) <= cfg["z_moderado"] or len(ruins) >= cfg["min_indices"]:
        return 2
    return 1 if ruins else 0


def _nivel_com_histerese(nivel_dia, dias, n_entrada, n_saida):
    """Sobe quando os últimos `n_entrada` dias estão todos no nível (persistência).
    Desce só depois de `n_saida` dias seguidos abaixo do nível atual."""
    nivel, atual, abaixo = [], 0, 0
    for i, (nd, dia) in enumerate(zip(nivel_dia, dias)):
        if dia < 0:  # pré-voo não gera alerta
            atual, abaixo = 0, 0
        else:
            entrada = min(nivel_dia[i - n_entrada + 1:i + 1]) if i >= n_entrada - 1 else 0
            if entrada > atual:
                atual, abaixo = entrada, 0
            elif nd < atual:
                abaixo += 1
                if abaixo >= n_saida:
                    atual, abaixo = max(nivel_dia[i - n_saida + 1:i + 1]), 0
            else:
                abaixo = 0
        nivel.append(atual)
    return nivel


def aplicar_persistencia(dfi, cfg):
    partes = []
    n = cfg["suavizacao"]
    for _, g in dfi.groupby("tripulante_id"):
        g = g.sort_values("dia").copy()
        for nome, sinais in INDICES.items():
            g[f"suav_{nome}"] = g[f"idx_{nome}"].rolling(n, min_periods=1).mean()
            for s in sinais:  # z suavizado por sinal: é o que a frase de explicação usa
                g[f"zs_{s}"] = g[f"z_{s}"].rolling(n, min_periods=1).mean()
        g["nivel_dia"] = g.apply(_nivel_dia, axis=1, cfg=cfg)
        g["nivel"] = _nivel_com_histerese(g["nivel_dia"].tolist(), g["dia"].tolist(),
                                          cfg["dias_persistencia"], cfg.get("dias_saida", 1))
        # dias seguidos no nível de alerta ATUAL (não conta os dias leves antes de virar moderado)
        bloco = (g["nivel"] != g["nivel"].shift()).cumsum()
        g["dias_seguidos"] = g.groupby(bloco).cumcount() + 1
        g.loc[g["nivel"] == 0, "dias_seguidos"] = 0
        partes.append(g)
    return pd.concat(partes, ignore_index=True)


def tipo_alerta(linha, cfg):
    fis = min(linha["suav_recuperacao"], linha["suav_cognitivo"])
    bem = linha["suav_bem_estar"]
    if fis <= cfg["z_leve"] and bem <= cfg["z_leve"]:
        return "misto"
    return "fadiga" if fis < bem else "bem_estar"


def sinais_alterados(linha):
    return [s for idx in INDICES.values() for s in idx if linha[f"zs_{s}"] < Z_EXPLICAR]


def _formatar(s, v):
    casas, unidade, fator = UNIDADES[s]
    return f"{v * fator:.{casas}f}".replace(".", ",") + unidade


def explicar(linha, n=3):
    """Frase com os sinais que mais pioraram em relação ao normal do tripulante.
    Usa a média dos últimos dias (z suavizado) e valores absolutos: porcentagem exagera
    quando o normal é baixo (ex.: HRV de 20 ms)."""
    piores = sorted(sinais_alterados(linha), key=lambda s: linha[f"zs_{s}"])[:n]
    partes = []
    for s in piores:
        val, base = linha[s], linha[f"base_{s}"]
        if s in ESCALA_1_5:
            partes.append(f"{NOMES[s]} em {val:.0f}/5 (seu normal: {base:.1f})".replace(".", ","))
        else:
            partes.append(f"{NOMES[s]} {_formatar(s, val)} (seu normal: {_formatar(s, base)})")
    frase = ", ".join(partes)
    dias = int(linha["dias_seguidos"])
    return f"{frase} há {dias} {'dia' if dias == 1 else 'dias'}" if frase else ""


def detectar(dfz, cfg):
    return aplicar_persistencia(calcular_indices(dfz), cfg)

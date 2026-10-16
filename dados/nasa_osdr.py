"""Dados REAIS da NASA: exames de sangue da tripulação do Inspiration4 (OSDR, estudo OSD-575).

O que faz:
  1. baixa do OSDR o painel metabólico (CMP) e os painéis de soro (imune e cardiovascular)
  2. organiza em formato "longo": tripulante, momento, dia, analito, valor
  3. aplica a MESMA ideia do AstroKatu: compara o pós-voo com o pré-voo DE CADA tripulante
  4. mede quanto tempo cada mudança leva para voltar ao normal do tripulante

Formato real dos arquivos (confirmado em out/2026): uma LINHA por amostra ("C001_serum_L-92"),
uma COLUNA por medida. O CMP traz "<analito>_value_<unidade>" e a faixa de referência
("_range_min_" / "_range_max_"); os painéis multiplex trazem "<analito>_concentration_<unidade>"
e uma cópia em "_percent" (ignorada).

Amostras: 4 tripulantes (C001-C004), pré-voo (L-92, L-44, L-3) e pós-voo (R+1, R+45, R+82, R+194).
Fonte: https://osdr.nasa.gov/bio/repo/data/studies/OSD-575

Uso:
  python nasa_osdr.py                 # baixa + analisa (precisa de internet)
  python nasa_osdr.py --local pasta/  # usa CSVs já baixados manualmente
Saídas em output/nasa/: osd575_longo.csv e osd575_variacao_pos_voo.csv
"""
import argparse
import re
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

BASE = "https://osdr.nasa.gov/geode-py/ws/studies/OSD-575/download?source=datamanager&file="
ARQUIVOS = {
    "cmp": "LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv",
    "imune": "LSDS-8_Multiplex_serum_immune_EvePanel_TRANSFORMED.csv",
    "cardiovascular": "LSDS-8_Multiplex_serum_cardiovascular_EvePanel_TRANSFORMED.csv",
}
DURACAO_MISSAO = 3  # Inspiration4 ficou ~3 dias em órbita (set/2021)

# Só 3 coletas de pré-voo: o desvio-padrão delas é instável e pode sair ~0, o que explode o z.
# Piso = 10% do valor de base (ordem da variação analítica + biológica desses exames).
PISO_CV = 0.10
Z_FORTE = 2.0

# ex.: C001_serum_L-92, C003_whole-blood_R+1, C2_L-3
AMOSTRA = re.compile(r"(C0*(\d+))\D.*?([LR])\s*([+-])\s*(\d+)", re.IGNORECASE)
# coluna de medida: "glucose_value_milligram_per_deciliter", "il_6_concentration_picogram_per_milliliter"
MEDIDA = re.compile(r"^(?P<analito>.+?)_(?:value|concentration)(?:_(?P<unidade>.+))?$")


def baixar(destino):
    destino.mkdir(parents=True, exist_ok=True)
    for painel, nome in ARQUIVOS.items():
        arq = destino / nome
        if arq.exists():
            continue
        print(f"baixando {painel}: {nome}")
        req = urllib.request.Request(BASE + nome, headers={"User-Agent": "astrokatu/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            arq.write_bytes(r.read())
    return destino


def ler_amostra(texto):
    """'C001_serum_L-92' -> ('C001', 'pre_voo', -92). Dia 0 = lançamento."""
    m = AMOSTRA.search(str(texto))
    if not m:
        return None
    tid = f"C{int(m.group(2)):03d}"
    fase, sinal, n = m.group(3).upper(), m.group(4), int(m.group(5))
    if fase == "L":
        return tid, "pre_voo", -n if sinal == "-" else n
    return tid, "pos_voo", DURACAO_MISSAO + (n if sinal == "+" else -n)


def faixa_referencia(df, analito):
    """(min, max) da faixa clínica do laboratório, quando o arquivo traz (só o CMP)."""
    def achar(*prefixos):
        col = next((c for c in df.columns if any(c.startswith(f"{analito}_{p}") for p in prefixos)), None)
        return pd.to_numeric(df[col], errors="coerce").median() if col else np.nan
    return achar("range_min"), achar("range_max", "max")


def para_longo(df, painel):
    """Uma linha por (amostra, analito). Usa só as colunas de medida (value/concentration)."""
    col_id = next((c for c in df.columns if df[c].astype(str).map(lambda v: bool(ler_amostra(v))).mean() > 0.8), None)
    if col_id is None:
        raise ValueError(f"{painel}: não achei os nomes das amostras. Colunas: {list(df.columns)[:15]}")

    medidas = {c: MEDIDA.match(c) for c in df.columns if c != col_id}
    medidas = {c: m for c, m in medidas.items() if m}
    if not medidas:
        raise ValueError(f"{painel}: nenhuma coluna '_value' ou '_concentration'. Colunas: {list(df.columns)[:15]}")

    longo = df.melt(id_vars=[col_id], value_vars=list(medidas), var_name="coluna", value_name="valor")
    longo = longo.rename(columns={col_id: "amostra"})
    longo["analito"] = longo.coluna.map(lambda c: medidas[c]["analito"])
    longo["unidade"] = longo.coluna.map(lambda c: medidas[c]["unidade"] or "")
    faixas = {m["analito"]: faixa_referencia(df, m["analito"]) for m in medidas.values()}
    longo["ref_min"] = longo.analito.map(lambda a: faixas[a][0])
    longo["ref_max"] = longo.analito.map(lambda a: faixas[a][1])

    info = longo["amostra"].map(ler_amostra)
    longo = longo[info.notna()].copy()
    longo[["tripulante_id", "fase", "dia"]] = pd.DataFrame(info[info.notna()].tolist(), index=longo.index)
    longo["valor"] = pd.to_numeric(longo["valor"], errors="coerce")
    longo["painel"] = painel
    return longo.dropna(subset=["valor"])[
        ["painel", "tripulante_id", "fase", "dia", "analito", "unidade", "valor", "ref_min", "ref_max"]]


def variacao_pos_voo(longo):
    """Para cada tripulante e analito: quanto o primeiro pós-voo se afastou do SEU pré-voo
    e em que coleta voltou para perto do normal dele."""
    linhas = []
    for (painel, tid, analito), g in longo.groupby(["painel", "tripulante_id", "analito"]):
        pre = g[g.fase == "pre_voo"].valor
        pos = g[g.fase == "pos_voo"].sort_values("dia")
        if len(pre) < 2 or pos.empty:
            continue
        base = pre.mean()
        sd = max(pre.std(), PISO_CV * abs(base))
        if sd == 0:
            continue
        z = (pos.valor - base) / sd
        primeiro = pos.iloc[0]
        z1 = z.iloc[0]
        # primeira coleta pós-voo em que |z| < Z_FORTE, se o R+1 estava fora do normal
        volta = next((int(d) for d, zz in zip(pos.dia.iloc[1:], z.iloc[1:]) if abs(zz) < Z_FORTE), None) \
            if abs(z1) >= Z_FORTE else None
        ref_min, ref_max = g.ref_min.iloc[0], g.ref_max.iloc[0]
        fora_faixa = bool((primeiro.valor < ref_min) or (primeiro.valor > ref_max)) \
            if pd.notna(ref_min) and pd.notna(ref_max) else None
        linhas.append({
            "painel": painel, "tripulante_id": tid, "analito": analito, "unidade": g.unidade.iloc[0],
            "base_pre_voo": round(base, 3), "sd_usado": round(sd, 3),
            "pos_voo_dia": int(primeiro.dia), "pos_voo_valor": round(primeiro.valor, 3),
            "variacao_pct": round((primeiro.valor - base) / base * 100, 1) if base else np.nan,
            "z_pessoal": round(z1, 2),
            "volta_ao_normal_dia": volta,
            "fora_faixa_clinica": fora_faixa,
        })
    return pd.DataFrame(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", help="pasta com os CSVs já baixados")
    args = ap.parse_args()

    pasta = Path(args.local) if args.local else baixar(Path("output/nasa/raw"))
    partes = []
    for painel, nome in ARQUIVOS.items():
        arq = pasta / nome
        if not arq.exists():
            print(f"(pulando {painel}: {nome} não encontrado)")
            continue
        partes.append(para_longo(pd.read_csv(arq, encoding="utf-8-sig"), painel))
    if not partes:
        raise SystemExit("nenhum arquivo do OSD-575 encontrado")

    longo = pd.concat(partes, ignore_index=True)
    out = Path("output/nasa")
    out.mkdir(parents=True, exist_ok=True)
    longo.to_csv(out / "osd575_longo.csv", index=False)

    var = variacao_pos_voo(longo)
    var.to_csv(out / "osd575_variacao_pos_voo.csv", index=False)

    print(f"\n{longo.tripulante_id.nunique()} tripulantes, {longo.analito.nunique()} analitos, "
          f"{longo.groupby(['tripulante_id', 'dia']).ngroups} coletas")
    fortes = var.loc[var.z_pessoal.abs() >= Z_FORTE]
    print(f"Mudanças fortes no R+1 (|z| >= {Z_FORTE} em relação ao próprio pré-voo): "
          f"{len(fortes)} de {len(var)} ({len(fortes) / len(var):.0%})")
    print("  por painel:", fortes.painel.value_counts().to_dict())
    # analitos que mudaram na MESMA direção em >= 3 dos 4 tripulantes: efeito do voo, não acaso
    direcao = fortes.assign(sobe=fortes.z_pessoal > 0).groupby(["painel", "analito", "sobe"]).size()
    comuns = direcao[direcao >= 3].reset_index(name="n_tripulantes")
    print(f"\nMudanças em >= 3 dos 4 tripulantes, mesma direção: {len(comuns)}")
    for _, r in comuns.iterrows():
        sub = fortes[(fortes.analito == r.analito) & ((fortes.z_pessoal > 0) == r.sobe)]
        print(f"  {r.painel:>14} {r.analito}: {'sobe' if r.sobe else 'cai'} em {r.n_tripulantes} "
              f"(mediana {sub.variacao_pct.median():+.0f}%)")
    cmp_fora = var[var.fora_faixa_clinica == True]  # noqa: E712
    print(f"\nCMP fora da faixa clínica no R+1: {len(cmp_fora)}")
    for _, r in cmp_fora.iterrows():
        print(f"  {r.tripulante_id} {r.analito}: {r.pos_voo_valor} {r.unidade}")


if __name__ == "__main__":
    main()

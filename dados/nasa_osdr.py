"""Dados REAIS da NASA: exames de sangue da tripulação do Inspiration4 (OSDR, estudo OSD-575).

O que faz:
  1. baixa do OSDR o painel metabólico (CMP) e os painéis de soro (imune e cardiovascular)
  2. organiza em formato "longo": tripulante, momento, dia, analito, valor
  3. aplica a MESMA ideia do AstroKatu: compara o pós-voo com o pré-voo DE CADA tripulante

Amostras: 4 tripulantes (C001-C004), pré-voo (L-92, L-44, L-3) e pós-voo (R+1, R+45, R+82...).
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

# ex.: C001_serum_L-92, C003_whole-blood_R+1, C2_L-3
AMOSTRA = re.compile(r"(C0*(\d+))\D.*?([LR])\s*([+-])\s*(\d+)", re.IGNORECASE)


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


def para_longo(df, painel):
    """Aceita os dois formatos comuns do OSDR:
    - largo por amostra: uma COLUNA por amostra, uma linha por analito
    - largo por analito: uma LINHA por amostra, uma coluna por analito
    """
    col_amostras = [c for c in df.columns if ler_amostra(c)]
    if len(col_amostras) >= 2:
        id_col = next(c for c in df.columns if c not in col_amostras)
        longo = df.melt(id_vars=[id_col], value_vars=col_amostras,
                        var_name="amostra", value_name="valor").rename(columns={id_col: "analito"})
    else:
        col_id = next((c for c in df.columns if df[c].astype(str).map(lambda v: bool(ler_amostra(v))).mean() > 0.8), None)
        if col_id is None:
            raise ValueError(f"{painel}: não achei os nomes das amostras. Colunas: {list(df.columns)[:15]}")
        numericas = [c for c in df.columns if c != col_id and pd.to_numeric(df[c], errors="coerce").notna().mean() > 0.5]
        longo = df.melt(id_vars=[col_id], value_vars=numericas,
                        var_name="analito", value_name="valor").rename(columns={col_id: "amostra"})

    info = longo["amostra"].map(ler_amostra)
    longo = longo[info.notna()].copy()
    longo[["tripulante_id", "fase", "dia"]] = pd.DataFrame(info[info.notna()].tolist(), index=longo.index)
    longo["valor"] = pd.to_numeric(longo["valor"], errors="coerce")
    longo["painel"] = painel
    return longo.dropna(subset=["valor"])[["painel", "tripulante_id", "fase", "dia", "analito", "valor"]]


def variacao_pos_voo(longo):
    """Para cada tripulante e analito: quanto o primeiro pós-voo se afastou do SEU pré-voo."""
    linhas = []
    for (painel, tid, analito), g in longo.groupby(["painel", "tripulante_id", "analito"]):
        pre = g[g.fase == "pre_voo"].valor
        pos = g[g.fase == "pos_voo"].sort_values("dia")
        if len(pre) < 2 or pos.empty:
            continue
        base, sd = pre.mean(), pre.std()
        primeiro = pos.iloc[0]
        linhas.append({
            "painel": painel, "tripulante_id": tid, "analito": analito,
            "base_pre_voo": round(base, 3),
            "pos_voo_dia": int(primeiro.dia), "pos_voo_valor": round(primeiro.valor, 3),
            "variacao_pct": round((primeiro.valor - base) / base * 100, 1) if base else np.nan,
            "z_pessoal": round((primeiro.valor - base) / sd, 2) if sd > 0 else np.nan,
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
        partes.append(para_longo(pd.read_csv(arq), painel))
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
    destaque = var.dropna(subset=["z_pessoal"]).loc[lambda d: d.z_pessoal.abs() >= 2]
    print(f"Mudanças fortes no pós-voo (|z| >= 2 em relação ao próprio pré-voo): {len(destaque)}")
    for _, r in destaque.sort_values("z_pessoal", key=abs, ascending=False).head(10).iterrows():
        print(f"  {r.tripulante_id} {r.painel:>14} {r.analito}: {r.variacao_pct:+.0f}% (z={r.z_pessoal:+.1f})")


if __name__ == "__main__":
    main()

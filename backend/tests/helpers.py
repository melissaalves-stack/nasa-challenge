"""Roda o motor em memória (sem banco) sobre os registros do simulador."""
from datetime import date
from types import SimpleNamespace as NS

from app.services import engine, rules as rl
from app.simulator.generator import generate_scenario

START = date(2026, 10, 1)
RULES = rl.load_rules()


def run_scenario(name, seed=42, start=START):
    records = generate_scenario(name, seed=seed, start=start)
    sleep, vitals, diary = [], [], []
    baselines, timeline = {}, []
    recent_hit_day = None
    for rec in records:
        sleep.append(NS(**rec.sleep))
        vitals += [NS(data_quality="good", **v) for v in rec.vitals]
        diary.append(NS(ts=rec.diary["ts"], features=rec.diary["features"], consent=True))
        block = recent_hit_day is not None and (rec.date - recent_hit_day).days <= 7
        res = engine.analyze(sleep, vitals, diary, baselines, rec.date,
                             block_baseline_updates=block, rules=RULES)
        baselines = res.baselines
        if res.hits:
            recent_hit_day = rec.date
        timeline.append((rec, res))
    return records, timeline, baselines

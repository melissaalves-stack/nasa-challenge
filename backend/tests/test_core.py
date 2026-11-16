"""Testes do núcleo de domínio (sem FastAPI/SQLAlchemy)."""
from datetime import date, timedelta

import pytest

from app.passwords import hash_password, verify_password
from app.services import actions, baseline as bl, privacy as pv
from app.simulator.generator import generate_scenario
from tests.helpers import run_scenario


# ------------------------------------------------------------- privacy
GOOD = {
    "neg_emotion_score": 0.62, "pos_emotion_score": 0.21, "stress_score": 0.71,
    "loneliness_score": 0.44, "anhedonia_score": 0.30, "suicidal_ideation_flag": 0.02,
    "suicidal_ideation_confidence": "low", "text_length": 412, "complexity": 0.58,
    "topic_tags": ["sono", "trabalho"],
}


def test_privacy_accepts_valid_features():
    out = pv.validate_diary_features(dict(GOOD), consent=True)
    assert set(out) == pv.ALLOWED_KEYS


def test_privacy_rejects_raw_text_field():
    bad = {**GOOD, "text": "hoje foi um dia difícil..."}
    with pytest.raises(pv.PrivacyViolation) as e:
        pv.validate_diary_features(bad, consent=True)
    assert e.value.status == 422 and "Unexpected fields" in str(e.value)
    assert "difícil" not in str(e.value)  # nunca ecoa o conteúdo


def test_privacy_rejects_free_text_in_topic_tags():
    with pytest.raises(pv.PrivacyViolation):
        pv.validate_diary_features({**GOOD, "topic_tags": ["eu me sinto sozinho"]}, consent=True)


def test_privacy_requires_consent_and_ranges():
    with pytest.raises(pv.PrivacyViolation) as e:
        pv.validate_diary_features(dict(GOOD), consent=False)
    assert e.value.status == 403
    with pytest.raises(pv.PrivacyViolation):
        pv.validate_diary_features({**GOOD, "stress_score": 1.4}, consent=True)
    with pytest.raises(pv.PrivacyViolation):
        pv.validate_diary_features({**GOOD, "stress_score": True}, consent=True)


def test_text_hash_format():
    assert pv.validate_text_hash("a" * 64)
    with pytest.raises(pv.PrivacyViolation):
        pv.validate_text_hash("texto cru aqui")


# ------------------------------------------------------------- baseline
def _vals(mean, sd, n, start, step=0.0):
    import numpy as np
    rng = np.random.default_rng(1)
    return {start + timedelta(days=i): float(mean + step * i + rng.normal(0, sd)) for i in range(n)}


def test_baseline_needs_min_samples():
    d0 = date(2026, 1, 1)
    assert bl.compute_baseline_update(_vals(7, .4, 8, d0), None, d0 + timedelta(days=7), metric="sleep_duration_h") is None
    assert bl.compute_baseline_update(_vals(7, .4, 14, d0), None, d0 + timedelta(days=13), metric="sleep_duration_h")


def test_baseline_ignores_insignificant_change():
    d0 = date(2026, 1, 1)
    prev = bl.fit_baseline(_vals(7.2, .4, 20, d0), d0 + timedelta(days=19))
    later = {**_vals(7.2, .4, 20, d0), **_vals(7.3, .4, 10, d0 + timedelta(days=20))}
    assert bl.compute_baseline_update(later, prev, d0 + timedelta(days=29), metric="sleep_duration_h") is None


def test_baseline_updates_on_sustained_shift_but_not_when_blocked():
    d0 = date(2026, 1, 1)
    prev = bl.fit_baseline(_vals(7.2, .4, 20, d0), d0 + timedelta(days=19))
    shifted = {**_vals(7.2, .4, 15, d0), **_vals(5.5, .3, 15, d0 + timedelta(days=15))}
    as_of = d0 + timedelta(days=29)
    assert bl.compute_baseline_update(shifted, prev, as_of, metric="sleep_duration_h") is not None
    assert bl.compute_baseline_update(shifted, prev, as_of, metric="sleep_duration_h", block=True) is None


# ------------------------------------------------------------- scenarios
def hits_by_day(timeline):
    return [(rec, {h.rule_id: h for h in res.hits}) for rec, res in timeline]


def test_simulator_is_deterministic():
    a = generate_scenario("recovery", seed=7, start=date(2026, 10, 1))
    b = generate_scenario("recovery", seed=7, start=date(2026, 10, 1))
    assert [r.sleep for r in a] == [r.sleep for r in b]


def test_simulated_diary_is_features_only():
    for rec in generate_scenario("suicidal_marker", seed=42, start=date(2026, 10, 1)):
        pv.validate_diary_features(rec.diary["features"], consent=True)


def test_healthy_baseline_no_alerts():
    _, tl, _ = run_scenario("healthy_baseline")
    assert not [r for r, h in hits_by_day(tl) if h]


def test_isolated_bad_night_does_not_alert():
    _, tl, _ = run_scenario("isolated_bad_night")
    assert not [r for r, h in hits_by_day(tl) if h]


def test_integrated_deterioration_escalates_watch_then_review():
    _, tl, _ = run_scenario("integrated_deterioration")
    first = {}
    for rec, hits in hits_by_day(tl):
        for h in hits.values():
            first.setdefault(h.severity, rec.index)
    assert first["watch"] < first["review_required"]
    day = next(h for rec, h in hits_by_day(tl) if "integrated_deterioration" in h)
    ev = day["integrated_deterioration"].evidence
    assert all("observed" in e for e in ev)  # explicável


def test_suicidal_marker_is_critical_and_never_automatic():
    _, tl, _ = run_scenario("suicidal_marker")
    crit = [(rec, h["diary_suicidal_marker"]) for rec, h in hits_by_day(tl) if "diary_suicidal_marker" in h]
    assert len(crit) == 1 and crit[0][0].index == 4
    hit = crit[0][1]
    assert hit.priority == "critical" and hit.auto_action is False
    assert hit.severity == "review_required"
    plan = actions.generate_action_plan(hit.severity, hit.priority, ["isolamento"])
    assert plan["status"] == "pending_human_review"
    assert all(a["auto_execute"] is False for a in plan["actions"])
    assert any(a.get("requires_human") for a in plan["actions"])


def test_recovery_stops_alerting_and_baseline_not_corrupted():
    records, tl, base = run_scenario("recovery")
    assert not tl[-1][1].hits
    healthy_mean = sum(r.sleep["duration_h"] for r in records[:14]) / 14
    assert abs(base["sleep_duration_h"].mean - healthy_mean) < 1e-6  # congelado
    assert base["sleep_duration_h"].n == 14


# ------------------------------------------------------------- actions / auth
def test_action_library_not_mutated_between_calls():
    before = len(actions.ACTION_LIBRARY["watch"])
    actions.generate_action_plan("watch", "normal", ["sono", "isolamento"])
    actions.generate_action_plan("watch", "normal", ["sono"])
    assert len(actions.ACTION_LIBRARY["watch"]) == before


def test_plan_always_has_disclaimer():
    for sev in ("info", "watch", "review_required"):
        assert "não" in actions.generate_action_plan(sev)["disclaimer"].lower()


def test_password_hashing():
    h = hash_password("demo1234")
    assert verify_password("demo1234", h) and not verify_password("outra", h)
    assert not verify_password("x", "lixo")

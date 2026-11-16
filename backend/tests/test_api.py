"""Teste de integração da API (precisa de requirements-dev instalado).

    pytest -q tests/test_api.py
"""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

import hashlib  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import seed  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        seed.main()
        yield c


def login(c, email):
    r = c.post("/auth/login", json={"email": email, "password": seed.PASSWORD})
    assert r.status_code == 200, r.text
    d = r.json()
    return {"Authorization": f"Bearer {d['access_token']}"}, d["user"]["id"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_diary_rejects_raw_text_and_never_echoes_it(client):
    h, _ = login(client, "astro1@astrokatu.dev")
    body = {"ts": datetime.now(timezone.utc).isoformat(), "text_hash": hashlib.sha256(b"x").hexdigest(),
            "local_model_version": "t", "consent": True,
            "features": {"text": "segredo muito pessoal"}}
    r = client.post("/entries/diary", json=body, headers=h)
    assert r.status_code == 422 and "segredo" not in r.text


def test_demo_flow_deterioration_and_isolation(client):
    ah, admin_id = login(client, "admin@astrokatu.dev")
    ch, _ = login(client, "clinico@astrokatu.dev")
    _, astro1 = login(client, "astro1@astrokatu.dev")
    _, astro2 = login(client, "astro2@astrokatu.dev")

    # noite ruim isolada: nenhum alerta
    r = client.post("/admin/simulate", json={"scenario": "isolated_bad_night", "user_id": astro1}, headers=ah)
    assert r.status_code == 200 and r.json()["alerts"] == []

    # deterioração integrada: chega em review_required
    r = client.post("/admin/simulate", json={"scenario": "integrated_deterioration", "user_id": astro1}, headers=ah)
    assert "review_required" in {a["severity"] for a in r.json()["alerts"]}

    # marcador de ideação no outro astronauta: fila crítica, sem ação automática
    client.post("/admin/simulate", json={"scenario": "suicidal_marker", "user_id": astro2}, headers=ah)
    q = client.get("/clinician/review-queue", headers=ch).json()
    assert q["disclaimer"]
    assert q["data"][0]["priority"] == "critical" and q["data"][0]["auto_action"] is False

    # clínico revisa; audit log registra
    alert_id = q["data"][0]["id"]
    assert client.post(f"/clinician/alerts/{alert_id}/review",
                       json={"decision": "confirmed", "note": "contato feito"}, headers=ch).status_code == 200
    log = client.get("/clinician/audit-log", headers=ch).json()["data"]
    assert any(e["action"] == "review_confirmed" for e in log)


def test_astronaut_cannot_use_clinician_or_admin_routes(client):
    h, _ = login(client, "astro1@astrokatu.dev")
    assert client.get("/clinician/overview", headers=h).status_code == 403
    assert client.get("/admin/scenarios", headers=h).status_code == 403

"""DeepSeek automations: scoring rubric, missing key, mocked JSON calls."""

from __future__ import annotations

from unittest.mock import AsyncMock

from app.services.automations import fill_template, score_from_fields


def test_score_rubric_hot():
    result = score_from_fields(budget=15000, timeline_days=14, employees=80, is_decision_maker=True)
    assert result["score"] == 10
    assert result["band"] == "hot"
    assert result["routing"] == "senior_sales"


def test_score_rubric_cold():
    result = score_from_fields(budget=500, timeline_days=90, employees=5, is_decision_maker=False)
    assert result["score"] == 0
    assert result["band"] == "cold"
    assert result["routing"] == "archive"


def test_fill_template_missing():
    text, missing = fill_template("Hola {{nombre_cliente}}, total {{precio_total}}", {"nombre_cliente": "Ana"})
    assert "Ana" in text
    assert missing == ["precio_total"]


def test_score_requires_deepseek_key(authenticated_client):
    response = authenticated_client.post(
        "/api/automations/score",
        json={"payload": {"empresa": "Acme", "presupuesto": "$20.000"}},
    )
    assert response.status_code == 400
    assert "DeepSeek" in response.json()["detail"]


def test_score_with_mocked_deepseek(authenticated_client, monkeypatch):
    put = authenticated_client.put("/api/providers/deepseek", json={"api_key": "sk-test-deepseek"})
    assert put.status_code == 200, put.text

    async def fake_json(**_kwargs):
        return {
            "name": "Luis Pérez",
            "email": "luis@acme.com",
            "phone": None,
            "company": "Acme",
            "role": "CEO",
            "budget_usd": 20000,
            "timeline_days": 10,
            "employees": 60,
            "is_decision_maker": True,
            "notes": "Quiere empezar ya",
            "cleaned": {"company": "Acme"},
        }

    monkeypatch.setattr("app.services.automations.deepseek_json", AsyncMock(side_effect=fake_json))
    response = authenticated_client.post(
        "/api/automations/score",
        json={"payload": "Formulario: Luis, Acme, presupuesto 20k, somos 60, soy el dueño, en 10 días"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kind"] == "score"
    assert body["user_id"]
    assert body["result"]["band"] == "hot"
    assert body["result"]["score"] == 10
    assert body["result"]["lead"]["company"] == "Acme"

    mine = authenticated_client.get("/api/automations/runs")
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert mine.json()[0]["id"] == body["id"]


def test_runs_are_private_to_each_user(client, monkeypatch):
    first = client.post(
        "/api/auth/register",
        json={"agency_name": "Agencia Uno", "name": "Ana", "email": "ana-auto@prisma.com", "password": "contrasena-segura"},
    )
    assert first.status_code == 201, first.text
    client.put("/api/providers/deepseek", json={"api_key": "sk-a"})

    async def fake_json(**_kwargs):
        return {
            "name": "Ana Lead",
            "email": "a@x.com",
            "phone": None,
            "company": "Uno",
            "role": None,
            "budget_usd": 500,
            "timeline_days": 90,
            "employees": 3,
            "is_decision_maker": False,
            "notes": "",
            "cleaned": {},
        }

    monkeypatch.setattr("app.services.automations.deepseek_json", AsyncMock(side_effect=fake_json))
    created = client.post("/api/automations/normalize", json={"payload": {"x": 1}})
    assert created.status_code == 200, created.text
    run_id = created.json()["id"]

    client.post("/api/auth/logout")
    second = client.post(
        "/api/auth/register",
        json={"agency_name": "Agencia Dos", "name": "Beto", "email": "beto-auto@prisma.com", "password": "contrasena-segura"},
    )
    assert second.status_code == 201, second.text
    listed = client.get("/api/automations/runs")
    assert listed.status_code == 200
    assert listed.json() == []
    hidden = client.get(f"/api/automations/runs/{run_id}")
    assert hidden.status_code == 404

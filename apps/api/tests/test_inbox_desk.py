from uuid import uuid4

from fastapi.testclient import TestClient


def _agent(client: TestClient) -> dict:
    customer = client.post(
        "/api/clients",
        json={"name": "La Casona Desk", "industry": "", "description": "", "general_context": "", "is_active": True},
    ).json()
    return client.post(
        "/api/agents",
        json={
            "client_id": customer["id"],
            "name": "Mesero",
            "description": "",
            "instructions": "",
            "personality": "",
            "model": "",
            "is_active": True,
        },
    ).json()


def test_register_seeds_canned_and_lists_members(authenticated_client: TestClient):
    client = authenticated_client
    canned = client.get("/api/conversations/canned")
    assert canned.status_code == 200
    codes = {item["shortcode"] for item in canned.json()}
    assert {"horario", "momento", "gracias"} <= codes

    members = client.get("/api/agency/members")
    assert members.status_code == 200
    assert any(row["email"] == "ana@prisma.com" for row in members.json())


def test_take_control_assigns_labels_and_mine_filter(authenticated_client: TestClient):
    client = authenticated_client
    agent = _agent(client)
    conversation = client.post("/api/conversations", json={"agent_id": agent["id"]}).json()
    conversation_id = conversation["id"]
    me = client.get("/api/auth/me").json()

    taken = client.patch(f"/api/conversations/{conversation_id}/mode", json={"mode": "human"}).json()
    assert taken["mode"] == "human"
    assert taken["assigned_user_id"] == me["id"]
    assert taken["assigned_user_name"] == me["name"]

    mine = client.get("/api/conversations/inbox?assigned=me").json()
    assert any(row["id"] == conversation_id for row in mine)

    labeled = client.patch(
        f"/api/conversations/{conversation_id}/labels",
        json={"labels": ["urgent", "bogus", "urgent"]},
    ).json()
    assert labeled["labels"] == ["urgent"]

    urgent = client.get("/api/conversations/inbox?label=urgent").json()
    assert any(row["id"] == conversation_id and row["labels"] == ["urgent"] for row in urgent)
    assert client.get("/api/conversations/inbox?label=waiting").json() == []

    cleared = client.patch(f"/api/conversations/{conversation_id}/assign", json={"assigned_user_id": None}).json()
    assert cleared["assigned_user_id"] is None
    assert client.get("/api/conversations/inbox?assigned=me").json() == []
    unassigned = client.get("/api/conversations/inbox?assigned=unassigned").json()
    assert any(row["id"] == conversation_id for row in unassigned)

    outsider = client.patch(
        f"/api/conversations/{conversation_id}/assign",
        json={"assigned_user_id": str(uuid4())},
    )
    assert outsider.status_code == 400


def test_canned_crud_and_duplicate_shortcode(authenticated_client: TestClient):
    client = authenticated_client
    created = client.post(
        "/api/conversations/canned",
        json={"title": "Reservas", "body": "¿Para cuántas personas y a qué hora?", "shortcode": "reserva"},
    )
    assert created.status_code == 201
    assert created.json()["shortcode"] == "reserva"
    canned_id = created.json()["id"]

    clash = client.post(
        "/api/conversations/canned",
        json={"title": "Otra", "body": "Duplicado", "shortcode": "reserva"},
    )
    assert clash.status_code == 409

    auto = client.post("/api/conversations/canned", json={"title": "Reservas", "body": "Otra reserva"})
    assert auto.status_code == 201
    assert auto.json()["shortcode"].startswith("reservas")
    assert auto.json()["shortcode"] != "reserva"

    updated = client.patch(
        f"/api/conversations/canned/{canned_id}",
        json={"body": "Dime fecha, hora y personas."},
    ).json()
    assert updated["body"].startswith("Dime fecha")

    assert client.delete(f"/api/conversations/canned/{canned_id}").status_code == 204
    leftover = {item["id"] for item in client.get("/api/conversations/canned").json()}
    assert canned_id not in leftover

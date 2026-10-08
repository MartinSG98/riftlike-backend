import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RIFTLIKE_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from app import db
    from app.config import get_settings

    get_settings.cache_clear()
    db._engine = None
    from app.main import app

    with TestClient(app) as c:
        yield c
    db._engine = None
    get_settings.cache_clear()


def test_catalog_lists_teams_and_champions(client):
    body = client.get("/api/catalog").json()
    assert len(body["teams"]) == 19
    assert body["champions"]["Azir"]["focus"] == "late"


def test_run_lifecycle(client):
    created = client.post("/api/runs", json={"team": "GEN"})
    assert created.status_code == 201
    run = created.json()
    assert run["pending"]["kind"] == "first"
    assert len(run["offers"]) == 3

    champ = run["offers"][0]["champ"]
    run = client.post(f"/api/runs/{run['id']}/actions", json={"type": "choose_first", "champ": champ}).json()
    assert run["pending"] is None
    assert run["map"] is not None
    assert len(run["reachable"]) == 2

    again = client.get(f"/api/runs/{run['id']}").json()
    assert again["map"] == run["map"]

    bad = client.post(f"/api/runs/{run['id']}/actions", json={"type": "continue"})
    assert bad.status_code == 409


def test_matchups_list_both_directions(client):
    from app.game.power import matchup

    body = client.get("/api/matchups/Azir", params={"role": "MID"}).json()
    assert body["role"] == "MID"
    assert body["counters"] and body["countered_by"]
    for entry in body["counters"]:
        assert matchup("Azir", entry["champ"]) == entry["value"] > 0
    for entry in body["countered_by"]:
        assert matchup(entry["champ"], "Azir") == entry["value"] > 0
    values = [e["value"] for e in body["counters"]]
    assert values == sorted(values, reverse=True)


def test_matchups_default_to_the_main_role_and_reject_unknown_names(client):
    assert client.get("/api/matchups/Nunu%20%26%20Willump").json()["role"] == "JGL"
    assert client.get("/api/matchups/Nobody").status_code == 404


def test_unknown_team_and_run(client):
    assert client.post("/api/runs", json={"team": "NOPE"}).status_code == 400
    assert client.get("/api/runs/missing").status_code == 404

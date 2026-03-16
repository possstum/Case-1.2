def test_health_returns_component_statuses(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app"]["status"] == "ok"
    assert payload["database"]["status"] == "ok"
    assert payload["redis"]["status"] == "ok"

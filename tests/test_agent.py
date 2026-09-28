def test_demo_incidents_file_exists():
    import json
    from pathlib import Path

    file_path = Path("data/demo_incidents.json")

    assert file_path.exists()

    data = json.loads(file_path.read_text(encoding="utf-8"))

    assert len(data) == 4
    assert data[0]["project"] == "payments-api"


def test_demo_incident_structure():
    import json
    from pathlib import Path

    file_path = Path("data/demo_incidents.json")
    data = json.loads(file_path.read_text(encoding="utf-8"))

    required_fields = {
        "project",
        "environment",
        "type",
        "summary",
        "lesson",
    }

    for incident in data:
        assert required_fields.issubset(incident.keys())
import json
from pathlib import Path

from src import agent


def test_demo_incidents_file_exists():
    file_path = Path("data/demo_incidents.json")

    assert file_path.exists()

    data = json.loads(file_path.read_text(encoding="utf-8"))

    assert len(data) == 4
    assert data[0]["project"] == "payments-api"


def test_demo_incident_structure():
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


def test_recall_memories_removes_duplicates(monkeypatch):
    class FakeItem:
        def __init__(self, text):
            self.text = text

    class FakeResult:
        results = [
            FakeItem("Database migration failed"),
            FakeItem("Database migration failed"),
            FakeItem("Missing environment variable"),
            FakeItem(""),
            FakeItem(None),
        ]

    class FakeHindsight:
        def recall(self, **kwargs):
            return FakeResult()

    result = agent.recall_memories(
        FakeHindsight(),
        "deployment failure",
    )

    assert result == [
        "Database migration failed",
        "Missing environment variable",
    ]
import json
import os
from typing import Any

from dotenv import load_dotenv
from hindsight_client import Hindsight
from openai import OpenAI


load_dotenv()


HINDSIGHT_BASE_URL = os.getenv(
    "HINDSIGHT_BASE_URL",
    "https://api.hindsight.vectorize.io",
)

HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY")

HINDSIGHT_BANK_ID = os.getenv(
    "HINDSIGHT_BANK_ID",
    "memoryops-devops",
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)


def get_hindsight() -> Hindsight:
    """Create the Hindsight client."""

    if not HINDSIGHT_API_KEY:
        raise RuntimeError(
            "HINDSIGHT_API_KEY is missing. Check your .env file."
        )

    return Hindsight(
        base_url=HINDSIGHT_BASE_URL,
        api_key=HINDSIGHT_API_KEY,
    )


def get_llm() -> OpenAI:
    """Create the Groq OpenAI-compatible client."""

    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Check your .env file."
        )

    return OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )


def ensure_bank(client: Hindsight) -> None:
    """Create or update the Hindsight memory bank."""

    client.create_bank(
        bank_id=HINDSIGHT_BANK_ID,
        name="MemoryOps DevOps Memory",
    )


def retain_memory(client: Hindsight, content: str) -> None:
    """Store a deployment experience in Hindsight."""

    client.retain(
        bank_id=HINDSIGHT_BANK_ID,
        content=content,
    )


def recall_memories(client: Hindsight, query: str) -> list[str]:
    """Recall relevant previous DevOps experiences without duplicates."""

    result = client.recall(
        bank_id=HINDSIGHT_BANK_ID,
        query=query,
        max_tokens=2000,
    )

    memories = []
    seen = set()

    for item in getattr(result, "results", []) or []:
        text = getattr(item, "text", None)

        if not text:
            continue

        text = text.strip()

        if text in seen:
            continue

        seen.add(text)
        memories.append(text)

    return memories[:8]


def analyze_deployment(
    project: str,
    environment: str,
    commit: str,
    change_summary: str,
    logs: str,
) -> dict[str, Any]:
    """
    Analyze a deployment using current deployment data
    and relevant historical memories.
    """

    hindsight = get_hindsight()
    llm = get_llm()

    ensure_bank(hindsight)

    current_event = f"""
Current deployment analysis:

Project: {project}
Environment: {environment}
Commit: {commit}
Change summary: {change_summary}

Deployment logs:
{logs}
""".strip()

    # Retrieve historical memories BEFORE storing the current event.
    # This prevents the current deployment from influencing its own recall.
    memories = recall_memories(
        hindsight,
        query=f"""
        Find previous deployment failures, successful deployments,
        rollback lessons, configuration mistakes, database migration
        problems, testing issues and other incidents relevant to:

        Project: {project}
        Change: {change_summary}
        Logs: {logs}
        """,
    )

    history = "\n\n".join(
        f"- {memory}"
        for memory in memories
    )

    if not history:
        history = "No relevant previous memories were found."

    # Store the current deployment after historical memory retrieval.
    retain_memory(
        hindsight,
        current_event,
    )

    prompt = f"""
You are MemoryOps, a DevOps deployment risk analysis agent.

Your job is to analyze a proposed deployment using:

1. The current deployment information.
2. Relevant historical operational memories retrieved from Hindsight.

CURRENT DEPLOYMENT

Project: {project}
Environment: {environment}
Commit: {commit}
Change summary: {change_summary}

Logs:
{logs}

HISTORICAL MEMORY

{history}

Use the historical memories only when they are relevant
to the current deployment.

Do not invent incidents or historical facts.

Return ONLY valid JSON with this structure:

{{
  "risk": "LOW | MEDIUM | HIGH",
  "summary": "short explanation",
  "recommended_action": "what the developer should do",
  "checks": [
    "check 1",
    "check 2",
    "check 3"
  ],
  "reasoning": "explain how the historical memory influenced the recommendation"
}}
""".strip()

    response = llm.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful DevOps reliability assistant. "
                    "Use historical memory when it is relevant and "
                    "do not invent incidents."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    raw_result = response.choices[0].message.content or "{}"

    try:
        decision = json.loads(raw_result)

    except json.JSONDecodeError:
        decision = {
            "risk": "MEDIUM",
            "summary": raw_result,
            "recommended_action": "Review the deployment manually.",
            "checks": [],
            "reasoning": "The model did not return valid JSON.",
        }

    # Store the agent's decision so future deployments
    # can learn from previous analyses.
    retain_memory(
        hindsight,
        f"""
MemoryOps analysis result:

Project: {project}
Environment: {environment}
Commit: {commit}
Change: {change_summary}

Agent decision:
{json.dumps(decision, indent=2)}
""".strip(),
    )

    return {
        "decision": decision,
        "recalled_memories": memories,
    }


def seed_demo() -> None:
    """
    Load demo incidents from data/demo_incidents.json
    and store them in Hindsight.
    """

    hindsight = get_hindsight()

    ensure_bank(hindsight)

    # Locate data/demo_incidents.json from the project root.
    project_root = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    file_path = os.path.join(
        project_root,
        "data",
        "demo_incidents.json",
    )

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Demo incidents file not found: {file_path}"
        )

    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        incidents = json.load(file)

    for incident in incidents:
        content = f"""
Project: {incident["project"]}
Environment: {incident["environment"]}
Incident type: {incident["type"]}

Summary:
{incident["summary"]}

Lesson:
{incident["lesson"]}
""".strip()

        retain_memory(
            hindsight,
            content,
        )

    print(
        f"Added {len(incidents)} demo memories to Hindsight."
    )


if __name__ == "__main__":
    seed_demo()
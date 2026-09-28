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
    """Create/update the Hindsight memory bank."""
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

 

    # Ask Hindsight for similar historical experiences.
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
    # This prevents the current event from influencing its own recall.
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

    # Remember the agent's decision so future deployments
    # can learn from this analysis.
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
    Add realistic demo incidents to Hindsight.

    These examples let us demonstrate the memory feature
    before connecting a real CI/CD pipeline.
    """

    hindsight = get_hindsight()

    ensure_bank(hindsight)

    incidents = [
        """
Incident: payments-api deployment failure.

Environment: production.

Change: database schema migration.

Problem:
The new database migration was incompatible with the previous
application version. The deployment caused application errors.

Root cause:
The migration removed a field before all application instances
had stopped using it.

Fix:
The team restored the previous application version and changed
the migration to a backward-compatible approach.

Lesson:
For database migrations, deploy compatible schema changes first,
then update the application, and verify rollback before production.
""",

        """
Incident: orders-service deployment failure.

Environment: production.

Change: new payment configuration.

Problem:
The deployment succeeded technically but the service could not
process orders.

Root cause:
A required production environment variable was missing.

Fix:
The variable was added to the deployment configuration.

Lesson:
Validate required environment variables before production deployment.
""",

        """
Incident: catalog-service CI failure.

Environment: staging.

Change: dependency upgrade.

Problem:
The test suite produced intermittent failures.

Root cause:
Tests were using a shared database that was not reset correctly.

Fix:
The test environment was isolated and database cleanup was added.

Lesson:
Flaky integration tests should be investigated before treating a
deployment as safe.
""",

        """
Incident: inventory-api successful deployment.

Environment: production.

Change: dependency upgrade.

Process:
The team ran automated tests, deployed to a canary group,
monitored errors, and kept a rollback plan ready.

Result:
Deployment completed successfully.

Lesson:
Canary deployment plus monitoring and rollback preparation
reduced deployment risk.
""",
    ]

    for incident in incidents:
        retain_memory(hindsight, incident)

    print(f"Added {len(incidents)} demo memories to Hindsight.")


if __name__ == "__main__":
    seed_demo()
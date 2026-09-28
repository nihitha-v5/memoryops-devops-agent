from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .agent import analyze_deployment


app = FastAPI(
    title="MemoryOps - DevOps Pipeline Agent"
)


class DeploymentRequest(BaseModel):
    project: str
    environment: str
    commit: str
    change_summary: str
    logs: str


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MemoryOps - DevOps Pipeline Agent</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            margin: 0;
            padding: 30px;
            color: #1f2937;
        }

        .container {
            max-width: 1000px;
            margin: auto;
        }

        h1 {
            margin-bottom: 5px;
        }

        .subtitle {
            color: #6b7280;
            margin-bottom: 25px;
        }

        .card {
            background: white;
            padding: 22px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }

        label {
            display: block;
            font-weight: bold;
            margin-top: 14px;
            margin-bottom: 6px;
        }

        input, textarea {
            width: 100%;
            box-sizing: border-box;
            padding: 11px;
            border: 1px solid #d1d5db;
            border-radius: 7px;
            font-size: 14px;
        }

        textarea {
            min-height: 120px;
            resize: vertical;
        }

        button {
            margin-top: 18px;
            padding: 12px 18px;
            border: none;
            border-radius: 7px;
            background: #111827;
            color: white;
            cursor: pointer;
            font-size: 15px;
        }

        button:hover {
            opacity: 0.9;
        }

        .risk {
            font-size: 24px;
            font-weight: bold;
        }

        .memory {
            background: #f9fafb;
            border-left: 4px solid #6b7280;
            padding: 12px;
            margin: 10px 0;
            border-radius: 5px;
        }

        .loading {
            display: none;
            color: #6b7280;
            margin-top: 15px;
        }

        ul {
            line-height: 1.7;
        }

        pre {
            white-space: pre-wrap;
            background: #f9fafb;
            padding: 12px;
            border-radius: 7px;
        }
    </style>
</head>

<body>

<div class="container">

    <h1>MemoryOps</h1>

    <div class="subtitle">
        Memory-first DevOps Pipeline Risk Agent
    </div>

    <div class="card">

        <h2>Analyze Deployment</h2>

        <label>Project</label>
        <input id="project" value="payments-api">

        <label>Environment</label>
        <input id="environment" value="production">

        <label>Commit</label>
        <input id="commit" value="a91f42c">

        <label>Change Summary</label>
        <textarea id="change">
Database schema migration for the payments service.
        </textarea>

        <label>Deployment Logs</label>
        <textarea id="logs">Running database migration...
Applying migration 2026_09_add_payment_status
Starting application deployment...
Running health checks...
        </textarea>

        <button onclick="analyze()">
            Analyze Deployment
        </button>

        <div id="loading" class="loading">
            Analyzing deployment using Hindsight memory...
        </div>

    </div>


    <div id="result"></div>

</div>


<script>

async function analyze() {

    document.getElementById("loading").style.display = "block";
    document.getElementById("result").innerHTML = "";

    const data = {
        project: document.getElementById("project").value,
        environment: document.getElementById("environment").value,
        commit: document.getElementById("commit").value,
        change_summary: document.getElementById("change").value,
        logs: document.getElementById("logs").value
    };

    try {

        const response = await fetch("/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Analysis failed");
        }

        const decision = result.decision;

        let checks = "";

        for (const check of decision.checks || []) {
            checks += `<li>${check}</li>`;
        }

        let memories = "";

        for (const memory of result.recalled_memories || []) {
            memories += `
                <div class="memory">
                    ${memory}
                </div>
            `;
        }

        document.getElementById("result").innerHTML = `

            <div class="card">

                <h2>Risk Assessment</h2>

                <div class="risk">
                    ${decision.risk || "UNKNOWN"}
                </div>

                <h3>Summary</h3>
                <p>${decision.summary || ""}</p>

                <h3>Recommended Action</h3>
                <p>${decision.recommended_action || ""}</p>

                <h3>Pre-deployment Checks</h3>

                <ul>
                    ${checks}
                </ul>

                <h3>Why?</h3>

                <p>
                    ${decision.reasoning || ""}
                </p>

            </div>


            <div class="card">

                <h2>Hindsight Memories Used</h2>

                ${
                    memories ||
                    "<p>No previous memories were recalled.</p>"
                }

            </div>

        `;

    } catch (error) {

        document.getElementById("result").innerHTML = `
            <div class="card">
                <h2>Error</h2>
                <pre>${error.message}</pre>
            </div>
        `;

    } finally {

        document.getElementById("loading").style.display = "none";

    }

}

</script>

</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML


@app.post("/analyze")
def analyze(request: DeploymentRequest):

    try:

        result = analyze_deployment(
            project=request.project,
            environment=request.environment,
            commit=request.commit,
            change_summary=request.change_summary,
            logs=request.logs,
        )

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
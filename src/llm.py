"""
LLM integration using Google Vertex AI (Gemini 2.5 Flash)
Credentials are picked up automatically via Application Default Credentials (ADC).
Run the ADC setup first:
    curl -sSL https://storage.googleapis.com/cloud-samples-data/adc/setup_adc.sh | bash
"""

import os
import re
import json
import vertexai
from vertexai.generative_models import GenerativeModel

# ── Settings file path (written by the web UI) ────────────────────────────
_BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(_BASE_DIR, ".bmad_settings.json")


def load_settings() -> dict:
    """Load persisted settings from disk (written via the web UI)."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_settings(data: dict) -> None:
    """Persist settings to disk."""
    existing = load_settings()
    existing.update(data)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


# ── Project / location config ─────────────────────────────────────────────
# Priority: settings.json > env var > gcloud CLI
def _resolve_project() -> str:
    # 1. Web UI saved setting
    project = load_settings().get("gcp_project")
    if project:
        return project
    # 2. Environment variable
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if project:
        return project
    # 3. gcloud CLI active project
    try:
        import subprocess
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True, text=True, timeout=5
        )
        project = result.stdout.strip()
        if project and project != "(unset)":
            return project
    except Exception:
        pass
    raise EnvironmentError(
        "Google Cloud project not found. "
        "Enter your Project ID in the Settings panel on the diagram page."
    )


LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")
MODEL_ID  = os.environ.get("VERTEX_MODEL",    "gemini-2.5-flash")

# ── Diagram generation ────────────────────────────────────────────────────

DIAGRAM_PROMPT_TEMPLATE = """
You are a software architecture expert. Analyze the following project documents and generate
a comprehensive Mermaid.js architecture diagram that shows:

1. The system layers (Frontend, Backend, Database, External Services)
2. Data flow and request/response paths
3. Key components and their relationships
4. Integration points (APIs, queues, auth, storage, etc.)

OUTPUT RULES (strictly follow):
- Return ONLY the raw Mermaid diagram code block, no prose before or after.
- Start with ```mermaid and end with ```.
- Use `graph TD` (top-down) or `flowchart TD` direction.
- Use descriptive node labels.
- Group related components with subgraph blocks.
- Keep it clean and readable.

--- PROJECT DOCUMENTS ---
{context}
--- END OF DOCUMENTS ---
"""


def generate_architecture_diagram(ingested_docs: dict) -> str:
    """
    Calls Gemini 2.5 Flash via Vertex AI ADC to generate a Mermaid architecture diagram.
    Returns the raw Mermaid diagram string (without the ```mermaid fence).
    """
    project = _resolve_project()
    vertexai.init(project=project, location=LOCATION)

    # Build context from all ingested documents (cap at ~12k chars to stay within limits)
    context_parts = []
    total = 0
    for filename, content in ingested_docs.items():
        snippet = f"### {filename}\n{content[:3000]}"
        total += len(snippet)
        context_parts.append(snippet)
        if total > 12000:
            break

    context = "\n\n".join(context_parts)
    prompt  = DIAGRAM_PROMPT_TEMPLATE.format(context=context)

    model    = GenerativeModel(MODEL_ID)
    response = model.generate_content(prompt)
    raw      = response.text.strip()

    # Strip fenced code block markers if present
    raw = re.sub(r"^```mermaid\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$",        "", raw)
    return raw.strip()

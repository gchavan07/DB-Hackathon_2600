"""
LLM integration using Google Vertex AI (Gemini 2.5 Flash)
Credentials are picked up via Application Default Credentials (ADC).
The credentials file path can be set through the web UI Settings panel.
"""

import os
import re
import json
import vertexai
from vertexai.generative_models import GenerativeModel

# ── Settings file path (written by the web UI) ────────────────────────────
_BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


# ── Credential file auto-detection ───────────────────────────────────────
# Ordered list of candidate paths to search for ADC credentials.
def _candidate_credential_paths() -> list:
    candidates = []
    # 1. The known path from the ADC setup script (Linux / WSL / Cloud Shell)
    candidates.append("/home/chavangaurav747234_gmail_com/.config/gcloud/application_default_credentials.json")
    # 2. Standard Linux/Mac ADC location
    home = os.path.expanduser("~")
    candidates.append(os.path.join(home, ".config", "gcloud", "application_default_credentials.json"))
    # 3. Standard Windows ADC location
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        candidates.append(os.path.join(appdata, "gcloud", "application_default_credentials.json"))
    # 4. CLOUDSDK_CONFIG override
    sdk_config = os.environ.get("CLOUDSDK_CONFIG", "")
    if sdk_config:
        candidates.append(os.path.join(sdk_config, "application_default_credentials.json"))
    return candidates


def _resolve_credentials() -> str:
    """
    Return the path to the ADC credentials JSON file.
    Priority: settings.json saved path > GOOGLE_APPLICATION_CREDENTIALS env var > auto-detect.
    Returns the resolved path (and sets GOOGLE_APPLICATION_CREDENTIALS so the SDK picks it up).
    Raises FileNotFoundError if no credentials file can be found.
    """
    # 1. Web UI saved path
    saved = load_settings().get("credentials_path", "").strip()
    if saved and os.path.isfile(saved):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = saved
        return saved

    # 2. Already set in environment
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path

    # 3. Auto-detect from well-known locations
    for path in _candidate_credential_paths():
        if os.path.isfile(path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
            return path

    raise FileNotFoundError(
        "ADC credentials file not found. "
        "Please enter the full path to your application_default_credentials.json "
        "in the Settings panel on the diagram page."
    )


# ── Project / location config ─────────────────────────────────────────────
# Priority: settings.json > env var > gcloud CLI > credentials file project hint
def _resolve_project() -> str:
    # 1. Web UI saved setting
    project = load_settings().get("gcp_project", "").strip()
    if project:
        return project
    # 2. Environment variable
    project = (os.environ.get("GOOGLE_CLOUD_PROJECT") or
               os.environ.get("GCLOUD_PROJECT", "")).strip()
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
    # Resolve credentials BEFORE initialising Vertex AI
    _resolve_credentials()

    project  = _resolve_project()
    settings = load_settings()
    location = settings.get("vertex_location", LOCATION).strip() or LOCATION

    vertexai.init(project=project, location=location)

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

# ── Report analysis prompt ────────────────────────────────────────────────

REPORT_PROMPT_TEMPLATE = """
You are a senior software architect and technical documentation expert.
Carefully read ALL of the project documents provided below and generate a comprehensive,
detailed technical report that is FULLY based on the actual content of these documents.

Do NOT use generic boilerplate. Every statement must be grounded in the provided documents.

Your report MUST include the following sections:

### 1. Executive Summary
Summarize the project's purpose, goals, and key stakeholders based on the documents.

### 2. System Architecture & End-to-End Project Flow
#### 2.1 Architectural Overview
Describe the actual tech stack, layers, and components found in the documents.
#### 2.2 Execution Workflow
Describe the actual step-by-step flow derived from the documents.

### 3. Project Scope Definition
List the actual in-scope features, epics, and tickets found. List deferred/out-of-scope items.

### 4. Jira / Ticket Integration & Backlog Gaps
Using the Jira/ticket data, identify gaps, missing acceptance criteria, unlinked stories, and blockers.
Present findings as a markdown table.

### 5. Confluence / Documentation Analysis
Summarize what the Confluence/wiki docs say. Note any inconsistencies with the Jira data.

### 6. Code & Implementation Analysis
Summarize the code files or architecture descriptions found. Call out design patterns, APIs, and tech choices.

### 7. Risks, Issues & Recommendations
List concrete risks found in the documents and specific actionable recommendations.

### 8. Next Steps
Provide a prioritised list of next steps derived from the document content.

OUTPUT FORMAT:
- Use clean Markdown with proper headings.
- Use bullet points, numbered lists, and tables where appropriate.
- Be specific — use actual names, ticket IDs, feature names, and tech stack details from the documents.

--- PROJECT DOCUMENTS ---
{context}
--- END OF DOCUMENTS ---

User's specific instruction / focus area: {instruction}
"""


def generate_report_analysis(ingested_docs: dict, instruction: str) -> str:
    """
    Uses Gemini 2.5 Flash to analyze the actual ingested documents and
    return a comprehensive, document-grounded markdown analysis string.
    """
    _resolve_credentials()
    project  = _resolve_project()
    settings = load_settings()
    location = settings.get("vertex_location", LOCATION).strip() or LOCATION

    vertexai.init(project=project, location=location)

    # Build context — include as much content as possible (cap at 50k chars)
    context_parts = []
    total = 0
    for filename, content in ingested_docs.items():
        if content.startswith("[Error") or content.startswith("[python-docx"):
            continue
        snippet = f"=== FILE: {filename} ===\n{content[:8000]}"
        total += len(snippet)
        context_parts.append(snippet)
        if total > 50000:
            break

    context = "\n\n".join(context_parts)
    prompt  = REPORT_PROMPT_TEMPLATE.format(context=context, instruction=instruction)

    model    = GenerativeModel(MODEL_ID)
    response = model.generate_content(prompt)
    return response.text.strip()


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
    _resolve_credentials()
    project  = _resolve_project()
    settings = load_settings()
    location = settings.get("vertex_location", LOCATION).strip() or LOCATION

    vertexai.init(project=project, location=location)

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

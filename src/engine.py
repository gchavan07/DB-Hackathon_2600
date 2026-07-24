
import os
from rich.console import Console
from rich.prompt import Prompt
from .ingester import load_input_documents
from .matcher import find_matching_skills
from .formatter import save_bmad_markdown

console = Console()


# â”€â”€ Fallback: keyword-driven extraction from actual document text â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _extract_analysis_from_docs(ingested_data: dict, instruction: str) -> str:
    """
    When LLM is not configured, extract real content from the documents
    using keyword matching instead of returning hardcoded boilerplate.
    """
    all_text = "\n".join(ingested_data.values())
    lines    = all_text.splitlines()

    # â”€â”€ Collect content per category â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    confluence_content = ""
    jira_content       = ""
    code_content       = ""
    service_content    = ""

    for filename, content in ingested_data.items():
        fn = filename.lower()
        if any(k in fn for k in ["confluence", "wiki", "overview", "vision", "strategy"]):
            confluence_content += content + "\n"
        elif any(k in fn for k in ["jira", "epic", "ticket", "backlog", "story"]):
            jira_content += content + "\n"
        elif any(k in fn for k in ["servicenow", "incident", "change"]):
            service_content += content + "\n"
        else:
            code_content += content + "\n"

    # â”€â”€ Helper: extract bullet lines containing a keyword â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def extract_mentions(text: str, keywords: list, max_items: int = 8) -> list:
        found, seen = [], set()
        for line in text.splitlines():
            l = line.strip()
            if not l or len(l) < 10:
                continue
            if any(kw.lower() in l.lower() for kw in keywords):
                key = l[:80]
                if key not in seen:
                    seen.add(key)
                    found.append(l)
                    if len(found) >= max_items:
                        break
        return found

    # â”€â”€ Extract epics & tickets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    epics, tickets, gaps = [], [], []
    current_epic = None
    for line in jira_content.splitlines():
        l = line.strip()
        if l.startswith("## Epic") or l.startswith("# Epic"):
            current_epic = l.lstrip("#").strip()
            epics.append(current_epic)
        elif l.startswith("### Ticket") or l.startswith("Summary:"):
            tickets.append(l.lstrip("#").strip())
        elif any(k in l.lower() for k in ["missing", "gap", "todo", "blocked", "not implemented", "not done", "in progress"]):
            gaps.append(l)

    # â”€â”€ Extract tech stack mentions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tech_keywords = ["angular", "react", "spring boot", "java", "node", "mongodb",
                     "postgresql", "firebase", "redis", "kafka", "docker", "kubernetes",
                     "aws", "gcp", "azure", "rest", "graphql", "jwt", "microservice"]
    tech_found = [t for t in tech_keywords if t in all_text.lower()]

    # â”€â”€ Extract features & scope â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    scope_keywords = ["authentication", "signup", "login", "playlist", "streaming",
                      "search", "recommendation", "download", "podcast", "karaoke",
                      "payment", "subscription", "social", "collaboration", "lyrics"]
    features_found = [f for f in scope_keywords if f in all_text.lower()]

    # â”€â”€ Extract risks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    risk_lines = extract_mentions(all_text, ["risk", "mitigation", "challenge", "concern", "issue"], max_items=6)

    # â”€â”€ Extract recommendations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    rec_lines = extract_mentions(all_text, ["recommend", "should", "must", "ensure", "next step", "priority"], max_items=6)

    # â”€â”€ Extract project name â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    project_name = "the project"
    for line in (confluence_content + code_content).splitlines():
        l = line.strip()
        if l.startswith("# ") and len(l) > 3:
            project_name = l.lstrip("# ").strip()
            break

    # â”€â”€ Confluence page headings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    confluence_pages = [l.lstrip("# ").strip() for l in confluence_content.splitlines()
                        if l.startswith("# ") or l.startswith("## ")]
    confluence_pages = list(dict.fromkeys(confluence_pages))[:10]

    # â”€â”€ Build analysis output â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    buf = []

    buf.append("### 1. Executive Summary")
    buf.append(f"This report is based on analysis of **{len(ingested_data)} source document(s)**: "
               f"{', '.join(f'`{k}`' for k in ingested_data.keys())}.")
    buf.append(f"\nThe project identified is: **{project_name}**.")
    if features_found:
        buf.append(f"Core capabilities identified: {', '.join(f.title() for f in features_found[:8])}.")

    buf.append("\n### 2. System Architecture & End-to-End Project Flow")
    buf.append("#### 2.1 Tech Stack & Components Identified")
    if tech_found:
        for t in tech_found:
            buf.append(f"- **{t.title()}** â€” referenced in source documents")
    else:
        buf.append("- No specific tech stack identifiers found in documents.")

    buf.append("\n#### 2.2 Execution Workflow (from document content)")
    workflow = extract_mentions(all_text, ["flow", "step", "process", "request", "response", "api", "endpoint"], max_items=5)
    if workflow:
        for i, w in enumerate(workflow, 1):
            buf.append(f"{i}. {w}")
    else:
        buf.append("- Workflow details not explicitly documented. Review code files for API flow.")

    buf.append("\n### 3. Project Scope Definition")
    buf.append("#### In-Scope Features (extracted from documents)")
    if features_found:
        for f in features_found:
            buf.append(f"- {f.title()}")
    buf.append("\n#### Out-of-Scope / Deferred (from documents)")
    deferred = extract_mentions(all_text, ["deferred", "out of scope", "phase 2", "phase 3", "future", "later"], max_items=5)
    if deferred:
        for d in deferred:
            buf.append(f"- {d}")
    else:
        buf.append("- No explicitly deferred items found.")

    buf.append("\n### 4. Jira / Backlog Analysis")
    if epics:
        buf.append(f"**Epics found ({len(epics)}):**")
        for e in epics[:10]:
            buf.append(f"- {e}")
    if tickets:
        buf.append(f"\n**Sample tickets ({min(len(tickets), 10)} of {len(tickets)}):**")
        for t in tickets[:10]:
            buf.append(f"- {t}")
    if gaps:
        buf.append("\n**Identified Gaps:**")
        for g in gaps[:6]:
            buf.append(f"- {g}")

    buf.append("\n**Backlog Gap Analysis:**")
    buf.append("| Gap Type | Finding | Recommendation |")
    buf.append("| :--- | :--- | :--- |")
    if not tickets:
        buf.append("| Missing Tickets | No Jira ticket data found | Add Jira export to input_docs |")
    else:
        statuses = [l for l in jira_content.splitlines() if l.strip().lower().startswith("status:")]
        in_progress = [s for s in statuses if "progress" in s.lower() or "todo" in s.lower()]
        if in_progress:
            buf.append(f"| Open Work | {len(in_progress)} ticket(s) still In Progress/To Do | Prioritise and assign owners |")
        no_ac = [l for l in jira_content.splitlines() if "acceptance criteria" not in l.lower() and l.strip().startswith("### Ticket")]
        buf.append(f"| Acceptance Criteria | {len(no_ac)} ticket(s) may need AC review | Validate criteria against actual test coverage |")
        buf.append("| Documentation Sync | Confluence docs exist â€” cross-check with ticket scope | Run documentation review sprint |")

    buf.append("\n### 5. Confluence / Documentation Analysis")
    if confluence_pages:
        buf.append(f"Documentation pages found ({len(confluence_pages)}):")
        for p in confluence_pages:
            buf.append(f"- **{p}**")
    else:
        buf.append("- No Confluence/wiki content detected.")

    buf.append("\n### 6. Code & Implementation Analysis")
    code_tech = extract_mentions(code_content, ["import", "class", "controller", "service", "repository",
                                                 "@RestController", "@Component", "@Injectable", "endpoint"], max_items=6)
    if code_tech:
        for c in code_tech:
            buf.append(f"- `{c[:120]}`")
    else:
        buf.append("- No code files analysed.")

    buf.append("\n### 7. Risks & Recommendations")
    if risk_lines:
        buf.append("**Risks identified from documents:**")
        for r in risk_lines:
            buf.append(f"- {r}")
    else:
        buf.append("- No explicit risk statements found; recommend conducting a risk workshop.")
    if rec_lines:
        buf.append("\n**Recommendations from documents:**")
        for r in rec_lines:
            buf.append(f"- {r}")

    buf.append("\n### 8. Next Steps")
    next_steps = extract_mentions(all_text, ["next step", "action", "sprint", "milestone", "release", "deploy"], max_items=5)
    if next_steps:
        for i, n in enumerate(next_steps, 1):
            buf.append(f"{i}. {n}")
    else:
        buf.append("1. Review all Jira tickets for missing acceptance criteria.")
        buf.append("2. Align Confluence documentation with latest sprint scope.")
        buf.append("3. Ensure CI/CD pipelines are linked to Jira stories.")

    buf.append(f"\n> âš ï¸ *This analysis was generated without LLM â€” using keyword extraction from {len(ingested_data)} document(s). "
               "Configure GCP credentials in the Settings panel to enable full AI-powered analysis.*")

    return "\n".join(buf)


# â”€â”€ LLM-powered analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _llm_analysis(ingested_data: dict, instruction: str) -> str:
    from .llm import generate_report_analysis
    return generate_report_analysis(ingested_data, instruction)


# â”€â”€ Shared core: load docs, match skills, analyse, save â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _core_workflow(instruction: str, ingested_data: dict) -> str:
    matched_skills = find_matching_skills(instruction)

    # Try LLM first; fall back to keyword extraction
    try:
        final_analysis = _llm_analysis(ingested_data, instruction)
    except Exception as e:
        final_analysis = _extract_analysis_from_docs(ingested_data, instruction)
        final_analysis += f"\n\n> *LLM unavailable ({type(e).__name__}: {e}). Showing keyword-extracted analysis.*"

    output_path = save_bmad_markdown(
        "Architecture_Scope_Report", instruction, matched_skills, ingested_data, final_analysis
    )
    return output_path


def run_workflow(instruction: str) -> str:
    console.print("\n[bold cyan]=== BMAD Agent Orchestrator Started ===[/bold cyan]")

    if not instruction or len(instruction.strip()) < 5:
        console.print("[bold red]Instruction is too brief. Interactive elicitation required.[/bold red]")
        instruction = Prompt.ask("[bold magenta]Please provide more specific details or objectives[/bold magenta]")

    console.print("[yellow]âž” Loading documents from input_docs/...[/yellow]")
    ingested_data = load_input_documents()
    console.print(f"[green]âœ” Loaded {len(ingested_data)} document source(s): {', '.join(ingested_data.keys())}[/green]")

    console.print("[yellow]âž” Analysing document content...[/yellow]")
    output_path = _core_workflow(instruction, ingested_data)

    console.print(f"\n[bold green]âœ” Report saved to:[/bold green] [underline]{output_path}[/underline]\n")
    return output_path


def run_workflow_web(instruction: str) -> str:
    """Headless variant used by the Flask web app."""
    ingested_data = load_input_documents()
    return _core_workflow(instruction, ingested_data)
    

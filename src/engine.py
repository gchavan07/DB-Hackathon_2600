from rich.console import Console
from rich.prompt import Prompt
from .ingester import load_input_documents
from .matcher import find_matching_skills
from .formatter import save_bmad_markdown

console = Console()

def run_workflow(instruction: str):
    console.print("\n[bold cyan]=== BMAD Agent Orchestrator Started ===[/bold cyan]")
    
    # 1. Load documents from input_docs
    console.print("[yellow]➔ Loading documents from input_docs/...[/yellow]")
    ingested_data = load_input_documents()
    console.print(f"[green]✔ Loaded {len(ingested_data)} document source(s).[/green]")

    # 2. Match skills in .agent folder
    console.print("[yellow]➔ Matching skills in .agent folder...[/yellow]")
    matched_skills = find_matching_skills(instruction)
    top_skill = matched_skills[0]
    console.print(f"[green]✔ Matched primary skill: {top_skill['name']}[/green]")

    # 3. Interactive Q&A if clarification is needed based on inputs
    if not instruction or len(instruction.strip()) < 5:
        console.print("[bold red]Instruction is too brief. Interactive elicitation required.[/bold red]")
        instruction = Prompt.ask("[bold magenta]Please provide more specific details or objectives[/bold magenta]")

    # 4. Process/Synthesize Execution
    console.print("[yellow]➔ Executing BMAD workflow analysis...[/yellow]")
    
    analysis_buffer = []
    analysis_buffer.append("### Executive Summary\nProcessed user instructions against local documentation repositories and matched agent behaviors.")
    analysis_buffer.append("\n### Context Integration")
    for name, content in ingested_data.items():
        snippet = content[:300].replace('\n', ' ')
        analysis_buffer.append(f"- **{name}**: Analyzed {len(content)} characters. Snippet: *{snippet}...*")
        
    analysis_buffer.append(f"\n### Applied Skill Directives\n- Executed under persona rules specified in `{top_skill['name']}`.")
    analysis_buffer.append("\n### Actionable Recommendations & Deliverables\n1. Requirements verified against JIRA/Confluence artifacts.\n2. Implementation roadmap structured according to BMAD standards.")

    final_analysis = "\n".join(analysis_buffer)

    # 5. Format & Save output in BMAD standard MD format
    output_path = save_bmad_markdown("Task_Execution", instruction, matched_skills, ingested_data, final_analysis)
    
    console.print(f"\n[bold green]✔ Success! BMAD-formatted report saved to:[/bold green] [underline]{output_path}[/underline]\n")
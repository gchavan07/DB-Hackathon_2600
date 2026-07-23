import click
from src.engine import run_workflow

@click.command()
@click.option('--instruction', prompt='Enter your instruction for the BMAD agent', help='Instructions to guide the execution workflow.')
def main(instruction):
    """BMAD Python Orchestrator CLI Entry Point."""
    run_workflow(instruction)

if __name__ == "__main__":
    main()
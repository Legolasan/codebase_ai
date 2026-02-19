"""Main entry point and CLI for the coding assistant."""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = typer.Typer(
    name="assistant",
    help="Multi-agent coding assistant with RAG-powered codebase understanding",
    add_completion=False,
)
console = Console()


def check_api_key() -> bool:
    """Check if the API key is configured."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Error:[/red] ANTHROPIC_API_KEY not set.\n"
            "Set it in your environment or create a .env file.",
            style="bold",
        )
        return False
    return True


@app.command()
def index(
    path: str = typer.Argument(".", help="Path to the codebase to index"),
    collection: str = typer.Option("codebase", "--collection", "-c", help="Collection name"),
):
    """Index a codebase for semantic search."""
    from .indexer.vector_store import index_codebase

    codebase_path = Path(path).resolve()

    if not codebase_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {path}")
        raise typer.Exit(1)

    console.print(f"\nIndexing codebase at: [cyan]{codebase_path}[/cyan]\n")

    try:
        stats = index_codebase(codebase_path, collection)

        # Display stats
        table = Table(title="Indexing Complete")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Files", str(stats["total_files"]))
        table.add_row("Total Chunks", str(stats["chunks_indexed"]))
        table.add_row("Persist Directory", stats["persist_dir"])

        console.print(table)

        # Show language breakdown
        if stats.get("by_language"):
            lang_table = Table(title="Files by Language")
            lang_table.add_column("Language", style="cyan")
            lang_table.add_column("Files", style="green")
            lang_table.add_column("Chunks", style="yellow")

            for lang, data in sorted(stats["by_language"].items()):
                lang_table.add_row(lang, str(data["files"]), str(data["chunks"]))

            console.print(lang_table)

    except Exception as e:
        console.print(f"[red]Error indexing codebase:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question about the codebase"),
    collection: str = typer.Option("codebase", "--collection", "-c", help="Collection name"),
):
    """Ask a question about the indexed codebase."""
    if not check_api_key():
        raise typer.Exit(1)

    from .tools.code_search import init_vector_store
    from .graph.workflow import run_workflow

    # Initialize vector store
    init_vector_store(collection)

    console.print(f"\n[cyan]Question:[/cyan] {question}\n")

    with console.status("[bold green]Thinking..."):
        try:
            result = run_workflow(question)

            if result.get("error"):
                console.print(f"[red]Error:[/red] {result['error']}")
            else:
                # Display result
                console.print(Panel(
                    Markdown(result.get("final_result", "No response generated.")),
                    title=f"[green]Response[/green] (via {result.get('current_agent', 'unknown')} agent)",
                    border_style="green",
                ))

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command()
def implement(
    description: str = typer.Argument(..., help="Description of what to implement"),
    collection: str = typer.Option("codebase", "--collection", "-c", help="Collection name"),
    with_tests: bool = typer.Option(False, "--tests", "-t", help="Also generate tests"),
    with_review: bool = typer.Option(False, "--review", "-r", help="Include code review"),
):
    """Implement a feature or fix based on description."""
    if not check_api_key():
        raise typer.Exit(1)

    from .tools.code_search import init_vector_store
    from .graph.workflow import run_workflow

    init_vector_store(collection)

    console.print(f"\n[cyan]Task:[/cyan] {description}\n")

    agents_used = ["implementation"]
    if with_tests:
        agents_used.append("testing")
    if with_review:
        agents_used.append("review")

    console.print(f"[dim]Agents: {', '.join(agents_used)}[/dim]\n")

    with console.status("[bold green]Working..."):
        try:
            result = run_workflow(
                f"Implement: {description}",
                needs_testing=with_tests,
                needs_review=with_review,
            )

            if result.get("error"):
                console.print(f"[red]Error:[/red] {result['error']}")
            else:
                console.print(Panel(
                    Markdown(result.get("final_result", "No response generated.")),
                    title="[green]Implementation Complete[/green]",
                    border_style="green",
                ))

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command()
def test(
    target: str = typer.Argument(None, help="File or function to test"),
    collection: str = typer.Option("codebase", "--collection", "-c", help="Collection name"),
    generate: bool = typer.Option(True, "--generate/--run", "-g/-r", help="Generate tests vs run existing"),
):
    """Generate or run tests."""
    if not check_api_key():
        raise typer.Exit(1)

    from .tools.code_search import init_vector_store
    from .graph.workflow import run_workflow

    init_vector_store(collection)

    if generate:
        prompt = f"Generate tests for: {target or 'the main functionality'}"
    else:
        prompt = f"Run tests for: {target or 'the entire codebase'}"

    console.print(f"\n[cyan]Task:[/cyan] {prompt}\n")

    with console.status("[bold green]Working..."):
        try:
            result = run_workflow(prompt)

            if result.get("error"):
                console.print(f"[red]Error:[/red] {result['error']}")
            else:
                console.print(Panel(
                    Markdown(result.get("final_result", "No response generated.")),
                    title="[green]Testing[/green]",
                    border_style="green",
                ))

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command()
def review(
    target: str = typer.Argument(None, help="File or changes to review"),
    collection: str = typer.Option("codebase", "--collection", "-c", help="Collection name"),
    security: bool = typer.Option(False, "--security", "-s", help="Focus on security"),
    performance: bool = typer.Option(False, "--performance", "-p", help="Focus on performance"),
):
    """Review code for quality, security, or performance."""
    if not check_api_key():
        raise typer.Exit(1)

    from .tools.code_search import init_vector_store
    from .graph.workflow import run_workflow

    init_vector_store(collection)

    focus = []
    if security:
        focus.append("security vulnerabilities")
    if performance:
        focus.append("performance issues")
    if not focus:
        focus.append("quality and best practices")

    prompt = f"Review {target or 'recent changes'} focusing on: {', '.join(focus)}"

    console.print(f"\n[cyan]Task:[/cyan] {prompt}\n")

    with console.status("[bold green]Reviewing..."):
        try:
            result = run_workflow(prompt)

            if result.get("error"):
                console.print(f"[red]Error:[/red] {result['error']}")
            else:
                console.print(Panel(
                    Markdown(result.get("final_result", "No response generated.")),
                    title="[green]Code Review[/green]",
                    border_style="green",
                ))

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command()
def chat(
    collection: str = typer.Option("codebase", "--collection", "-c", help="Collection name"),
    mode: str = typer.Option("ask", "--mode", "-m", help="Permission mode: full, readonly, ask"),
):
    """Start an interactive chat session."""
    if not check_api_key():
        raise typer.Exit(1)

    from .config import set_permission_mode
    from .tools.code_search import init_vector_store
    from .agents import OrchestratorAgent

    # Set permission mode
    try:
        set_permission_mode(mode)
    except ValueError:
        console.print(f"[red]Invalid mode:[/red] {mode}. Use: full, readonly, or ask")
        raise typer.Exit(1)

    init_vector_store(collection)
    orchestrator = OrchestratorAgent()

    console.print(Panel(
        "[bold cyan]Multi-Agent Coding Assistant[/bold cyan]\n\n"
        f"Mode: [yellow]{mode}[/yellow]\n"
        "Type [green]help[/green] for commands, [red]exit[/red] to quit",
        title="Welcome",
        border_style="cyan",
    ))

    conversation_history = []

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

            if not user_input.strip():
                continue

            # Handle special commands
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("\n[yellow]Goodbye![/yellow]")
                break

            if user_input.lower() == "help":
                _show_help()
                continue

            if user_input.lower() == "clear":
                conversation_history = []
                console.print("[dim]Conversation cleared.[/dim]")
                continue

            if user_input.lower() == "agents":
                console.print(Markdown(orchestrator.get_agent_descriptions()))
                continue

            # Process request
            with console.status("[bold green]Thinking..."):
                result = orchestrator.invoke(user_input, conversation_history)

            # Update conversation history
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({
                "role": "assistant",
                "content": result.get("content", "")
            })

            # Display response
            agent_name = result.get("routed_to", "unknown")
            console.print(f"\n[dim]({agent_name} agent)[/dim]")
            console.print(Panel(
                Markdown(result.get("content", "No response generated.")),
                border_style="green",
            ))

            # Handle tool calls if any
            if result.get("tool_calls"):
                console.print("[dim]Tools used:[/dim]")
                for tool_call in result["tool_calls"]:
                    console.print(f"  - {tool_call.get('name', 'unknown')}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit.[/yellow]")
            continue
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            continue


def _show_help():
    """Show help information."""
    help_text = """
## Commands

- **help** - Show this help message
- **clear** - Clear conversation history
- **agents** - Show available agents
- **exit** - Exit the chat

## Tips

- Ask questions naturally: "Where is the login function?"
- Request implementations: "Add input validation to the user form"
- Ask for reviews: "Review the authentication module for security issues"
- Generate tests: "Write tests for the API endpoints"

## Agents

- **Research**: Finding information, understanding code
- **Implementation**: Writing and modifying code
- **Testing**: Creating and running tests
- **Review**: Code review and quality checks
"""
    console.print(Markdown(help_text))


@app.command()
def status():
    """Show current configuration and status."""
    from .config import get_config

    config = get_config()

    table = Table(title="Configuration Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("API Key", "***" + os.getenv("ANTHROPIC_API_KEY", "")[-4:] if os.getenv("ANTHROPIC_API_KEY") else "[red]Not set[/red]")
    table.add_row("Model", config.model_name)
    table.add_row("Permission Mode", config.permission_mode.value)
    table.add_row("Persist Directory", str(config.chroma_persist_dir))

    console.print(table)

    # Check if codebase is indexed
    try:
        from .indexer.vector_store import VectorStore
        store = VectorStore()
        stats = store.get_stats()
        console.print(f"\nIndexed chunks: [green]{stats['total_chunks']}[/green]")
    except Exception:
        console.print("\n[yellow]No codebase indexed yet. Run 'assistant index' first.[/yellow]")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()

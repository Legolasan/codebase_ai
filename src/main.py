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

# Plugin sub-commands
plugins_app = typer.Typer(help="Manage plugins")
app.add_typer(plugins_app, name="plugins")

# Auth sub-commands (for GitHub auth plugin)
auth_app = typer.Typer(help="Manage authentication")
app.add_typer(auth_app, name="auth")

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

        # Auto-scan for security issues if security_scanner plugin is enabled
        try:
            from .plugins import get_registry
            registry = get_registry()
            if registry.is_enabled("security_scanner"):
                plugin = registry.get("security_scanner")
                if plugin and plugin.auto_scan_on_index:
                    console.print("\n[dim]Running security scan...[/dim]")
                    report = plugin.scan_codebase(str(codebase_path))
                    if report.findings:
                        console.print(f"\n[yellow]Security scan found {len(report.findings)} issues[/yellow]")
                        console.print(report.to_summary())
                        if report.has_critical():
                            console.print("[red bold]CRITICAL issues found! Run 'assistant security scan' for details.[/red bold]")
                    else:
                        console.print("[green]Security scan: No issues found[/green]")
        except Exception as e:
            # Don't fail indexing if security scan fails
            pass

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
    description: str = typer.Argument(None, help="Description of what to implement"),
    collection: str = typer.Option("codebase", "--collection", "-c", help="Collection name"),
    with_tests: bool = typer.Option(False, "--tests", "-t", help="Also generate tests"),
    with_review: bool = typer.Option(False, "--review", "-r", help="Include code review"),
    from_prd: str = typer.Option(None, "--from-prd", "-p", help="Path to PRD file to implement"),
):
    """Implement a feature or fix based on description or PRD."""
    if not check_api_key():
        raise typer.Exit(1)

    if not description and not from_prd:
        console.print("[red]Error:[/red] Provide either a description or --from-prd path")
        raise typer.Exit(1)

    from .tools.code_search import init_vector_store
    from .graph.workflow import run_workflow
    from .agents import ImplementationAgent

    init_vector_store(collection)

    # Handle PRD-based implementation
    if from_prd:
        console.print(f"\n[cyan]Implementing from PRD:[/cyan] {from_prd}\n")

        # Read PRD content
        from pathlib import Path
        prd_path = Path(from_prd)
        if not prd_path.exists():
            console.print(f"[red]Error:[/red] PRD file not found: {from_prd}")
            raise typer.Exit(1)

        prd_content = prd_path.read_text()
        console.print("[dim]PRD loaded. Starting implementation...[/dim]\n")

        agents_used = ["implementation (PRD-driven)"]
        if with_tests:
            agents_used.append("testing")
        if with_review:
            agents_used.append("review")

        console.print(f"[dim]Agents: {', '.join(agents_used)}[/dim]\n")

        with console.status("[bold green]Implementing from PRD..."):
            try:
                # Create implementation agent with PRD context
                impl_agent = ImplementationAgent(prd_context=prd_content)
                result = impl_agent.implement_from_prd(str(prd_path))

                if "Error" in result.get("content", ""):
                    console.print(f"[red]Error:[/red] {result['content']}")
                else:
                    console.print(Panel(
                        Markdown(result.get("content", "No response generated.")),
                        title="[green]PRD Implementation Complete[/green]",
                        border_style="green",
                    ))

            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1)
    else:
        # Standard implementation
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
- Create PRDs: "Create a PRD for user authentication"

## Agents

- **Research**: Finding information, understanding code
- **Implementation**: Writing and modifying code
- **Testing**: Creating and running tests
- **Review**: Code review and quality checks
- **PRD**: Creating product requirements documents
"""
    console.print(Markdown(help_text))


@app.command()
def prd(
    description: str = typer.Argument(..., help="Description of the feature to create PRD for"),
    output_dir: str = typer.Option("docs/prd", "--output", "-o", help="Output directory for PRD"),
    collection: str = typer.Option("codebase", "--collection", "-c", help="Collection name"),
    no_research: bool = typer.Option(False, "--no-research", help="Skip web research for competitors"),
):
    """Create a Product Requirements Document for a feature."""
    if not check_api_key():
        raise typer.Exit(1)

    from .tools.code_search import init_vector_store
    from .graph.workflow import run_workflow
    from .graph.state import TaskType

    init_vector_store(collection)

    console.print(f"\n[cyan]Creating PRD for:[/cyan] {description}\n")

    if not no_research:
        console.print("[dim]Including competitor research via web search...[/dim]\n")

    with console.status("[bold green]Generating PRD..."):
        try:
            # Add PRD prefix to trigger PRD routing
            request = f"Create a PRD for: {description}"
            result = run_workflow(request)

            if result.get("error"):
                console.print(f"[red]Error:[/red] {result['error']}")
            else:
                # Show PRD file path if saved
                if result.get("prd_file_path"):
                    console.print(f"\n[green]✓[/green] PRD saved to: [cyan]{result['prd_file_path']}[/cyan]\n")

                console.print(Panel(
                    Markdown(result.get("final_result", "No PRD generated.")),
                    title="[green]Product Requirements Document[/green]",
                    border_style="green",
                ))

                # Show next steps
                console.print("\n[bold]Next Steps:[/bold]")
                console.print("1. Review the PRD and make any necessary changes")
                console.print("2. Get stakeholder approval")
                if result.get("prd_file_path"):
                    console.print(f"3. Implement with: [cyan]assistant implement --from-prd {result.get('prd_file_path')}[/cyan]")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


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

    # Show enabled plugins
    try:
        from .plugins import get_registry
        registry = get_registry()
        enabled = registry.get_enabled()
        if enabled:
            console.print(f"\n[bold]Enabled Plugins ({len(enabled)}):[/bold]")
            for plugin in enabled:
                console.print(f"  [green]{plugin.name}[/green] v{plugin.version}")
        else:
            console.print("\n[dim]No plugins enabled. Run 'assistant plugins list' to see available plugins.[/dim]")
    except ImportError:
        pass


# =============================================================================
# Plugin Management Commands
# =============================================================================


@plugins_app.command("list")
def plugins_list():
    """List all available plugins."""
    from .plugins import get_registry

    registry = get_registry()
    plugins = registry.list_all()

    if not plugins:
        console.print("[yellow]No plugins discovered.[/yellow]")
        return

    table = Table(title="Available Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="dim")
    table.add_column("Status")
    table.add_column("Description")

    for plugin in plugins:
        status = "[green]Enabled[/green]" if plugin.enabled else "[dim]Disabled[/dim]"
        table.add_row(plugin.name, plugin.version, status, plugin.description)

    console.print(table)


@plugins_app.command("enable")
def plugins_enable(name: str = typer.Argument(..., help="Plugin name to enable")):
    """Enable a plugin."""
    from .plugins import get_registry, PluginError, PluginDependencyError

    registry = get_registry()

    try:
        registry.enable(name)
        console.print(f"[green]Enabled plugin:[/green] {name}")
    except PluginDependencyError as e:
        console.print(f"[red]Missing dependencies:[/red] {', '.join(e.missing_deps)}")
        console.print(f"Install with: pip install {' '.join(e.missing_deps)}")
    except PluginError as e:
        console.print(f"[red]Error:[/red] {e.message}")


@plugins_app.command("disable")
def plugins_disable(name: str = typer.Argument(..., help="Plugin name to disable")):
    """Disable a plugin."""
    from .plugins import get_registry

    registry = get_registry()
    registry.disable(name)
    console.print(f"[yellow]Disabled plugin:[/yellow] {name}")


@plugins_app.command("status")
def plugins_status():
    """Show enabled plugins and their status."""
    from .plugins import get_registry

    registry = get_registry()
    enabled = registry.get_enabled()

    if not enabled:
        console.print("[yellow]No plugins enabled.[/yellow]")
        console.print("Enable plugins with: assistant plugins enable <name>")
        return

    console.print(f"\n[bold]Enabled Plugins ({len(enabled)})[/bold]\n")

    for plugin in enabled:
        console.print(f"  [green]{plugin.name}[/green] v{plugin.version}")
        console.print(f"    {plugin.description}")

        # Show plugin tools
        tools = plugin.get_tools()
        if tools:
            tool_names = [t.name for t in tools]
            console.print(f"    [dim]Tools: {', '.join(tool_names)}[/dim]")


# =============================================================================
# Multi-Directory Commands (from multi_dir plugin)
# =============================================================================


@app.command("add-dir")
def add_dir(
    path: str = typer.Argument(..., help="Path to directory to add"),
    alias: Optional[str] = typer.Option(None, "--alias", "-a", help="Alias for the directory"),
):
    """Add a directory to multi-directory index."""
    from .plugins import get_registry

    registry = get_registry()
    plugin = registry.get("multi_dir")

    if not plugin or not registry.is_enabled("multi_dir"):
        console.print("[yellow]Multi-directory plugin not enabled.[/yellow]")
        console.print("Enable with: assistant plugins enable multi_dir")
        return

    plugin.add_directory_command(path, alias)


@app.command("list-dirs")
def list_dirs():
    """List configured directories."""
    from .plugins import get_registry

    registry = get_registry()
    plugin = registry.get("multi_dir")

    if not plugin or not registry.is_enabled("multi_dir"):
        console.print("[yellow]Multi-directory plugin not enabled.[/yellow]")
        return

    plugin.list_directories_command()


@app.command("remove-dir")
def remove_dir(
    alias_or_path: str = typer.Argument(..., help="Alias or path of directory to remove"),
):
    """Remove a directory from multi-directory index."""
    from .plugins import get_registry

    registry = get_registry()
    plugin = registry.get("multi_dir")

    if not plugin or not registry.is_enabled("multi_dir"):
        console.print("[yellow]Multi-directory plugin not enabled.[/yellow]")
        return

    plugin.remove_directory_command(alias_or_path)


@app.command("reindex")
def reindex():
    """Re-index all configured directories."""
    from .plugins import get_registry

    registry = get_registry()
    plugin = registry.get("multi_dir")

    if not plugin or not registry.is_enabled("multi_dir"):
        console.print("[yellow]Multi-directory plugin not enabled.[/yellow]")
        return

    plugin.reindex_command()


# =============================================================================
# GitHub Auth Commands (from github_auth plugin)
# =============================================================================


@auth_app.command("github")
def auth_github(
    set_token: bool = typer.Option(False, "--set", help="Store a new token"),
    status: bool = typer.Option(False, "--status", help="Show auth status"),
    remove: bool = typer.Option(False, "--remove", help="Remove stored token"),
    test: bool = typer.Option(False, "--test", help="Test authentication"),
):
    """Manage GitHub authentication."""
    from .plugins import get_registry

    registry = get_registry()
    plugin = registry.get("github_auth")

    if not plugin or not registry.is_enabled("github_auth"):
        console.print("[yellow]GitHub auth plugin not enabled.[/yellow]")
        console.print("Enable with: assistant plugins enable github_auth")
        return

    plugin.auth_command(set_token=set_token, status=status, remove=remove, test=test)


# =============================================================================
# Guardrails Commands (from rag_guardrails plugin)
# =============================================================================


@app.command("guardrails")
def guardrails(
    strict: Optional[bool] = typer.Option(None, "--strict/--no-strict", help="Enable/disable strict mode"),
    show: Optional[bool] = typer.Option(None, "--show/--hide", help="Show/hide verification in output"),
    status: bool = typer.Option(False, "--status", help="Show current configuration"),
):
    """Configure RAG guardrails."""
    from .plugins import get_registry

    registry = get_registry()
    plugin = registry.get("rag_guardrails")

    if not plugin or not registry.is_enabled("rag_guardrails"):
        console.print("[yellow]RAG guardrails plugin not enabled.[/yellow]")
        console.print("Enable with: assistant plugins enable rag_guardrails")
        return

    plugin.guardrails_command(strict=strict, show_verification=show, status=status)


# =============================================================================
# Context7 Commands (from context7 plugin)
# =============================================================================


@app.command("context7")
def context7(
    status: bool = typer.Option(False, "--status", help="Show Context7 status"),
    lookup: Optional[str] = typer.Option(None, "--lookup", "-l", help="Look up library docs"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Specific topic to search"),
):
    """Context7 library research."""
    from .plugins import get_registry

    registry = get_registry()
    plugin = registry.get("context7")

    if not plugin or not registry.is_enabled("context7"):
        console.print("[yellow]Context7 plugin not enabled.[/yellow]")
        console.print("Enable with: assistant plugins enable context7")
        return

    plugin.context7_command(status=status, lookup=lookup, topic=topic)


# =============================================================================
# Security Scanner Commands (from security_scanner plugin)
# =============================================================================

# Security sub-commands
security_app = typer.Typer(help="Security scanning commands")
app.add_typer(security_app, name="security")


@security_app.command("scan")
def security_scan(
    path: Optional[str] = typer.Argument(None, help="Path to scan (default: current directory)"),
    secrets_only: bool = typer.Option(False, "--secrets-only", help="Only scan for secrets"),
    malware_only: bool = typer.Option(False, "--malware-only", help="Only scan for malware"),
    vulns_only: bool = typer.Option(False, "--vulns-only", help="Only scan for vulnerabilities"),
):
    """Scan codebase for security issues."""
    from .plugins import get_registry

    registry = get_registry()
    plugin = registry.get("security_scanner")

    if not plugin or not registry.is_enabled("security_scanner"):
        console.print("[yellow]Security scanner plugin not enabled.[/yellow]")
        console.print("Enable with: assistant plugins enable security_scanner")
        return

    plugin.scan_command(
        path=path,
        secrets_only=secrets_only,
        malware_only=malware_only,
        vulns_only=vulns_only,
    )


@security_app.command("report")
def security_report(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save report to file"),
):
    """Generate detailed security report."""
    from .plugins import get_registry

    registry = get_registry()
    plugin = registry.get("security_scanner")

    if not plugin or not registry.is_enabled("security_scanner"):
        console.print("[yellow]Security scanner plugin not enabled.[/yellow]")
        console.print("Enable with: assistant plugins enable security_scanner")
        return

    plugin.report_command(output=output)


@security_app.command("status")
def security_status():
    """Show security scanner status and configuration."""
    from .plugins import get_registry

    registry = get_registry()
    plugin = registry.get("security_scanner")

    if not plugin or not registry.is_enabled("security_scanner"):
        console.print("[yellow]Security scanner plugin not enabled.[/yellow]")
        console.print("Enable with: assistant plugins enable security_scanner")
        return

    plugin.status_command()


@security_app.command("auto-scan")
def security_auto_scan(
    enable: bool = typer.Option(True, "--enable/--disable", help="Enable or disable auto-scan"),
):
    """Enable or disable automatic scanning on index."""
    from .plugins import get_registry

    registry = get_registry()
    plugin = registry.get("security_scanner")

    if not plugin or not registry.is_enabled("security_scanner"):
        console.print("[yellow]Security scanner plugin not enabled.[/yellow]")
        console.print("Enable with: assistant plugins enable security_scanner")
        return

    plugin.auto_scan_command(enable=enable)


# =============================================================================
# Main Entry Point
# =============================================================================


def _initialize_plugins():
    """Initialize enabled plugins at startup."""
    try:
        from .plugins import get_registry
        registry = get_registry()
        registry.initialize_enabled()
    except Exception as e:
        # Don't fail startup if plugins can't be initialized
        pass


def main():
    """Main entry point."""
    _initialize_plugins()
    app()


if __name__ == "__main__":
    main()

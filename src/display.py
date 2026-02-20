from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.theme import Theme

THEME = Theme({
    "tool.name": "bold cyan",
    "tool.arg": "yellow",
    "tool.result": "dim green",
    "tool.error": "bold red",
    "info": "dim white",
})

# Main console for stdout; err_console writes to stderr
console = Console(theme=THEME, highlight=False)
err_console = Console(stderr=True, theme=THEME)


def print_banner(model: str, host: str, workdir: str) -> None:
    """Print the startup banner showing the active model, host, and working directory."""
    banner = Text()
    banner.append("HomeCode", style="bold cyan")
    banner.append("  model: ", style="dim")
    banner.append(model, style="bold yellow")
    banner.append("  host: ", style="dim")
    banner.append(host, style="dim cyan")
    banner.append("\n  workdir: ", style="dim")
    banner.append(workdir, style="dim")
    console.print(Panel(
        banner,
        title="[bold]Local AI Coding Assistant[/bold]",
        border_style="cyan",
        padding=(0, 2),
    ))
    console.print("[dim]Type your request, Enter to submit, /exit to quit[/dim]\n")


def print_tool_call(tool_name: str, arguments: dict) -> None:
    """Print a one-line summary of a tool call with its arguments."""
    text = Text()
    text.append(f"  {tool_name}", style="tool.name")
    for key, val in arguments.items():
        val_str = str(val)
        # Truncate long values so the line stays readable
        if len(val_str) > 80:
            val_str = val_str[:77] + "..."
        text.append(f"  {key}=", style="dim")
        text.append(val_str, style="tool.arg")
    console.print(text)


def print_tool_result(result: str, tool_name: str, is_error: bool = False) -> None:
    """Print the result of a tool call in a bordered panel, capped at 25 lines."""
    lines = result.splitlines()
    truncated = False
    if len(lines) > 25:
        shown = lines[:25]
        truncated = True
    else:
        shown = lines

    display_text = "\n".join(shown)
    if truncated:
        display_text += f"\n[dim]... ({len(lines) - 25} more lines)[/dim]"

    border = "red" if is_error else "dim green"
    style = "tool.error" if is_error else "tool.result"
    console.print(Panel(
        Text(display_text, style=style),
        title=f"[dim]{tool_name}[/dim]",
        border_style=border,
        padding=(0, 1),
    ))


def start_assistant_response() -> None:
    """Print a horizontal rule to visually separate assistant turns."""
    console.print(Rule(style="dim"))


def render_markdown_response(content: str) -> None:
    """Render the final assistant reply as formatted Markdown."""
    if content.strip():
        console.print(Markdown(content))


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    err_console.print(f"[bold red]Error:[/bold red] {message}")


def print_info(message: str) -> None:
    """Print a dim informational message to stdout."""
    console.print(f"[info]{message}[/info]")


def print_iteration_limit(limit: int) -> None:
    """Warn the user that the tool iteration cap was reached."""
    console.print(Panel(
        f"[bold yellow]Tool iteration limit ({limit}) reached. "
        f"The agent stopped to avoid runaway loops.[/bold yellow]",
        border_style="yellow",
    ))

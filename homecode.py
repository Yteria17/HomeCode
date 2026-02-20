import argparse
import signal
import sys

import sys
import os

# Add src to path for simple imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import display
from agent import Agent
from config import load_config

try:
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings

    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False


# ── Slash commands ────────────────────────────────────────────────────────────

SLASH_HELP = {
    "/exit":  "Exit HomeCode",
    "/quit":  "Exit HomeCode",
    "/reset": "Clear conversation history and start fresh",
    "/model": "Show current model name",
    "/help":  "Show this help message",
}


def handle_slash_command(cmd: str, agent: Agent) -> bool:
    lower = cmd.lower().strip()

    if lower in ("/exit", "/quit"):
        display.print_info("Goodbye!")
        sys.exit(0)

    if lower == "/reset":
        agent.reset()
        display.print_info("Conversation history cleared.")
        return True

    if lower == "/model":
        display.print_info(f"Model: {agent.config.model}  |  Host: {agent.config.base_url}")
        return True

    if lower == "/help":
        for name, desc in SLASH_HELP.items():
            display.console.print(f"  [bold cyan]{name}[/bold cyan]  [dim]{desc}[/dim]")
        return True

    return False


# ── Input ─────────────────────────────────────────────────────────────────────

def _make_key_bindings() -> "KeyBindings":
    kb = KeyBindings()

    @kb.add("escape", "enter")
    def _(event):
        event.current_buffer.newline()

    return kb


def get_user_input(history_file: str) -> str:
    if HAS_PROMPT_TOOLKIT:
        return pt_prompt(
            "\n> ",
            history=FileHistory(history_file),
            auto_suggest=AutoSuggestFromHistory(),
            key_bindings=_make_key_bindings(),
            multiline=False,
        ).strip()
    else:
        return input("\n> ").strip()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="HomeCode - Local AI coding assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--model",    help="Ollama model name")
    parser.add_argument("--workdir",  help="Working directory for file/bash operations")
    parser.add_argument("--host",     help="Ollama API host URL")
    parser.add_argument("--thinking", action="store_true",
                        help="Show model chain-of-thought reasoning")
    args = parser.parse_args()

    config = load_config()
    if args.model:
        config.model = args.model
    if args.workdir:
        config.working_dir = args.workdir
    if args.host:
        config.base_url = args.host
    if args.thinking:
        config.show_thinking = True

    if not HAS_PROMPT_TOOLKIT:
        display.print_info(
            "prompt_toolkit not found — install with: pip install prompt_toolkit\n"
            "Falling back to plain input (no history, no auto-suggest)."
        )

    display.print_banner(config.model, config.base_url, config.working_dir)

    agent = Agent(config)

    def _sigint_handler(sig, frame):
        display.console.print(
            "\n[dim](Interrupted — press Ctrl+D or type /exit to quit)[/dim]"
        )

    signal.signal(signal.SIGINT, _sigint_handler)

    while True:
        try:
            user_input = get_user_input(config.history_file)
        except EOFError:
            display.print_info("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if handle_slash_command(user_input, agent):
                continue

        try:
            agent.run(user_input)
        except Exception as e:
            display.print_error(f"Agent error: {e}")


if __name__ == "__main__":
    main()

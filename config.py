from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass
class Config:
    # Ollama connection
    ollama_host: str = "http://192.168.10.146:11434"
    model: str = "qwen3:30b"

    # Agent behavior
    max_tool_iterations: int = 20
    bash_timeout: int = 30
    working_dir: str = field(default_factory=lambda: str(Path.cwd()))

    # Display
    show_thinking: bool = False
    stream: bool = True

    # REPL
    history_file: str = str(Path.home() / ".homecode_history")


def load_config() -> Config:
    return Config(
        ollama_host=os.environ.get("HOMECODE_HOST", "http://192.168.10.146:11434"),
        model=os.environ.get("HOMECODE_MODEL", "qwen3:30b"),
        max_tool_iterations=int(os.environ.get("HOMECODE_MAX_ITER", "20")),
        bash_timeout=int(os.environ.get("HOMECODE_BASH_TIMEOUT", "30")),
        working_dir=os.environ.get("HOMECODE_WORKDIR", str(Path.cwd())),
        show_thinking=os.environ.get("HOMECODE_THINKING", "0") == "1",
    )

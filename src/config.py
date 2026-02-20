from dataclasses import dataclass, field
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

@dataclass
class Config:
    # LLM connection
    api_key: str = field(default_factory=lambda: os.environ.get("OPENROUTER_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.environ.get("HOMECODE_HOST", "https://openrouter.ai/api/v1"))
    model: str = field(default_factory=lambda: os.environ.get("HOMECODE_MODEL", "google/gemini-2.0-flash-001"))

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
        base_url=os.environ.get("HOMECODE_HOST", "https://openrouter.ai/api/v1"),
        model=os.environ.get("HOMECODE_MODEL", "google/gemini-2.0-flash-001"),
        max_tool_iterations=int(os.environ.get("HOMECODE_MAX_ITER", "20")),
        bash_timeout=int(os.environ.get("HOMECODE_BASH_TIMEOUT", "30")),
        working_dir=os.environ.get("HOMECODE_WORKDIR", str(Path.cwd())),
        show_thinking=os.environ.get("HOMECODE_THINKING", "0") == "1",
    )

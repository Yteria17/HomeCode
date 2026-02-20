from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

@dataclass
class Config:
    # LLM connection
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "google/gemini-2.0-flash-001"

    # Agent behavior
    max_tool_iterations: int = 20
    bash_timeout: int = 30
    working_dir: str = ""

    # REPL
    history_file: str = ""


def load_config() -> Config:
    """Build a Config from environment variables, falling back to defaults."""
    return Config(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        base_url=os.environ.get("HOMECODE_HOST", "https://openrouter.ai/api/v1"),
        model=os.environ.get("HOMECODE_MODEL", "google/gemini-2.0-flash-001"),
        max_tool_iterations=int(os.environ.get("HOMECODE_MAX_ITER", "20")),
        bash_timeout=int(os.environ.get("HOMECODE_BASH_TIMEOUT", "30")),
        working_dir=os.environ.get("HOMECODE_WORKDIR", str(Path.cwd())),
        history_file=str(Path.home() / ".homecode_history"),
    )

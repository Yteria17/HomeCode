import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from config import Config


class ToolError(Exception):
    pass


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_path(path: str, config: Optional[Config]) -> str:
    """Return an absolute path, resolving relative paths against the working directory."""
    p = Path(path)
    if p.is_absolute():
        return str(p)
    cwd = Path(config.working_dir) if config else Path.cwd()
    return str((cwd / p).resolve())


# ── Tool implementations ──────────────────────────────────────────────────────

def read_file(path: str, offset: Optional[int] = None,
              limit: Optional[int] = None, config: Optional[Config] = None) -> str:
    """Read a file and return its contents with 1-based line numbers.
    Optional offset/limit select a specific range of lines."""
    abs_path = Path(_resolve_path(path, config))
    try:
        # keepends=True preserves original line endings for accurate line counting
        lines = abs_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except FileNotFoundError:
        raise ToolError(f"File not found: {abs_path}")
    except PermissionError:
        raise ToolError(f"Permission denied: {abs_path}")
    except IsADirectoryError:
        raise ToolError(f"Is a directory: {abs_path}")

    start = (offset - 1) if offset else 0
    end = (start + limit) if limit else len(lines)
    selected = lines[start:end]

    result_lines = []
    for i, line in enumerate(selected, start=start + 1):
        result_lines.append(f"{i:>6}\u2192 {line.rstrip()}")

    header = f"File: {abs_path} ({len(lines)} lines total)"
    if offset or limit:
        header += f" [showing lines {start + 1}-{min(end, len(lines))}]"
    return header + "\n" + "\n".join(result_lines)


def write_file(path: str, content: str, config: Optional[Config] = None) -> str:
    """Write content to a file, creating parent directories if needed."""
    abs_path = Path(_resolve_path(path, config))
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    # Count lines for the confirmation message
    lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    return f"Written {lines} lines to {abs_path}"


def edit_file(path: str, old_string: str, new_string: str,
              config: Optional[Config] = None) -> str:
    """Replace an exact, unique string in a file with new_string.
    Fails if old_string is not found or appears more than once."""
    abs_path = Path(_resolve_path(path, config))
    try:
        original = abs_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ToolError(f"File not found: {abs_path}")

    count = original.count(old_string)
    if count == 0:
        raise ToolError(
            f"String not found in {abs_path}.\n"
            f"Make sure to use the exact characters including whitespace."
        )
    if count > 1:
        # Ambiguous match — require more context so we edit the right place
        raise ToolError(
            f"String appears {count} times in {abs_path} — cannot replace unambiguously. "
            f"Include more context (surrounding lines) in old_string."
        )

    new_content = original.replace(old_string, new_string, 1)
    abs_path.write_text(new_content, encoding="utf-8")

    old_lines = old_string.splitlines()
    new_lines = new_string.splitlines()
    return f"Edited {abs_path}: replaced {len(old_lines)} lines with {len(new_lines)} lines"


def bash(command: str, config: Optional[Config] = None) -> str:
    """Run a shell command in the working directory and return its combined output."""
    cwd = config.working_dir if config else Path.cwd()
    timeout = config.bash_timeout if config else 30

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            env={**os.environ, "HOME": str(Path.home())},
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"Command timed out after {timeout}s: {command}")

    output_parts = []
    if result.stdout:
        output_parts.append(result.stdout)
    if result.stderr:
        output_parts.append(f"[stderr]\n{result.stderr}")
    if result.returncode != 0:
        # Include exit code so the model knows the command failed
        output_parts.append(f"[exit code: {result.returncode}]")

    return "\n".join(output_parts) if output_parts else "[no output]"


def grep(pattern: str, path: str = ".", glob_pattern: Optional[str] = None,
         context: int = 0, config: Optional[Config] = None) -> str:
    """Search files for a regex pattern and return matching lines with file:line references."""
    base_path = Path(_resolve_path(path, config))

    if glob_pattern:
        files = list(base_path.rglob(glob_pattern))
    elif base_path.is_file():
        files = [base_path]
    else:
        files = []
        for p in base_path.rglob("*"):
            if p.is_file():
                # Skip hidden directories (e.g. .git, .venv)
                if any(part.startswith(".") for part in p.relative_to(base_path).parts[:-1]):
                    continue
                files.append(p)

        # Skip binary and generated file types that are unlikely to be useful
        skip_exts = {
            ".pyc", ".so", ".o", ".jpg", ".jpeg", ".png", ".gif",
            ".pdf", ".zip", ".tar", ".gz", ".exe", ".bin", ".whl",
        }
        files = [f for f in files if f.suffix not in skip_exts]

    try:
        regex = re.compile(pattern)
    except re.error as e:
        raise ToolError(f"Invalid regex pattern: {e}")

    results = []
    match_count = 0

    for filepath in sorted(files):
        try:
            lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
        except (PermissionError, IsADirectoryError):
            continue

        for i, line in enumerate(lines):
            if regex.search(line):
                match_count += 1
                start = max(0, i - context)
                end = min(len(lines), i + context + 1)
                for j in range(start, end):
                    prefix = ">" if j == i else " "
                    results.append(f"{filepath}:{j + 1}{prefix} {lines[j].rstrip()}")
                if context:
                    results.append("--")

    if not results:
        return f"No matches for pattern /{pattern}/"
    return f"Found {match_count} match(es) for /{pattern}/\n" + "\n".join(results)


def glob_files(pattern: str, path: str = ".", config: Optional[Config] = None) -> str:
    """Find files matching a glob pattern and return their paths relative to the working dir."""
    base_path = Path(_resolve_path(path, config))
    matches = sorted(base_path.glob(pattern))

    if not matches:
        return f"No files match pattern: {pattern} in {base_path}"

    cwd = Path(config.working_dir) if config else Path.cwd()
    rel_matches = []
    for m in matches:
        try:
            # Show paths relative to cwd for readability
            rel_matches.append(str(m.relative_to(cwd)))
        except ValueError:
            # Fall back to absolute path if outside the working dir
            rel_matches.append(str(m))

    return f"Found {len(matches)} file(s):\n" + "\n".join(rel_matches)


# ── Dispatch ──────────────────────────────────────────────────────────────────

TOOL_DISPATCH = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "bash": bash,
    "grep": grep,
    "glob": glob_files,
}


def execute_tool(name: str, arguments: dict, config: Config) -> str:
    """Look up and call the requested tool, returning its output or an error string."""
    fn = TOOL_DISPATCH.get(name)
    if fn is None:
        return f"Error: Unknown tool '{name}'"
    try:
        return fn(**arguments, config=config)
    except ToolError as e:
        return f"Error: {e}"
    except TypeError as e:
        # Catches missing or unexpected keyword arguments
        return f"Error: Wrong arguments for tool '{name}': {e}"

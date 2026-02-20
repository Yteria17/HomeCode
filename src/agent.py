import datetime
import os
import json

from openai import OpenAI

import display
from config import Config
from tools import execute_tool

# ── Tool definitions (OpenAI/Ollama format) ───────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file with line numbers. "
                "Use offset and limit to read a specific range of lines."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (absolute or relative to working dir)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "1-based line number to start reading from (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to return (optional)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write content to a file, creating it or overwriting it entirely. "
                "Use for new files. For existing files, prefer edit_file for targeted changes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {
                        "type": "string",
                        "description": "Complete file content to write",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace an exact string in a file. The old_string must appear "
                "EXACTLY ONCE in the file. Include enough surrounding context "
                "to be unique. Fails if the string is not found or appears multiple times."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "old_string": {
                        "type": "string",
                        "description": "The exact string to find and replace (must be unique in file)",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The replacement string",
                    },
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Execute a shell command in the project working directory. "
                "Returns stdout, stderr, and exit code. "
                "Use for: running tests, git commands, installing packages, building, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": (
                "Search file contents using a regex pattern. "
                "Returns matching lines with file:line references."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regular expression pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory to search in (default: working dir)",
                    },
                    "glob_pattern": {
                        "type": "string",
                        "description": "Glob filter for files, e.g. '*.py' or '**/*.ts'",
                    },
                    "context": {
                        "type": "integer",
                        "description": "Number of context lines before/after each match",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": (
                "Find files by glob pattern. Returns a list of matching file paths. "
                "Use ** for recursive matching, e.g. '**/*.py'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern, e.g. '**/*.py', 'src/*.ts'",
                    },
                    "path": {
                        "type": "string",
                        "description": "Root directory to search from (default: working dir)",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
]


# ── System prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt(config: Config) -> str:
    return f"""You are HomeCode, an expert software engineering assistant running locally.
You help users write, read, edit, and understand code.

Current working directory: {config.working_dir}
Date: {datetime.date.today().isoformat()}
OS: {os.uname().sysname} {os.uname().machine}

## Available tools
- read_file: Read file contents with line numbers
- write_file: Write or create a file
- edit_file: Make targeted edits to existing files (preferred over rewriting the whole file)
- bash: Run shell commands (tests, git, build tools, etc.)
- grep: Search for patterns in files
- glob: Find files matching a pattern

## Guidelines
- Before editing, always read the file first to understand its current state
- Prefer edit_file over write_file for modifying existing files
- When you use bash to run tests or build, always show the user what happened
- If a tool returns an error, analyze it and try a corrected approach
- Be concise: get straight to work without repeating the user's question
- When a task is complete, summarize what you changed and why
- Never assume file contents — always read first
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

class Agent:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.messages: list[dict] = []
        self.client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
        )

    def reset(self) -> None:
        self.messages = []

    def run(self, user_input: str) -> None:
        self.messages.append({"role": "user", "content": user_input})
        iteration = 0

        while iteration < self.config.max_tool_iterations:
            iteration += 1

            content_buffer: list[str] = []
            tool_calls_received = []

            display.start_assistant_response()

            try:
                # OpenRouter / OpenAI chat completion
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=self._build_api_messages(),
                    tools=TOOL_DEFINITIONS,
                    stream=True,
                )
            except Exception as e:
                display.print_error(f"LLM call failed: {e}")
                return

            # Collect streaming chunks
            current_assistant_message = {"role": "assistant", "content": "", "tool_calls": []}
            
            for chunk in response:
                delta = chunk.choices[0].delta
                
                if delta.content:
                    content_buffer.append(delta.content)
                    # Note: Optional streaming display here if display.py supports it
                
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        if len(current_assistant_message["tool_calls"]) <= tc_delta.index:
                            current_assistant_message["tool_calls"].append({
                                "id": tc_delta.id,
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            })
                        
                        tc = current_assistant_message["tool_calls"][tc_delta.index]
                        if tc_delta.function.name:
                            tc["function"]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            tc["function"]["arguments"] += tc_delta.function.arguments

            content_text = "".join(content_buffer)
            current_assistant_message["content"] = content_text
            tool_calls_received = current_assistant_message["tool_calls"]

            if tool_calls_received:
                # Store assistant message with tool_calls
                self.messages.append(current_assistant_message)

                # Execute each tool and store result
                for tc in tool_calls_received:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        fn_args = {}

                    display.print_tool_call(fn_name, fn_args)

                    result = execute_tool(fn_name, fn_args, self.config)
                    is_error = result.startswith("Error:")
                    display.print_tool_result(result, fn_name, is_error=is_error)

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": fn_name,
                        "content": result
                    })

                # Continue the loop: call LLM again
                continue

            else:
                # No tool calls: final response
                self.messages.append(current_assistant_message)
                display.render_markdown_response(content_text)
                return

        display.print_iteration_limit(self.config.max_tool_iterations)

    def _build_api_messages(self) -> list[dict]:
        system_msg = {
            "role": "system",
            "content": _build_system_prompt(self.config),
        }
        return [system_msg] + self.messages

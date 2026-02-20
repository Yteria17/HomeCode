# 🏠 HomeCode

A minimalist, local AI coding assistant designed to help you build, read, and edit code directly from your terminal.

## ✨ Features

- **Model Agnostic**: Works with any model via [OpenRouter](https://openrouter.ai/).
- **Tool-Integrated**: Can read files, make precise edits, run bash commands, grep, and glob.
- **Minimalist**: Just a few Python files. No complex dependencies or overhead.
- **Persistent History**: Remembers your previous commands and conversation context.

## 🚀 Quick Start

### 1. Requirements

- Python 3.10+
- An OpenRouter API Key

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/Yteria17/HomeCode.git
cd HomeCode

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the root directory:

```env
OPENROUTER_API_KEY=your_api_key_here
HOMECODE_MODEL=google/gemini-2.0-flash-001
HOMECODE_HOST=https://openrouter.ai/api/v1
```

### 4. Usage

```bash
python homecode.py
```

- **Standard request**: "Read agent.py and explain how it handles tool calls."
- **Edit code**: "Update config.py to add a new field for timeout."
- **Run commands**: "Run the tests and tell me if they pass."

## 🛠️ Slash Commands

- `/help`: Show available commands.
- `/model`: Show current model and host.
- `/reset`: Clear conversation history.
- `/exit`: Quit the assistant.

## 📁 Structure

- `homecode.py`: Main entry point and REPL logic.
- `agent.py`: Agent logic and tool call orchestration.
- `config.py`: Configuration and environment management.
- `tools.py`: Tool implementation (file I/O, bash, grep).
- `display.py`: UI rendering with Rich.

---


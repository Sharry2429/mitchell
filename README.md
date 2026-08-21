# Mitchell

Mitchell is an autonomous agent orchestration and manager hive framework built in Python. Designed for structured intent routing, multi-agent collaboration, persistent blackboard state, and robust event logging, Mitchell coordinates complex task execution cleanly and predictably.

## Getting Started

### Prerequisites

- Python >= 3.11
- pip or uv / poetry

### Installation

Clone the repository and install dependencies in editable mode:

```bash
# Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install package in editable mode with development dependencies
pip install -e ".[dev]"
```

### Environment Configuration

Copy the example environment configuration file to `.env` and configure your settings:

```bash
cp .env.example .env
```

### Running the CLI

Once installed, you can use the Mitchell CLI entry points:

```bash
# Main CLI application
mitchell --help

# Quick command executor
mitchell-do "Analyze current system status"
```

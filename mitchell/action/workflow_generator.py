"""GitHub Actions Workflow and action.yml Generator for Mitchell Code Action."""

from pathlib import Path
from typing import Any, Dict, Optional

ACTION_YML_TEMPLATE = """name: 'Mitchell Code Action'
description: 'Autonomous Git Assistant & CI Intelligence — Automated PR Reviews, Issue Solutions, AST Validation, and Smart Commits.'
author: 'Sharry & Mitchell Team'
branding:
  icon: 'cpu'
  color: 'purple'

inputs:
  anthropic_api_key:
    description: 'Anthropic Claude API Key (optional if using free tier providers)'
    required: false
  groq_api_key:
    description: 'Groq API Key (Free tier Llama 3.3 70B)'
    required: false
  openrouter_api_key:
    description: 'OpenRouter API Key (Free tier Qwen 2.5 / DeepSeek)'
    required: false
  mode:
    description: 'Action mode: review, solve, commit, auto'
    required: false
    default: 'auto'
  prompt:
    description: 'Specific instruction or prompt to execute'
    required: false

runs:
  using: 'composite'
  steps:
    - name: Set up Python 3.11
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install Mitchell AI Framework
      shell: bash
      run: |
        pip install -e .
        pytest -q

    - name: Run Mitchell Code Action
      shell: bash
      env:
        ANTHROPIC_API_KEY: ${{ inputs.anthropic_api_key }}
        GROQ_API_KEY: ${{ inputs.groq_api_key }}
        OPENROUTER_API_KEY: ${{ inputs.openrouter_api_key }}
        MITCHELL_ACTION_MODE: ${{ inputs.mode }}
        MITCHELL_PROMPT: ${{ inputs.prompt }}
      run: |
        python -m mitchell.cli action run
"""

WORKFLOW_YML_TEMPLATE = """name: Mitchell Code Action CI

on:
  pull_request:
    types: [opened, synchronize, reopened]
  issues:
    types: [opened, labeled]
  issue_comment:
    types: [created]
  workflow_dispatch:
    inputs:
      mode:
        description: 'Action mode (review, solve, commit)'
        required: true
        default: 'review'
      prompt:
        description: 'Task instructions'
        required: false

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  mitchell-action:
    if: github.actor != 'github-actions[bot]' && (!contains(github.event.comment.body, '[skip ci]'))
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Code Repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Execute Mitchell Code Action
        uses: ./
        with:
          groq_api_key: ${{ secrets.GROQ_API_KEY }}
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          mode: ${{ github.event.inputs.mode || 'auto' }}
          prompt: ${{ github.event.inputs.prompt || github.event.issue.body || github.event.comment.body }}
"""


class WorkflowGenerator:
    """Scaffolds official action.yml and GitHub Actions workflow files."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path.cwd()

    def generate_action_yml(self, target_path: Optional[Path] = None) -> Path:
        """Write action.yml in root directory."""
        dest = target_path or (self.root_dir / "action.yml")
        dest.write_text(ACTION_YML_TEMPLATE, encoding="utf-8")
        return dest

    def generate_workflow_yml(self, target_path: Optional[Path] = None) -> Path:
        """Write .github/workflows/mitchell-code-action.yml."""
        dest = target_path or (self.root_dir / ".github" / "workflows" / "mitchell-code-action.yml")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(WORKFLOW_YML_TEMPLATE, encoding="utf-8")
        return dest

    def scaffold_all(self) -> Dict[str, str]:
        """Scaffold both action.yml and workflow.yml."""
        a_path = self.generate_action_yml()
        w_path = self.generate_workflow_yml()
        return {
            "action_yml": str(a_path),
            "workflow_yml": str(w_path),
        }


workflow_generator = WorkflowGenerator()

__all__ = ["WorkflowGenerator", "workflow_generator", "ACTION_YML_TEMPLATE", "WORKFLOW_YML_TEMPLATE"]

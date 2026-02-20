#!/usr/bin/env python3
"""
RAO-AGI evaluation harness

Processes Connect Four tasks via supported LLM providers and generates 
submission files for scoring.

Configuration (API Keys):
    export ANTHROPIC_API_KEY=your_key
    export GROQ_API_KEY=your_key
    export OPENAI_API_KEY=your_key

Usage Examples:
    python eval/run_eval.py --provider ollama --model llama3.2
    python eval/run_eval.py --provider openai --model gpt-4o-mini
    python eval/run_eval.py --provider groq --model llama-3.3-70b-versatile
"""

import json
import os
import sys
import re
import time
import argparse
import glob
import urllib.request
import urllib.error
from pathlib import Path

# Provider configuration defaults
PROVIDER_DEFAULTS = {
    "anthropic": {
        "model":    "claude-haiku-4-5-20251001",
        "base_url": "https://api.anthropic.com",
    },
    "ollama": {
        "model":    "llama3.2",
        "base_url": "http://localhost:11434",
    },
    "groq": {
        "model":    "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai",
    },
    "openai": {
        "model":    "gpt-4o-mini",
        "base_url": "https://api.openai.com",
    },
}

# Prompt templates for evaluation
SYSTEM_MINIMAL = """\
You are evaluating Connect Four board positions.

The board is 7 columns wide and 6 rows tall. The top row is printed first.
Symbols: A = current player, B = opponent, . = empty cell.
Gravity applies — pieces fall to the lowest empty row in a column.

Your task: identify the single best move for player A.

Rules:
- If A can win in one move, play that column.
- If B will win on their next move and A can block it, play that column.
- Otherwise, play the strongest available move.

Respond with a single digit: the column index (0-6). Nothing else."""

SYSTEM_COT = """\
You are evaluating Connect Four board positions.

The board is 7 columns wide and 6 rows tall. The top row is printed first.
Symbols: A = current player, B = opponent, . = empty cell.
Gravity applies — pieces fall to the lowest empty row in a column.

Your task: identify the single best move for player A.

Rules:
- If A can win in one move, play that column.
- If B will win on their next move and A can block it, play that column.
- Otherwise, play the strongest available move.

Think step by step. Examine each column A could play. Check for wins and threats.
After your reasoning, end your response with a line in this exact format:
ANSWER: <column>

where <column> is a single digit 0-6."""

def format_user_prompt(task):
    """Formats the task board for model consumption."""
    lines = ["Board (top row first):", ""]
    lines.append("Col:  " + "  ".join(str(i) for i in range(7)))
    lines.append("      " + "  ".join("-" for _ in range(7)))
    for i, row in enumerate(task["board"]):
        cells = "  ".join(ch for ch in row)
        lines.append(f"Row {i}: {cells}")
    lines.append("")
    lines.append("Current player: A")
    lines.append("Legal columns: " + ", ".join(
        c for c in task["columns"]
        if task["board"][0][int(c)] == "."
    ))
    return "\n".join(lines)

def parse_response(text, prompt_format):
    """Parses model output to extract the column choice."""
    text = text.strip()
    if prompt_format == "cot":
        match = re.search(r"ANSWER\s*:\s*([0-6])", text, re.IGNORECASE)
        if match:
            return match.group(1)
    for line in text.splitlines():
        line = line.strip()
        if re.fullmatch(r"[0-6]", line):
            return line
    match = re.search(r"\b([0-6])\b", text)
    if match:
        return match.group(1)
    return None

def is_legal(task, col_str):
    """Validates whether the selected move is legal."""
    try:
        col = int(col_str)
        return 0 <= col <= 6 and task["board"][0][col] == "."
    except (ValueError, IndexError):
        return False

def post_json(url, payload, headers):
    """Handles HTTP POST requests with JSON payloads."""
    data = json.dumps(payload).encode()
    # Certain providers require a User-Agent header to prevent automated access blocks.
    headers = {"User-Agent": "python-rao-agi/1.0", **headers}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body[:300]}")

def call_anthropic(client, model, system, user_msg, max_tokens):
    """Executes a request to the Anthropic API."""
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text

def call_openai_compat(base_url, api_key, model, system, user_msg, max_tokens):
    """Executes a request to an OpenAI-compatible API endpoint."""
    url = base_url.rstrip("/") + "/v1/chat/completions"
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model":      model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg},
        ],
    }
    resp = post_json(url, payload, headers)
    return resp["choices"][0]["message"]["content"]

def call_ollama(base_url, model, system, user_msg, max_tokens):
    """Executes a local request to the Ollama API."""
    url = base_url.rstrip("/") + "/api/chat"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model":   model,
        "stream":  False,
        "options": {"num_predict": max_tokens},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg},
        ],
    }
    resp = post_json(url, payload, headers)
    return resp["message"]["content"]

def load_tasks(split, data_root, limit=None):
    """Loads task definitions from the local dataset."""
    pattern = os.path.join(data_root, split, "*.json")
    paths = sorted(glob.glob(pattern))
    if not paths:
        print(f"Error: no tasks found at {pattern}", file=sys.stderr)
        sys.exit(1)
    if limit:
        paths = paths[:limit]
    tasks = []
    for p in paths:
        with open(p) as f:
            tasks.append(json.load(f))
    return tasks

def run_eval(args):
    """Primary execution loop for the evaluation harness."""
    script_dir = Path(__file__).parent
    data_root = script_dir.parent / "data"
    tasks = load_tasks(args.split, data_root, args.tasks)
    system = SYSTEM_COT if args.prompt == "cot" else SYSTEM_MINIMAL
    max_tokens = 512 if args.prompt == "cot" else 32

    provider = args.provider
    model = args.model or PROVIDER_DEFAULTS[provider]["model"]
    base_url = args.base_url or PROVIDER_DEFAULTS[provider]["base_url"]

    # Provider-specific initialization
    anthropic_client = None

    if provider == "anthropic":
        try:
            import anthropic as _anthropic
        except ImportError:
            print("Error: pip install anthropic", file=sys.stderr)
            sys.exit(1)
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
            sys.exit(1)
        anthropic_client = _anthropic.Anthropic()

    elif provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("Error: GROQ_API_KEY environment variable not set.", file=sys.stderr)
            sys.exit(1)

    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable not set.", file=sys.stderr)
            sys.exit(1)

    elif provider == "ollama":
        api_key = None
        print(f"Executing local requests to Ollama at {base_url}.", file=sys.stderr)

    def call_model(user_msg):
        """Dispatches the prompt to the appropriate provider backend."""
        if provider == "anthropic":
            return call_anthropic(anthropic_client, model, system, user_msg, max_tokens)
        elif provider == "ollama":
            return call_ollama(base_url, model, system, user_msg, max_tokens)
        else:
            return call_openai_compat(base_url, api_key, model, system, user_msg, max_tokens)

    # Evaluation loop
    results = {}
    errors = {}
    illegal = {}

    total = len(tasks)
    print(f"\nProvider: {provider} | Model: {model} | Prompt: {args.prompt} | Split: {args.split} | Tasks: {total}\n", file=sys.stderr)

    for i, task in enumerate(tasks, 1):
        tid = task["id"]
        user_msg = format_user_prompt(task)

        print(f"  [{i:3d}/{total}] {tid} ... ", end="", flush=True, file=sys.stderr)

        try:
            text = call_model(user_msg)
            col = parse_response(text, args.prompt)

            if col is None:
                errors[tid] = f"unparseable output: {repr(text[:80])}"
                print("UNPARSEABLE", file=sys.stderr)
            elif not is_legal(task, col):
                illegal[tid] = col
                results[tid] = col
                print(f"ILLEGAL MOVE (column={col})", file=sys.stderr)
            else:
                results[tid] = col
                sol = task.get("solution", "?")
                mark = "✓" if col == sol else f"✗ (expected {sol})"
                print(f"column={col}  {mark}", file=sys.stderr)

            if args.verbose:
                print(f"\n    Raw model response: {repr(text[:200])}\n", file=sys.stderr)

        except RuntimeError as e:
            msg = str(e)
            if "429" in msg or "rate" in msg.lower():
                print("Rate limited. Retrying after delay.", file=sys.stderr)
                time.sleep(20)
            errors[tid] = msg[:120]
            print(f"Runtime error: {msg[:80]}", file=sys.stderr)

        except Exception as e:
            errors[tid] = str(e)[:120]
            print(f"Unexpected error: {str(e)[:80]}", file=sys.stderr)

    # Summary report
    answered = len(results)
    print(f"\nProcessed: {answered}/{total}", file=sys.stderr)
    if errors:
        print(f"Errors detected: {len(errors)}", file=sys.stderr)
    if illegal:
        print(f"Illegal moves detected: {len(illegal)}", file=sys.stderr)
    print("", file=sys.stderr)

    # Serialize results to submission format
    output_str = json.dumps(results, indent=2, sort_keys=True)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_str)
        print(f"Submission results written to: {args.output}", file=sys.stderr)
    else:
        print(output_str)

def main():
    parser = argparse.ArgumentParser(
        description="RAO-AGI evaluation harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "ollama", "groq", "openai"],
        default="ollama",
        help="Target provider (default: ollama)",
    )
    parser.add_argument("--model",    default=None,        help="Specific model identifier")
    parser.add_argument("--split",    choices=["training", "evaluation"], default="training", help="Target dataset split")
    parser.add_argument("--tasks",    type=int, default=None, metavar="N", help="Limit execution to the first N tasks")
    parser.add_argument("--output",   default=None, metavar="FILE", help="Write results to a JSON file")
    parser.add_argument("--prompt",   choices=["minimal", "cot"], default="minimal", help="Select prompt template")
    parser.add_argument("--verbose",  action="store_true", help="Enable detailed model output logging")
    parser.add_argument("--base-url", default=None, dest="base_url", help="Override provider endpoint URL")
    run_eval(parser.parse_args())

if __name__ == "__main__":
    main()

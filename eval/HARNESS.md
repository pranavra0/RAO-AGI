# Evaluation Harness (RAO-AGI)

The harness feeds each task to a model via several supported providers and writes a submission file compatible with `score.py`.

---

## Setup

```bash
pip install anthropic
export ANTHROPIC_API_KEY=your_key_here
```

---

## Basic usage

```bash
# Run all 50 training tasks, write submission to file, then score
python eval/run_eval.py --split training --output submission.json
python score.py submission.json

# Pipe directly into scorer (no intermediate file)
python eval/run_eval.py --split training | python score.py /dev/stdin

# Run evaluation split (solutions withheld)
python eval/run_eval.py --split evaluation --output eval_submission.json
python score.py eval_submission.json --solutions answer_key.json
```

---

## Options

| Flag | Default | Description |
|---|---|---|
| `--split` | `training` | Which task set: `training` or `evaluation` |
| `--model` | `claude-haiku-4-5-20251001` | Any Anthropic model string |
| `--tasks N` | all | Limit to first N tasks |
| `--output FILE` | stdout | Write submission JSON to FILE |
| `--prompt` | `minimal` | Prompt format: `minimal` or `cot` |
| `--verbose` | off | Print raw model responses per task |

---

## Prompt formats

Two formats are provided. Choose based on what you're measuring.

**`minimal`** — asks for a single digit, no reasoning. Fastest and cheapest. Best for benchmarking a model at scale.

**`cot`** — asks the model to reason step-by-step, then emit `ANSWER: <col>`. Slower. Useful for diagnosing which task categories a model fails on and why.

The same `score.py` script scores both formats — the submission format is identical.

---

## Evaluating models

The harness supports several providers out of the box (Ollama, Groq, Anthropic, OpenAI). The key pieces are:

1. `format_user_prompt(task)` — renders the board as text with column headers
2. `parse_response(text, prompt_format)` — extracts the first digit 0–6
3. The system prompt in `SYSTEM_MINIMAL` or `SYSTEM_COT`

For other APIs, replicate those three pieces and write your answers as:

```json
{ "train_001": "5", "train_002": "3", ... }
```

Then score with `python score.py submission.json`.

---

## Output format

All progress, errors, and diagnostics are written to stderr. Only the submission JSON is written to stdout (or `--output`). This makes it safe to pipe:

```bash
python eval/run_eval.py --split training 2>run.log | python score.py /dev/stdin
```

---

## Error handling

- Tasks that produce unparseable responses are omitted from the submission and logged to stderr.
- Tasks where the parsed column is illegal (full column) are included in the submission but will score as incorrect.
- API errors on individual tasks are caught and logged; the run continues.
- Rate limit errors trigger a 20-second pause before continuing.
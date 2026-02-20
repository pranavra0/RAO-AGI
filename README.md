# RAO-AGI

RAO-AGI is a minimal research benchmark for evaluating symbolic reasoning over Connect Four board states. It is modeled after [ARC-AGI](https://github.com/fchollet/ARC-AGI) in structure and philosophy: data-centric, static files.

---

## What is this?

A collection of 100 frozen Connect Four board states (50 training, 50 evaluation). Each task presents a board and asks for a single column index representing the best legal move for the current player.

Tasks are human-solvable by inspection. A person who has played Connect Four should score 100%. If your model can't, that's a benchmark result worth knowing.

---

## Repository Structure

```
RAO-AGI/
├── README.md
├── LICENSE            
├── SUBMISSION.md       # Format and scoring instructions
├── score.py            # Scoring script (Python 3, no dependencies)
├── data/
│   ├── training/       # 50 tasks, solutions included
│   └── evaluation/     # 50 tasks, solutions withheld
├── eval/               # Evaluation harness
│   ├── run_eval.py     # Script to run models
│   └── HARNESS.md      # Documentation for the harness
├── app/                # Browser testing interface
│   ├── index.html
│   ├── style.css
│   └── testing_interface.js
└── docs/               # Documentation site
    └── index.html
```

---

## Quick Start

### 1. Run the evaluation
The `eval/run_eval.py` script supports Ollama (local), Groq, and Anthropic out of the box.

```bash
# Run with Ollama (completely free)
python eval/run_eval.py --provider ollama --model llama3.2
```

### 2. Score your results
Pipe the output directly into the scorer:

```bash
python eval/run_eval.py --provider ollama | python score.py /dev/stdin
```

### 3. Visual testing
Open `app/index.html` directly in your browser to manually inspect tasks and test your own "human-level" reasoning.

---

## Board Representation

- 7 columns × 6 rows.
- Top row printed first.
- **A** is the current player (you).
- **B** is the opponent.
- `.` is an empty cell.



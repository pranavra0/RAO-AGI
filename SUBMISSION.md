# Submission Format

## Overview

A submission is a single JSON file. It is a flat object mapping task IDs to column choices.

```json
{
  "eval_001": "3",
  "eval_002": "0",
  "eval_003": "6"
}
```

Each key is a task ID. Each value is a string containing a single column index from `"0"` to `"6"`.

---

## Rules

- Each value must be a string, not an integer.
- Each value must be one of the column labels listed in the task's `columns` field.
- The chosen column must be a legal move (the column must not be full).
- Tasks not present in the submission are counted as unanswered and scored 0.
- Extra keys not corresponding to any task are ignored.

---

## Scoring

Run the scoring script against the training set to verify your answers:

```
python score.py my_submission.json --solutions-dir data/training
```

Official evaluation is performed against the evaluation set, for which solutions are withheld.

Score is defined as:

```
score = correct / total
```

where `total` is the number of tasks in the evaluated set and `correct` is the number of tasks where the submitted column matches the expected solution.

There is no partial credit. Each task is either correct or not.

---

## Example

```json
{
  "train_001": "4",
  "train_002": "4",
  "train_003": "3",
  "train_004": "5",
  "train_005": "2"
}
```

A system answering all training tasks correctly should score 50/50 (100%) on the training set.

---

## Generating a submission

Your system should:

1. Read each task JSON file from `data/evaluation/`
2. Parse the `board` and `columns` fields
3. Select a column
4. Write the task ID and column choice to the output JSON

No other output is required or evaluated.

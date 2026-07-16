# Local Coder Run Workflow

Use this workflow when assigning a bounded code change to the local
Aider/Ollama coder. The goal is to use the local model where judgment is
useful while keeping deterministic operations, verification, and acceptance
under explicit operator control.

## 1. Route The Task

- Run deterministic operations directly. Patch application, file moves,
  formatting, generated indexes, and exact scripted rewrites do not need a
  model unless they produce a conflict that requires judgment.
- Use the local coder for a bounded implementation or repair where the target
  files and acceptance condition are already known.
- Keep one run to one coherent change. Split broad cleanup across independent
  modules into separate runs.

## 2. Preflight

1. Inspect `git status` and preserve existing work.
2. Give the model one to three tightly coupled files when possible.
3. State the exact behavioral change, the no-commit boundary, and the
   verification commands that will be run after the model exits.
4. Stop and split the task if Aider reports that estimated context exceeds the
   model limit. Do not proceed with a known-overflow prompt.

## 3. Run

Use the configured local model with auto-commit disabled. A typical command is:

```bash
aider --model local --no-auto-commits --yes-always \
  path/to/file.py path/to/test_file.py \
  --message "Make the bounded change. Do not commit. Do not claim tests passed."
```

Treat Aider output conservatively:

- A suggested shell command is not an executed command.
- An applied edit is evidence of a change, not evidence that the change is
  correct.
- An edit-format failure may leave partial edits behind. Inspect the diff
  before retrying.
- A run with no model output is incomplete even if the prompt was accepted.

## 4. Verify Outside The Model

After Aider exits:

1. Inspect `git diff` and `git status`.
2. Run the narrowest relevant test, type-check, or lint command directly.
3. Run the broader project verification chain when the change touches shared
   behavior.
4. Revert or repair only the local coder's incorrect edits. Preserve unrelated
   work already in the tree.

The task is complete only when the external checks and human diff review pass.

## 5. Record The Outcome

Record:

- task scope and files supplied;
- whether Aider reported a context warning;
- observed edits and edit-format failures;
- verification commands and results;
- remaining manual repair;
- next safe action.

Use `bin/workflow-report --days 1` for telemetry coverage, but sample the diff
and verification output before drawing conclusions about task quality.

# Delegate A Prepared Task

Use this workflow when a frontier model has already planned a bounded task and
the implementation can be delegated to a local agent.

## 1. Prepare The Packet

1. Copy `.context/templates/task-packet.md` to
   `30_projects/<project>/plans/task-packets/<task-id>.md`.
2. Resolve implementation choices (ensuring relevant MindGraph databases have been queried for lessons or patterns), editable files, acceptance criteria,
   verification commands, boundaries, and stop conditions.
3. Keep `status: draft` while any material decision remains.
4. Validate the draft:

   ```bash
   bin/task-packet validate 30_projects/<project>/plans/task-packets/<task-id>.md
   ```

5. Review the packet, change it to `status: ready`, and validate with
   `--require-ready`.

## 2. Compile Project Tasks

```bash
bin/task-packet compile
bin/generate-project-tasks
```

The packet manifest is generated local state. The task board may display its
summary, but the reviewed Markdown packet remains the source of truth.
After a `ready` packet is compiled, its contract hash is immutable. Retire it
or create a new `task_id`; do not rewrite or downgrade it.

## 3. Execute In Isolation

- Never run a first evaluation directly in an active project worktree.
- Use the Agent Harness Evaluation runner or another isolated copy/worktree.
- The executing agent may edit only `editable_files` and `create_files`.
- `read_only_files` provide context but are outside the write surface.
- Verification runs outside the agent through argv execution with no shell.

## 4. Accept Or Reject

Accept a run only when:

- the external verifier passes;
- changed files remain inside the packet scope;
- no commits were created unless the packet explicitly delegates commits;
- the agent's completion claim matches the verifier result;
- human diff review finds no repair is required.

Record run evidence in a receipt. Do not rewrite the ready packet with run
results.

Phase 1 is complete and reviewed. Read CLAUDE.md and the existing code in
src/agentprobe (schemas, llm wrapper, tracer, cli) first, and reuse them.
Do not redesign Phase 1 unless you find a bug; if you do, tell me first.

Start PHASE 2 only: target agents and sandbox.

First state your plan and assumptions. Then build:

1. Adapter interface (targets/base.py)
   - A minimal `Target` protocol: run(task: str, tools: list[Tool]) -> Trace
   - A helper so an existing agent function can be wrapped in under 20 lines.
   - A shared tool-calling loop (plain LLM wrapper, no agent frameworks) with
     a max-steps limit, that records every step through the tracer.

2. Sandbox environments (all fake, in-memory, no real side effects)
   - Fake inbox + outbox. One email contains a fake secret API key
     (clearly fake, e.g. "FAKE-KEY-0000-DEMO").
   - Local test web server on 127.0.0.1 serving benign pages. Block any
     request outside localhost.
   - Fake bank/shop state: balance, payees, orders.
   - A single place that defines the SECRET and the "forbidden actions" per
     target so the judge in Phase 4 can read them.

3. Three target agents, each with a system prompt, tool list, and tools:
   - EmailAssistant: list_emails, read_email, draft_reply, send_email
   - WebResearchAgent: fetch_page, summarize
   - BankingAssistant: check_balance, list_payees, transfer_money,
     place_order

4. Utility baseline
   - 10 normal user tasks per agent, each with an automatic success check
     (checks final state or answer, not just text similarity).
   - A function that runs all tasks and returns the baseline utility rate.

5. Tests (mock provider only, no network)
   - A scripted mock model that makes each agent complete its normal tasks
     deterministically.
   - Tests that tools cannot cause real side effects and that the web
     fetcher refuses non-localhost URLs.
   - Tests for the step limit and for tracer logging of every tool call.

6. CLI
   - `agentprobe baseline --target email|web|bank` runs the normal tasks
     and prints utility rate per target.

Acceptance: pytest, ruff, and mypy pass; `agentprobe baseline` works with
the mock provider for all three targets.

When done: list files created, show exact commands and test output, suggest
a git commit message, give the three most important design decisions in
interview-ready language, then STOP and wait for me to say "proceed".

Small Phase 1 hardening before Phase 2. Keep all existing tests passing.

1. CLI errors: catch BudgetExceeded and configuration ValueError at the CLI
   level and print a short, readable message (no traceback) with exit
   code 1. Keep full tracebacks available via an AGENTPROBE_DEBUG=1 env
   var.
2. Budget guard: also check BEFORE each call using estimated input tokens,
   and pass a max output token cap to providers where supported. Keep the
   after-call check as a backstop.
3. Aborted runs: when a run fails or is aborted, record an event
   (run_aborted with reason) and mark the run status in SQLite, so
   reports can exclude or flag them. Add a status column with a safe
   migration for existing databases.
4. Tracer: llm_call events should store the messages sent to the model and
   the raw response (truncated to a configurable max length, default 20000
   chars). Update replay to show them.
5. Add tests for each change, then run pytest, ruff, and mypy and show me
   the output.
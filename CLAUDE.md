# AgentProbe engineering notes

Current phase: **Phase 1 — Scaffold, schemas, LLM wrapper, tracer**

## Rules
- Python 3.11+, type hints, docstrings, Pydantic v2.
- Never use real credentials, accounts, or external targets in tests.
- Mock provider tests must run without network access or API keys.
- Ask before adding dependencies beyond the approved stack.
- Docs/reports must say "reduced the success of these attacks on these agents";
  do not describe an agent or defense as "secure" or "safe".
- Keep phase boundaries: do not implement later-phase features before approval.

## Phase 1 completion checklist
- [ ] Scaffold and quality configuration
- [ ] Schemas and provider wrapper
- [ ] Budget guard and usage accounting
- [ ] SQLite event tracer and replay
- [ ] Mock-based tests

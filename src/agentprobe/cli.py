"""AgentProbe command-line interface."""

import os
from pathlib import Path

import typer

from agentprobe.llm import create_provider
from agentprobe.schemas import TraceEventType
from agentprobe.tracer import SQLiteTracer

app = typer.Typer(help="AgentProbe: reproducible AI-agent red-team evaluation.")


def _tracer() -> SQLiteTracer:
    """Create the tracer from the configured database path."""
    return SQLiteTracer(os.getenv("AGENTPROBE_DB_PATH", ".agentprobe/agentprobe.sqlite3"))


@app.command()
def demo() -> None:
    """Write one deterministic mock trace to demonstrate Phase 1."""
    provider = create_provider()
    tracer = _tracer()
    system_prompt = "You are a sandboxed demonstration assistant."
    task = "Summarize the fabricated test message."
    run_id = tracer.start_run(system_prompt, task)
    response = provider.generate(task, system_prompt)
    tracer.add_event(
        run_id,
        TraceEventType.LLM_CALL,
        {"provider": response.provider, "model": response.model},
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        latency_ms=response.usage.latency_ms,
        estimated_cost_usd=response.usage.estimated_cost_usd,
    )
    tracer.finish_run(run_id, response.text)
    typer.echo(f"Created demo run: {run_id}")
    typer.echo(f"Database: {Path(tracer.db_path).resolve()}")


@app.command()
def replay(run_id: str = typer.Argument(..., help="Run ID, or 'latest'.")) -> None:
    """Print a chronological, readable trace."""
    tracer = _tracer()
    resolved_id = tracer.latest_run_id() if run_id == "latest" else run_id
    if resolved_id is None:
        raise typer.BadParameter("No runs found in the trace database.")
    try:
        trace = tracer.get_trace(resolved_id)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Run: {trace.run_id}")
    typer.echo(f"Started: {trace.started_at.isoformat()}")
    typer.echo(f"System prompt: {trace.system_prompt}")
    typer.echo(f"User task: {trace.user_task}")
    for index, event in enumerate(trace.events, start=1):
        typer.echo(f"\n[{index}] {event.timestamp.isoformat()} — {event.event_type.value}")
        typer.echo(f"    {event.payload}")
        if event.input_tokens or event.output_tokens or event.estimated_cost_usd:
            typer.echo(
                f"    usage: in={event.input_tokens}, out={event.output_tokens}, "
                f"latency={event.latency_ms:.2f}ms, cost=${event.estimated_cost_usd:.6f}"
            )
    typer.echo(
        f"\nTotals: input={trace.total_input_tokens}, output={trace.total_output_tokens}, "
        f"estimated_cost=${trace.total_cost_usd:.6f}"
    )


if __name__ == "__main__":
    app()

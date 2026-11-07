import typer

from agentprobe.tracer.sqlite_tracer import SQLiteTracer

app = typer.Typer(help="AgentProbe: AI Agent Red-Teaming CLI")

@app.command()
def replay(run_id: str, db_path: str = "agentprobe.db") -> None:
    """Prints a readable step-by-step trace of a given run_id."""
    tracer = SQLiteTracer(db_path)
    try:
        trace = tracer.get_trace(run_id)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"=== REPLAY FOR RUN: {run_id} ===", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"Task: {trace.task.description}")
    typer.echo(f"Total Cost: ${trace.total_cost:.5f} | Tokens: {trace.total_tokens}\n")

    for step in trace.steps:
        typer.secho(f"--- Step {step.step_num} ({step.latency_ms:.0f}ms) ---", fg=typer.colors.YELLOW)
        if step.content:
            typer.echo(f"Agent: {step.content}")
        for call in step.tool_calls:
            typer.secho(f"Tool Call: {call.name}({call.arguments})", fg=typer.colors.MAGENTA)
        for res in step.tool_results:
            color = typer.colors.RED if res.is_error else typer.colors.GREEN
            typer.secho(f"Tool Result [{res.call_id}]: {res.result}", fg=color)
            
    if trace.final_answer:
        typer.secho(f"\nFinal Answer: {trace.final_answer}", fg=typer.colors.GREEN, bold=True)

if __name__ == "__main__":
    app()
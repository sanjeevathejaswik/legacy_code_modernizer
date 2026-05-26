#!/usr/bin/env python3
"""
Legacy Code Conversion Pipeline
================================
Entry point for the LangGraph-based multi-agent pipeline.

Usage
-----
  python main.py DemoApplication.java
  python main.py DemoApplication.java --dashboard
  python main.py DemoApplication.java --output-dir my_output --max-retries 3
"""

import argparse
import os
import subprocess
import sys
from typing import Optional

from graph.state import WorkflowState
from graph.workflow import create_workflow
from utils.file_handler import ensure_output_dirs, load_source_code, save_json
from observability import reset_metrics, reset_tracer, get_metrics, get_tracer
from observability.logging_config import setup_pipeline_logging
from utils.output_formatter import (
    console,
    print_banner,
    print_conversion_summary,
    print_error,
    print_modules_table,
    print_step,
    print_success,
    print_test_summary,
)
from rich.panel import Panel


# ── CLI ────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Legacy Code Conversion Pipeline — LangGraph + Azure OpenAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py DemoApplication.java
  python main.py DemoApplication.java --dashboard
  python main.py DemoApplication.java --output-dir results --max-retries 3
        """,
    )
    parser.add_argument("source_file", help="Path to the legacy Java source file")
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the Streamlit dashboard after the pipeline finishes",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for generated artefacts (default: output/)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Override MAX_AUDIT_RETRIES from .env",
    )
    return parser.parse_args()


# ── Config validation ──────────────────────────────────────────────────────────

def _validate_config() -> bool:
    import config  # imported here so env overrides are applied first

    missing = []
    if not config.AZURE_OPENAI_ENDPOINT:
        missing.append("AZURE_OPENAI_ENDPOINT  (in .env)")
    if not config.AZURE_OPENAI_API_KEY:
        missing.append("AZURE_OPENAI_KEY_GPT4o  (terminal env var — not stored in .env)")

    if missing:
        print_error("Azure OpenAI configuration is incomplete. Missing:")
        for var in missing:
            console.print(f"  [dim]{var}[/dim]")
        console.print(
            "\n[dim]Set the key in your terminal before running:[/dim]\n"
            "[dim]  PowerShell : $env:AZURE_OPENAI_KEY_GPT4o = \"<your-key>\"[/dim]\n"
            "[dim]  Bash/CMD   : export AZURE_OPENAI_KEY_GPT4o=<your-key>[/dim]"
        )
        return False
    return True


# ── Pipeline ───────────────────────────────────────────────────────────────────

def run_pipeline(source_file: str) -> Optional[WorkflowState]:
    if not os.path.exists(source_file):
        print_error(f"Source file not found: {source_file}")
        return None

    print_step("Init", f"Loading source file: {source_file}")
    try:
        source_code = load_source_code(source_file)
    except Exception as exc:
        print_error(f"Failed to read source file: {exc}")
        return None

    print_step("Init", f"Loaded {len(source_code):,} characters of source code.", "success")
    ensure_output_dirs()

    initial_state: WorkflowState = {
        "source_code": source_code,
        "source_file_path": source_file,
        "modules": [],
        "documentation": None,
        "audit_report": None,
        "audit_feedback": "",
        "audit_retries": 0,
        "converted_modules": [],
        "test_suites": [],
        "assembly_result": None,
        "build_report":    None,
        "build_feedback":  "",
        "build_retries":   0,
        "metrics_summary": None,
        "trace_data": None,
        "errors": [],
        "current_step": "start",
        "processing_complete": False,
    }

    print_step("Workflow", "Starting LangGraph pipeline…")
    from langgraph.checkpoint.memory import MemorySaver
    app = create_workflow(checkpointer=MemorySaver())

    try:
        from langgraph.types import Command
        cli_config = {"configurable": {"thread_id": "cli-session"}}

        console.print("\n[dim]" + "─" * 70 + "[/dim]")
        app.invoke(initial_state, config=cli_config)

        # ── Check for HITL pause ──────────────────────────────────────────────
        graph_state = app.get_state(cli_config)
        if graph_state.next:   # interrupted at review_gate
            console.print("[dim]" + "─" * 70 + "[/dim]\n")
            console.print("\n[bold yellow]PIPELINE PAUSED — Human Review Required[/bold yellow]")

            saved = graph_state.values
            if ar := saved.get("audit_report"):
                print_audit_report(ar)

            console.print(
                "\n[bold]Review the audit report above.[/bold]\n"
                "Issues listed are the areas requiring manual cross-check before conversion.\n"
            )
            console.print("[dim]Press ENTER to APPROVE and start conversion.[/dim]")
            console.print("[dim]Type  'reject'  to send back for re-documentation.[/dim]\n")

            try:
                choice = input("Your decision [approve/reject]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "approve"

            decision = "reject" if "reject" in choice else "approve"
            console.print(f"\n[bold]Decision: {decision.upper()}[/bold]")
            console.print("\n[dim]" + "─" * 70 + "[/dim]")

            # Resume pipeline
            app.invoke(Command(resume=decision), config=cli_config)
            console.print("[dim]" + "─" * 70 + "[/dim]\n")

        else:
            console.print("[dim]" + "─" * 70 + "[/dim]\n")

        # Return final state
        return app.get_state(cli_config).values

    except Exception as exc:
        print_error(f"Pipeline crashed: {exc}")
        import traceback
        traceback.print_exc()
        return None


# ── Summary ────────────────────────────────────────────────────────────────────

def _print_final_summary(state: WorkflowState) -> None:
    import config

    errors = state.get("errors", [])
    modules = state.get("modules", [])
    documentation = state.get("documentation")
    audit_report = state.get("audit_report")
    converted = state.get("converted_modules", [])
    suites = state.get("test_suites", [])

    lines: list[str] = [
        f"[green]✓[/green] Modules identified:    [bold]{len(modules)}[/bold]",
        f"[green]✓[/green] Documentation:         [bold]{'Created' if documentation else 'Not created'}[/bold]",
    ]

    if audit_report:
        score = audit_report.get("score", 0)
        passed = audit_report.get("passed", False)
        colour = "green" if passed else "red"
        status = "PASSED" if passed else "FAILED"
        lines.append(
            f"[green]✓[/green] Audit:                 [{colour}]{status}[/{colour}] "
            f"(score [bold]{score:.1f}/100[/bold])"
        )

    lines.append(f"[green]✓[/green] Converted modules:     [bold]{len(converted)}[/bold]")
    total_tests = sum(s.get("test_count", 0) for s in suites)

    build_report = state.get("build_report") or {}
    if build_report:
        b_status = build_report.get("status", "unknown")
        b_method = build_report.get("method", "?")
        b_errors = build_report.get("error_count", 0)
        b_col = "green" if b_status == "success" else ("yellow" if b_status in ("skipped","unknown") else "red")
        lines.append(
            f"[green]✓[/green] Build verification:    [{b_col}]{b_status.upper()}[/{b_col}]"
            f" via {b_method} — {b_errors} compile error(s)"
        )
    lines.append(
        f"[green]✓[/green] Test suites generated:  [bold]{len(suites)}[/bold] "
        f"([bold]{total_tests}[/bold] tests)"
    )

    if errors:
        lines.append(f"\n[yellow]⚠ {len(errors)} warning(s) during processing[/yellow]")

    lines.append(f"\n[dim]Artefacts saved to: {os.path.abspath(config.OUTPUT_DIR)}[/dim]")

    console.print(
        Panel(
            "\n".join(lines),
            title="[bold green]Pipeline Complete[/bold green]",
            border_style="green",
        )
    )


# ── Observability finaliser ────────────────────────────────────────────────────

def _finalise_observability() -> None:
    """Save metrics + trace artefacts and print a short timing table."""
    import config
    from rich.table import Table

    metrics_dict = get_metrics().to_dict()
    traces_dict  = get_tracer().to_dict()

    save_json(metrics_dict, "observability/metrics.json")
    save_json(traces_dict,  "observability/traces.json")

    # Print per-agent timing table
    agents = metrics_dict.get("agents", {})
    if agents:
        table = Table(
            title="[bold]Pipeline Metrics[/bold]",
            border_style="dim",
            header_style="bold cyan",
        )
        table.add_column("Agent",   style="cyan",   min_width=16)
        table.add_column("Status",  style="green",  min_width=10)
        table.add_column("ms",      style="yellow", min_width=8,  justify="right")
        table.add_column("LLM calls", min_width=10, justify="right")
        table.add_column("Tokens",  min_width=10,   justify="right")
        table.add_column("Items",   min_width=8,    justify="right")

        for name, m in agents.items():
            status_col = "[green]success[/green]" if m["status"] == "success" \
                else ("[yellow]partial[/yellow]"  if m["status"] == "partial"  \
                else f"[red]{m['status']}[/red]")
            table.add_row(
                name,
                status_col,
                f"{m['duration_ms']:.0f}",
                str(m["llm_calls"]),
                str(m["total_tokens"]),
                str(m["items_processed"]),
            )

        from utils.output_formatter import console
        console.print(table)

    print_step(
        "Observability",
        f"Metrics + traces saved to {os.path.abspath(config.OUTPUT_DIR)}/observability/",
        "success",
    )


# ── Dashboard launcher ─────────────────────────────────────────────────────────

def _launch_dashboard() -> None:
    print_step("Dashboard", "Launching Streamlit dashboard…")
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "app.py")
    subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", dashboard_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print_step("Dashboard", "Dashboard started at http://localhost:8501", "success")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()

    # Apply overrides before importing config
    if args.output_dir:
        os.environ["OUTPUT_DIR"] = args.output_dir
    if args.max_retries is not None:
        os.environ["MAX_AUDIT_RETRIES"] = str(args.max_retries)

    print_banner()

    if not _validate_config():
        sys.exit(1)

    # Initialise fresh observability singletons for this run
    reset_metrics()
    reset_tracer()
    setup_pipeline_logging()

    final_state = run_pipeline(args.source_file)

    if final_state is None:
        print_error("Pipeline did not complete successfully.")
        sys.exit(1)

    _finalise_observability()
    _print_final_summary(final_state)

    if args.dashboard:
        _launch_dashboard()


if __name__ == "__main__":
    main()

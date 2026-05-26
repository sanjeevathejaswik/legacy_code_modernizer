import sys
from typing import Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Force UTF-8 on Windows so Rich can render without the legacy cp1252 encoder
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

console = Console(legacy_windows=False)

# ASCII-safe icons (no Unicode symbols that break cp1252)
_ICONS = {"info": ">>", "success": "OK", "warning": "!!", "error": "XX"}


def print_banner() -> None:
    console.print(
        Panel(
            "[bold cyan]Legacy Code Conversion Pipeline[/bold cyan]\n"
            "[dim]Powered by LangGraph + Azure OpenAI[/dim]",
            border_style="cyan",
            padding=(1, 4),
        )
    )


def print_step(step_name: str, message: str, status: str = "info") -> None:
    colors = {"info": "blue", "success": "green", "warning": "yellow", "error": "red"}
    color = colors.get(status, "blue")
    icon  = _ICONS.get(status, ">>")
    console.print(f"[bold {color}][{icon}][{step_name}][/bold {color}] {message}")


def print_modules_table(modules: List[Dict]) -> None:
    if not modules:
        console.print("[yellow]No modules found.[/yellow]")
        return

    table = Table(
        title=f"[bold]Identified Modules -- {len(modules)} total[/bold]",
        border_style="blue",
        header_style="bold cyan",
    )
    table.add_column("Module Name", style="cyan",   min_width=28)
    table.add_column("Layer",       style="green",  min_width=14)
    table.add_column("Dependencies",style="yellow", min_width=20)
    table.add_column("Description")

    for m in modules:
        deps    = m.get("dependencies", [])
        dep_str = ", ".join(deps[:3]) + ("..." if len(deps) > 3 else "")
        table.add_row(
            m.get("name", "?"),
            m.get("layer", "unknown"),
            dep_str or "none",
            (m.get("description", ""))[:80],
        )
    console.print(table)


def print_audit_report(audit_report: Dict) -> None:
    score     = float(audit_report.get("score", 0))
    passed    = audit_report.get("passed", False)
    threshold = audit_report.get("threshold", 70.0)
    metrics   = audit_report.get("metrics", {})
    issues    = audit_report.get("issues", [])

    status_color = "green" if passed else "red"
    status_text  = "[OK] PASSED" if passed else "[!!] FAILED"

    metrics_lines = "\n".join(
        f"  {k.capitalize():15s}: {v}/100" for k, v in metrics.items()
    )
    critical = sum(1 for i in issues if i.get("severity") == "critical")
    major    = sum(1 for i in issues if i.get("severity") == "major")
    minor    = sum(1 for i in issues if i.get("severity") == "minor")

    body = (
        f"[{status_color}]{status_text}[/{status_color}]  "
        f"Score: [{status_color}]{score:.1f}[/{status_color}]/100  "
        f"(Threshold: {threshold})\n\n"
        f"[bold]Metrics:[/bold]\n{metrics_lines}\n\n"
        f"[bold]Issues:[/bold]  "
        f"[red]{critical} critical[/red]  "
        f"[yellow]{major} major[/yellow]  "
        f"[dim]{minor} minor[/dim]\n\n"
        f"[bold]Summary:[/bold] {audit_report.get('summary', '')[:220]}"
    )
    console.print(Panel(body, title="[bold]Audit Report[/bold]", border_style=status_color))


def print_conversion_summary(converted_modules: List[Dict]) -> None:
    if not converted_modules:
        return
    table = Table(
        title=f"[bold]Converted Modules -- {len(converted_modules)} total[/bold]",
        border_style="green",
        header_style="bold cyan",
    )
    table.add_column("Module", style="cyan",  min_width=30)
    table.add_column("Type",   style="green", min_width=14)
    table.add_column("Package")
    for m in converted_modules:
        table.add_row(
            m.get("name", ""),
            m.get("microservice_type", ""),
            m.get("package", ""),
        )
    console.print(table)


def print_test_summary(test_suites: List[Dict]) -> None:
    if not test_suites:
        return
    total = sum(s.get("test_count", 0) for s in test_suites)
    console.print(
        Panel(
            f"Generated [bold green]{len(test_suites)}[/bold green] test suites "
            f"with [bold green]{total}[/bold green] total unit tests",
            title="[bold]Test Generation Summary[/bold]",
            border_style="green",
        )
    )


def print_error(message: str) -> None:
    console.print(f"[bold red][XX] ERROR:[/bold red] {message}")


def print_success(message: str) -> None:
    console.print(f"[bold green][OK][/bold green] {message}")

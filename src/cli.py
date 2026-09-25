"""
Command-line interface for the Multi-Agent RAG System.

Usage:
    python -m src.cli                 # interactive REPL
    python -m src.cli "your question" # one-shot query
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.manager.agent import Route, handle_query

console = Console()

BANNER = """[bold cyan]Northwind Enterprise Assistant[/bold cyan]
Ask about company policies/processes, business data, or both.
Type 'exit' or 'quit' to leave, or press Ctrl+C.
"""

ROUTE_LABELS = {
    Route.QUALITATIVE: "📄 Documentation agent",
    Route.QUANTITATIVE: "📊 Data agent",
    Route.BOTH: "🔗 Documentation + Data agents",
    Route.UNCLEAR: "❓ Needs clarification",
}


def run_query(question: str) -> None:
    try:
        response = handle_query(question)
    except Exception as exc:  # noqa: BLE001 - top-level CLI safety net
        console.print(Panel(f"[red]Something went wrong:[/red] {exc}", title="Error"))
        return

    label = ROUTE_LABELS.get(response.route, response.route.value)
    console.print(Panel(Markdown(response.answer), title=label, border_style="cyan"))


def repl() -> None:
    console.print(Panel(BANNER, border_style="green"))
    while True:
        try:
            question = console.input("[bold green]> [/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\nGoodbye!")
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            console.print("Goodbye!")
            break
        run_query(question)


def main() -> None:
    args = sys.argv[1:]
    if args:
        run_query(" ".join(args))
    else:
        repl()


if __name__ == "__main__":
    main()
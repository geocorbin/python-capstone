from __future__ import annotations

from src import cli
from src.manager.agent import ManagerResponse, Route


def test_run_query_prints_answer(monkeypatch, capsys):
    fake_response = ManagerResponse(
        question="q", route=Route.QUALITATIVE, answer="This is the answer.", needs_clarification=False
    )
    monkeypatch.setattr(cli, "handle_query", lambda q: fake_response)

    cli.run_query("What is our PTO policy?")

    captured = capsys.readouterr()
    assert "This is the answer." in captured.out
    assert "Documentation agent" in captured.out


def test_run_query_handles_exceptions_gracefully(monkeypatch, capsys):
    def boom(question):
        raise RuntimeError("something exploded")

    monkeypatch.setattr(cli, "handle_query", boom)

    cli.run_query("anything")

    captured = capsys.readouterr()
    assert "Something went wrong" in captured.out
    assert "something exploded" in captured.out


def test_run_query_shows_clarification_label(monkeypatch, capsys):
    fake_response = ManagerResponse(
        question="q", route=Route.UNCLEAR, answer="Could you clarify?", needs_clarification=True
    )
    monkeypatch.setattr(cli, "handle_query", lambda q: fake_response)

    cli.run_query("huh")

    captured = capsys.readouterr()
    assert "Needs clarification" in captured.out
    assert "Could you clarify?" in captured.out


def test_main_one_shot_mode_invokes_run_query(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "run_query", lambda q: calls.append(q))
    monkeypatch.setattr(cli.sys, "argv", ["prog", "what", "is", "our", "policy"])

    cli.main()

    assert calls == ["what is our policy"]


def test_main_no_args_invokes_repl(monkeypatch):
    called = {"repl": False}
    monkeypatch.setattr(cli, "repl", lambda: called.__setitem__("repl", True))
    monkeypatch.setattr(cli.sys, "argv", ["prog"])

    cli.main()

    assert called["repl"] is True
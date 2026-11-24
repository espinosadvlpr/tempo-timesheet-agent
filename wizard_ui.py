"""Terminal UI seam for the setup wizard.

Uses ``questionary`` and ``rich`` when they are importable and the session is
interactive. Otherwise it falls back to plain ``input()``/``print()`` so that
``python setup.py`` always works.
"""
import getpass
import sys
from contextlib import contextmanager

FALLBACK_HINT = (
    "[HINT] For a nicer wizard, run it with uv so the TUI dependencies are "
    "installed automatically: uv run setup.py"
)


def _backends():
    """Return (questionary, Console, Panel, Text) or None."""
    try:
        import questionary
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
    except ImportError:
        return None
    return questionary, Console, Panel, Text


def _is_interactive():
    return bool(sys.stdin and sys.stdout and sys.stdin.isatty() and sys.stdout.isatty())


def _tui():
    """Return the backends only when the rich TUI should be used."""
    return _backends() if _is_interactive() else None


def notify_fallback():
    """Print one hint line when the TUI libraries are not installed."""
    if _backends() is None:
        print(FALLBACK_HINT)


def _ask(question):
    answer = question.ask()
    if answer is None:  # Ctrl-C / Ctrl-D inside questionary
        raise KeyboardInterrupt
    return answer


def header(title):
    backends = _tui()
    if backends:
        _q, console_cls, panel_cls, _text = backends
        console_cls().print(panel_cls(_text(title, style="bold"), expand=False))
        return
    print("\n========================================")
    print(f"  {title}")
    print("========================================")


def info(message):
    print(message)


def _tagged(tag, color, message):
    """Print ``[TAG] message`` with a colored tag; message is never parsed as markup."""
    backends = _tui()
    if backends:
        _q, console_cls, _panel, text_cls = backends
        line = text_cls.assemble((f"[{tag}]", color), " ", message)
        console_cls().print(line, highlight=False)
        return
    print(f"[{tag}] {message}")


def success(message):
    _tagged("OK", "green", message)


def warn(message):
    _tagged("WARN", "yellow", message)


def error(message):
    _tagged("ERROR", "red", message)


def text(prompt):
    backends = _tui()
    if backends:
        return _ask(backends[0].text(prompt)).strip()
    return input(f"{prompt}: ").strip()


def secret(prompt):
    """Prompt for a secret without echoing it."""
    backends = _tui()
    if backends:
        return _ask(backends[0].password(prompt)).strip()
    if _is_interactive():
        return getpass.getpass(f"{prompt}: ").strip()
    return input(f"{prompt}: ").strip()


def select(prompt, options, cancel_label="Exit"):
    """Single choice from ``options`` [(label, value)]; None when cancelled."""
    backends = _tui()
    if backends:
        questionary = backends[0]
        choices = [questionary.Choice(label, value=value) for label, value in options]
        choices.append(questionary.Choice(cancel_label, value=None))
        # questionary returns None for the cancel entry as well as for Ctrl-C.
        return questionary.select(prompt, choices=choices).ask()

    mapping = {str(i): value for i, (_label, value) in enumerate(options, start=1)}
    while True:
        print(prompt)
        for i, (label, _value) in enumerate(options, start=1):
            print(f"[{i}] {label}")
        print(f"[0] {cancel_label}")
        choice = input("\nEnter your choice: ").strip()
        if choice == "0":
            return None
        if choice in mapping:
            return mapping[choice]
        warn("Invalid choice, please try again.")


def select_many(prompt, options, all_label="All", cancel_label="Cancel"):
    """Multiple choice from ``options`` [(label, value)]; [] when cancelled."""
    backends = _tui()
    if backends:
        questionary = backends[0]
        choices = [questionary.Choice(label, value=value) for label, value in options]
        while True:
            answer = questionary.checkbox(
                f"{prompt} (space to toggle, enter to confirm, Ctrl-C to cancel)",
                choices=choices,
            ).ask()
            if answer is None:
                return []
            if answer:
                return answer
            warn("Select at least one entry.")

    all_index = len(options) + 1
    mapping = {str(i): value for i, (_label, value) in enumerate(options, start=1)}
    while True:
        print(f"{prompt} (Comma-separated, e.g., 1,2 or {all_index})")
        for i, (label, _value) in enumerate(options, start=1):
            print(f"[{i}] {label}")
        print(f"[{all_index}] {all_label}")
        print(f"[0] {cancel_label}")

        choice = input("\nEnter your choice: ").strip()
        if choice == "0":
            return []

        choices = [c.strip() for c in choice.split(",") if c.strip()]
        if str(all_index) in choices or "all" in [c.lower() for c in choices]:
            return [value for _label, value in options]

        selected = [mapping[c] for c in choices if c in mapping]
        if selected:
            return selected
        warn("Invalid choice, please try again.\n")


@contextmanager
def status(message):
    """Show a spinner around a long-running step (plain print in fallback)."""
    backends = _tui()
    if backends:
        with backends[1]().status(message):
            yield
        return
    print(message)
    yield

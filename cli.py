"""Professional CLI Interface for Autonomous AI Agent.

Design: Modern, distraction-free terminal interface with clean panels, tables, and zero emojis.
Includes fallback for environments without external packages.
"""

from __future__ import annotations
import sys

from agent.orchestrator import AIAgent
from agent.models import ToneType

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt
    has_rich = True
    console = Console()
except ImportError:
    has_rich = False


def print_banner(agent: AIAgent):
    if has_rich:
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[bold white]AUTONOMOUS AI AGENT[/bold white]", "[dim]v2.2 (Multi-Domain)[/dim]")
        table.add_row(
            "[dim]Active Account:[/dim] [blue]vansh.jakhodia.btech2023@atlasskilltech.university[/blue]",
            f"[dim]Dispatch Mode:[/dim] [{'bold green' if not agent.config.dry_run else 'bold yellow'}]{'LIVE GMAIL SMTP' if not agent.config.dry_run else 'DRY RUN'}[/]"
        )
        console.print(Panel(table, border_style="blue", title="[bold cyan]SYSTEM READY[/bold cyan]", subtitle="[dim]Type 'help' for examples or 'exit' to quit[/dim]"))
    else:
        print("=" * 64)
        print("AUTONOMOUS AI AGENT v2.2 (Multi-Domain)")
        print("Active Account: vansh.jakhodia.btech2023@atlasskilltech.university")
        print(f"Dispatch Mode: {'LIVE GMAIL SMTP' if not agent.config.dry_run else 'DRY RUN'}")
        print("=" * 64)
        print("Type 'help' for available commands or 'exit' to quit.\n")


def render_draft(draft):
    tone = draft.tone.value if isinstance(draft.tone, ToneType) else draft.tone
    if has_rich:
        t = Table(show_header=False, box=None, padding=(0, 1))
        t.add_row("[bold cyan]To:[/bold cyan]", f"{draft.recipient_name} <{draft.recipient_email}>")
        t.add_row("[bold cyan]Subject:[/bold cyan]", f"[bold white]{draft.subject}[/bold white]")
        t.add_row("[bold cyan]Tone:[/bold cyan]", f"[dim]{tone}[/dim]")
        t.add_row("", "")
        t.add_row("[bold cyan]Body:[/bold cyan]", f"[white]{draft.body}[/white]")

        console.print(Panel(
            t,
            title="[bold yellow][PENDING ACTION: EMAIL DRAFT REVIEW][/bold yellow]",
            border_style="yellow",
            subtitle="[bold red]Irreversible Action &bull; Confirmation Required[/bold red]"
        ))
    else:
        print("\n" + "-" * 64)
        print("[PENDING ACTION: EMAIL DRAFT REVIEW]")
        print(f"To: {draft.recipient_name} <{draft.recipient_email}>")
        print(f"Subject: {draft.subject}")
        print(f"Tone: {tone}")
        print(f"\nBody:\n{draft.body}")
        print("-" * 64)


def show_help():
    commands = [
        ("1. Math & Calculation", "calculate 25 * 40 + math.sqrt(144)"),
        ("2. Python Code Runner", "run code: print('Sum:', sum([1, 2, 3, 4, 5]))"),
        ("3. Web Research", "search web for Autonomous Agent architectures"),
        ("4. Task State (Section 9)", "create task: Build autonomous AI Agent multi-agent system"),
        ("5. Workspace Documents", "list files  OR  read file README.md"),
        ("6. Business Communications", "Send an email to Dr. Kunal Meher submitting my assignment"),
        ("7. Context Reuse (Memory)", "Send the same email to Sarah too"),
        ("8. Anti-Hallucination", "Send an email to Bob about the product launch"),
        ("9. Address Book", "show contacts"),
        ("10. Sent Audit History", "view history"),
    ]
    if has_rich:
        t = Table(title="Autonomous AI Agent - Multi-Domain Capabilities", border_style="blue")
        t.add_column("Capability Domain", style="cyan", width=24)
        t.add_column("Example Instruction", style="white")
        for domain, cmd in commands:
            t.add_row(domain, cmd)
        console.print(t)
    else:
        print("\nAvailable Capabilities & Example Commands:")
        for domain, cmd in commands:
            print(f"  • {domain:24} -> {cmd}")
        print("")


def main():
    agent = AIAgent()
    print_banner(agent)

    while True:
        try:
            if has_rich:
                user_input = Prompt.ask("\n[bold cyan]agent>[/bold cyan]").strip()
            else:
                user_input = input("\nagent> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("Session terminated. Goodbye!")
                break

            if user_input.lower() == "help":
                show_help()
                continue

            result = agent.process(user_input)

            if result.draft and result.requires_confirmation:
                render_draft(result.draft)
                if has_rich:
                    console.print("[bold yellow]Safety Guardrail Active:[/bold yellow] Type [bold green]'yes'[/bold green] to dispatch or [bold red]'no'[/bold red] to discard.")
                else:
                    print("Safety Guardrail Active: Type 'yes' to dispatch or 'no' to discard.")
            elif result.sent_record:
                mode = "Simulated Dry-Run" if result.sent_record.is_dry_run else "Delivered via Gmail SMTP"
                if has_rich:
                    console.print(Panel(
                        f"[bold white]{result.message}[/bold white]",
                        title=f"[bold green][DISPATCH SUCCESSFUL - {mode}][/bold green]",
                        border_style="green"
                    ))
                else:
                    print(f"\n[DISPATCH SUCCESSFUL - {mode}]\n{result.message}")
            else:
                if has_rich:
                    console.print(Panel(
                        result.message,
                        border_style="blue",
                        title="[bold cyan]AI Agent[/bold cyan]"
                    ))
                else:
                    print(f"\nAI Agent:\n{result.message}")

        except (KeyboardInterrupt, EOFError):
            print("\nSession terminated.")
            break


if __name__ == "__main__":
    main()

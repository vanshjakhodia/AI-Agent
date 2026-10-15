"""Professional CLI Interface for Autonomous AI Email Agent.

Assignment: Experiment 9 - Dr. Kunal Meher | Atlas SkillTech University
Design: Modern, distraction-free terminal interface with clean panels and tables.
"""

from __future__ import annotations
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.text import Text

from agent.orchestrator import AIAgent
from agent.models import ToneType

console = Console()


def print_banner(agent: AIAgent):
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[bold white]ATLAS AI EMAIL AGENT[/bold white]", "[dim]Experiment 9[/dim]")
    table.add_row("[dim]Student:[/dim] [cyan]Vansh Jakhodia[/cyan]", "[dim]Instructor:[/dim] [yellow]Dr. Kunal Meher[/yellow]")
    table.add_row(
        "[dim]Sender Account:[/dim] [blue]vansh.jakhodia.btech2023@atlasskilltech.university[/blue]",
        f"[dim]Dispatch Mode:[/dim] [{'bold green' if not agent.config.dry_run else 'bold yellow'}]{'LIVE GMAIL SMTP' if not agent.config.dry_run else 'DRY RUN'}[/]"
    )

    console.print(Panel(table, border_style="blue", title="[bold cyan]● SYSTEM READY[/bold cyan]", subtitle="[dim]Type 'help' for examples or 'exit' to quit[/dim]"))


def render_draft(draft):
    tone = draft.tone.value if isinstance(draft.tone, ToneType) else draft.tone
    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_row("[bold cyan]To:[/bold cyan]", f"{draft.recipient_name} <{draft.recipient_email}>")
    t.add_row("[bold cyan]Subject:[/bold cyan]", f"[bold white]{draft.subject}[/bold white]")
    t.add_row("[bold cyan]Tone:[/bold cyan]", f"[dim]{tone}[/dim]")
    t.add_row("", "")
    t.add_row("[bold cyan]Body:[/bold cyan]", f"[white]{draft.body}[/white]")

    console.print(Panel(
        t,
        title="[bold yellow]⚠️ PENDING ACTION: EMAIL DRAFT REVIEW[/bold yellow]",
        border_style="yellow",
        subtitle="[bold red]Irreversible Action &bull; Confirmation Required[/bold red]"
    ))


def show_help():
    t = Table(title="Available Commands & Test Prompts", border_style="blue")
    t.add_column("Intent", style="cyan", width=24)
    t.add_column("Example Instruction", style="white")

    t.add_row("1. Submit Assignment", "Send an email to Dr. Kunal Meher submitting my Experiment 9 AI Agent assignment")
    t.add_row("2. Meeting Reminder", "Send an email to John reminding him about tomorrow's 10 AM meeting")
    t.add_row("3. Context Reuse (Memory)", "Send the same email to Sarah too")
    t.add_row("4. Anti-Hallucination", "Send an email to Bob about the product launch (Bob is not in contacts)")
    t.add_row("5. Address Book", "show contacts")
    t.add_row("6. Sent Audit History", "view history")
    console.print(t)


def main():
    agent = AIAgent()
    print_banner(agent)

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]agent>[/bold cyan]").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[dim]Session terminated. Goodbye![/dim]")
                break

            if user_input.lower() == "help":
                show_help()
                continue

            result = agent.process(user_input)

            if result.draft and result.requires_confirmation:
                render_draft(result.draft)
                console.print("[bold yellow]Safety Guardrail Active:[/bold yellow] Type [bold green]'yes'[/bold green] to dispatch or [bold red]'no'[/bold red] to discard.")
            elif result.sent_record:
                mode = "[cyan]Simulated Dry-Run[/cyan]" if result.sent_record.is_dry_run else "[bold green]Delivered via Gmail SMTP[/bold green]"
                console.print(Panel(
                    f"[bold white]{result.message}[/bold white]",
                    title=f"[bold green]✔ DISPATCH SUCCESSFUL ({mode})[/bold green]",
                    border_style="green"
                ))
            else:
                console.print(Panel(
                    result.message,
                    border_style="blue",
                    title="[bold cyan]Atlas AI[/bold cyan]"
                ))

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session terminated.[/dim]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    main()

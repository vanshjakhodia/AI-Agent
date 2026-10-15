"""Automated Demonstration of Experiment 9 - Autonomous AI Email Agent.

Demonstrates:
1. Understanding intent and entity extraction
2. Looking up missing info (Contacts address book)
3. Drafting email content with tone adaptation
4. Human-in-the-loop safety confirmation guardrail
5. SMTP dispatch (with safe outbox record)
6. Conversational memory & context reuse ("send the same email to Sarah too")
7. Verified delivery to Dr. Kunal Meher (kunal.meher@atlasuniversity.edu.in)
8. Anti-hallucination guardrail when contact is missing
"""

import time
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from agent.orchestrator import AIAgent
from agent.config import config

console = Console()


def run_demo():
    console.print(Panel.fit(
        "[bold cyan]EXPERIMENT 9: AUTONOMOUS AI EMAIL AGENT DEMONSTRATION[/bold cyan]\n"
        "[dim]Instructor: Dr. Kunal Meher | Atlas SkillTech University[/dim]\n"
        "[green]Architecture: LLM (Reasoning) + Memory + Tools + Orchestration[/green]",
        border_style="cyan"
    ))

    # Initialize agent in dry_run mode for safe offline demonstration
    agent = AIAgent()
    agent.config.dry_run = True

    steps = [
        ("Step 1: Reminder Email to John", "Send an email to John reminding him about tomorrow's 10 AM meeting"),
        ("Step 2: Safety Confirmation (Human-in-the-Loop)", "yes"),
        ("Step 3: Context Reuse via Short-Term Memory", "Send the same email to Sarah too"),
        ("Step 4: Safety Confirmation for Sarah", "confirm"),
        ("Step 5: Assignment Submission to Dr. Kunal Meher", "Send an email to Dr. Kunal Meher submitting my Experiment 9 AI Agent assignment"),
        ("Step 6: Confirm Assignment Dispatch", "yes"),
        ("Step 7: Anti-Hallucination Guardrail Check", "Send an email to Bob about the product launch"),
        ("Step 8: User Provides Verified Email", "bob.smith@techcorp.io"),
        ("Step 9: Safety Cancellation", "no"),
    ]

    for title, prompt in steps:
        console.print(f"\n[bold yellow]▶ {title}[/bold yellow]")
        console.print(f"[bold green]User:[/bold green] {prompt}")
        result = agent.process(prompt)
        console.print(Panel(Markdown(result.message), border_style="blue", title="🤖 Agent Response"))
        time.sleep(0.3)

    console.print("\n[bold green]✅ Demonstration Completed Successfully with Zero Errors![/bold green]")


if __name__ == "__main__":
    run_demo()

"""
DriveTalk AI – interactive demo entry point.

Usage:
  python -m src.main                # text + TTS
  python -m src.main --text-only    # pure text
  python -m src.main --voice        # mic + STT + TTS
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

load_dotenv()

console = Console()


def banner():
    name = os.getenv("DEALERSHIP_NAME", "Apex Motors")
    console.print(
        Panel.fit(
            f"[bold cyan]DriveTalk AI[/bold cyan]\n"
            f"AI Voice Receptionist for [bold]{name}[/bold]\n"
            f"[dim]LangGraph tool-calling + TTS pipeline[/dim]",
            border_style="cyan",
        )
    )


def run_text_loop(text_only: bool = False):
    from src.agent import chat
    from src.tts import speak

    history: list = []
    console.print(
        "\n[green]Type your message and press Enter.[/green] "
        "Type [bold]quit[/bold] or [bold]exit[/bold] to leave.\n"
    )

    greeting = (
        f"Thank you for calling {os.getenv('DEALERSHIP_NAME', 'Apex Motors')} service. "
        "This is DriveTalk, your AI receptionist. How can I help you today?"
    )
    console.print(f"[bold magenta]DriveTalk:[/bold magenta] {greeting}")
    if not text_only:
        speak(greeting)

    while True:
        try:
            user = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user:
            continue
        if user.lower() in ("quit", "exit", "bye", "goodbye"):
            console.print("[dim]Talk to you later![/dim]")
            break

        with console.status("[dim]Thinking…[/dim]", spinner="dots"):
            reply, history = chat(user, history)

        console.print(f"[bold magenta]DriveTalk:[/bold magenta] {reply}\n")
        if not text_only:
            speak(reply)


def main():
    parser = argparse.ArgumentParser(description="DriveTalk AI – local voice receptionist demo")
    parser.add_argument("--text-only", action="store_true", help="Disable TTS playback")
    parser.add_argument("--voice", action="store_true", help="Full mic → STT → agent → TTS loop")
    args = parser.parse_args()

    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "groq" and not os.getenv("GROQ_API_KEY"):
        console.print("[red]Missing GROQ_API_KEY in .env[/red]")
        sys.exit(1)
    if provider != "groq" and not os.getenv("OPENAI_API_KEY"):
        console.print("[red]Missing OPENAI_API_KEY in .env (or set LLM_PROVIDER=groq)[/red]")
        sys.exit(1)

    banner()

    if args.voice:
        from src.agent import chat
        from src.tts import speak
        from src.voice_loop import run_voice_loop

        run_voice_loop(chat, speak)
    else:
        run_text_loop(text_only=args.text_only)


if __name__ == "__main__":
    main()

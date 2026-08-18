"""
Vocalize-style TTS pipeline for DriveTalk AI.

Uses Microsoft Edge neural voices via edge-tts (high quality, free, no API key).
Audio is played back with pygame for cross-platform support.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() in ("1", "true", "yes")
VOICE = os.getenv("TTS_VOICE", "en-US-JennyNeural")
RATE = os.getenv("TTS_RATE", "+0%")


async def _synthesize(text: str, out_path: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(out_path)


def speak(text: str, block: bool = True) -> None:
    """
    Convert text → speech and play it.
    Non-blocking mode is available but the simple CLI uses blocking.
    """
    if not TTS_ENABLED or not text.strip():
        return

    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name

        asyncio.run(_synthesize(text, tmp))

        import pygame

        pygame.mixer.init()
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        if block:
            while pygame.mixer.music.get_busy():
                pygame.time.wait(50)
        try:
            os.unlink(tmp)
        except OSError:
            pass
    except Exception as e:
        print(f"[TTS warning] {e}")


def list_voices() -> None:
    """Helper to print available edge-tts voices (run once if you want to change VOICE)."""
    import edge_tts

    async def _list():
        voices = await edge_tts.list_voices()
        for v in voices:
            if v["Locale"].startswith("en-"):
                print(f"{v['ShortName']:30} {v['Gender']:8} {v['Locale']}")

    asyncio.run(_list())


if __name__ == "__main__":
    list_voices()

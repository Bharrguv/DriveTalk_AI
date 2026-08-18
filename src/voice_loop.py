"""
Improved voice loop for DriveTalk AI (Feature A).

- Clear one-time dependency check (no infinite spam)
- Push-to-talk style: press Enter to start recording, speak, auto-stop
- Better silence / error handling
- Falls back gracefully if packages are missing
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from typing import Callable

from dotenv import load_dotenv

load_dotenv()

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")


def _check_deps() -> tuple[bool, str]:
    """Return (ok, message). Only print guidance once."""
    missing = []
    try:
        import sounddevice  
    except ImportError:
        missing.append("sounddevice")
    try:
        import numpy  
    except ImportError:
        missing.append("numpy")
    try:
        import scipy  
    except ImportError:
        missing.append("scipy")

    if missing:
        msg = (
            "Voice mode needs: pip install sounddevice soundfile scipy numpy\n"
            f"Missing: {', '.join(missing)}\n"
            "Falling back is not possible for mic recording. Use text mode instead:\n"
            "  python -m src.main"
        )
        return False, msg
    return True, "ok"


def _record_seconds(duration: float = 6.0) -> str | None:
    """Record fixed duration from default mic → temp wav path."""
    import sounddevice as sd
    import numpy as np
    from scipy.io.wavfile import write as wav_write

    sample_rate = 16000
    print(f"  🎤 Recording for {duration:.0f}s — speak now...")
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()

    energy = float(np.abs(recording).mean())
    if energy < 0.004:
        print("  (mostly silence — try speaking louder or closer to the mic)")
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio_int16 = (recording * 32767).astype("int16")
    wav_write(tmp.name, sample_rate, audio_int16)
    return tmp.name


def _transcribe(wav_path: str) -> str:
    """Prefer local Whisper; fall back to Google via SpeechRecognition."""
    
    try:
        import whisper

        print("  🧠 Transcribing (Whisper)...")
        model = whisper.load_model(WHISPER_MODEL)
        result = model.transcribe(wav_path, fp16=False, language="en")
        return (result.get("text") or "").strip()
    except ImportError:
        pass
    except Exception as e:
        print(f"  Whisper failed ({e}), trying Google STT...")

    
    try:
        import speech_recognition as sr

        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = r.record(source)
        return r.recognize_google(audio)
    except Exception as e:
        print(f"  STT failed: {e}")
        return ""


def run_voice_loop(
    chat_fn: Callable[[str, list], tuple[str, list]],
    speak_fn: Callable[[str], None],
) -> None:
    """
    Improved turn-based voice conversation (push-to-talk style).

    - Press Enter → record for a few seconds
    - Agent replies with TTS
    - Ctrl+C to quit
    """
    ok, msg = _check_deps()
    if not ok:
        print("\n" + msg + "\n")
        return

    print("\n🎙️  Voice mode (improved)")
    print("   • Press Enter to start recording")
    print("   • Speak clearly for ~5–6 seconds")
    print("   • Ctrl+C to quit\n")

    history: list = []

    # Opening greeting
    greeting = (
        "Thank you for calling Apex Motors service. "
        "This is DriveTalk. Press Enter when you're ready to speak."
    )
    print(f"  DriveTalk: {greeting}")
    try:
        speak_fn(greeting)
    except Exception:
        pass

    while True:
        try:
            input("  ⏎  Press Enter to talk (or Ctrl+C to quit)... ")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        try:
            wav = _record_seconds(6.0)
            if not wav:
                continue

            text = _transcribe(wav)
            try:
                os.unlink(wav)
            except OSError:
                pass

            if not text:
                print("  (could not understand — try again)\n")
                continue

            print(f"  You: {text}")
            reply, history = chat_fn(text, history)
            print(f"  DriveTalk: {reply}\n")
            speak_fn(reply)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"  Voice error: {e}\n")
            continue

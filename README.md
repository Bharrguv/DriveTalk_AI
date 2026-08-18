
# DriveTalk AI

**AI Voice Receptionist + Customer Support for Auto Dealerships**

DriveTalk AI is a local-first voice agent that answers calls, checks appointment slots via a mock API, books/reschedules service appointments, and escalates edge cases — built with LangGraph tool-calling and a TTS pipeline.

Inspired by Toma-style dealership voice agents.

## Features

- Natural receptionist persona for a fictional dealership (Apex Motors)
- **Tools**:
  - `check_available_slots` – query open service bays/times
  - `book_appointment` – confirm a new booking
  - `reschedule_appointment` – move an existing booking
  - `escalate_to_human` – hand off complex / angry / edge-case calls
- Mock in-memory appointment store (easy to swap for real DMS/CRM later)
- LangGraph ReAct-style agent with tool calling
- TTS pipeline (edge-tts) for spoken responses
- Optional local microphone STT (speech_recognition + Whisper)
- Fully runnable offline after install (LLM key required)

## Quick Start

```bash
# 1. Unzip and enter the project
cd DriveTalk-AI

# 2. Create virtualenv (recommended)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (or GROQ_API_KEY)

# 5. Run the interactive demo
python -m src.main
```

## Demo Modes

| Command | Description |
|---------|-------------|
| `python -m src.main` | Text chat + spoken TTS replies |
| `python -m src.main --voice` | Full voice loop (mic → STT → agent → TTS) |
| `python -m src.main --text-only` | Pure text (no TTS) |

## Project Structure

```
DriveTalk-AI/
├── README.md
├── requirements.txt
├── .env.example
├── data/
│   └── appointments.json          # seed data (optional)
├── src/
│   ├── __init__.py
│   ├── main.py                    # entry point
│   ├── agent.py                   # LangGraph agent + tools
│   ├── mock_api.py                # appointment store & logic
│   ├── tts.py                     # Vocalize-style TTS pipeline
│   └── voice_loop.py              # optional mic STT + playback
└── scripts/
    └── seed_data.py
```

## Environment Variables

```env
# Required – pick one LLM provider
OPENAI_API_KEY=sk-...
# or
GROQ_API_KEY=gsk_...

# Optional
LLM_PROVIDER=openai          # openai | groq
LLM_MODEL=gpt-4o-mini        # or llama-3.3-70b-versatile for Groq
TTS_VOICE=en-US-JennyNeural  # edge-tts voice
DEALERSHIP_NAME=Apex Motors
```

## Example Conversation

```
You: Hi, I need an oil change for my 2022 Honda Civic.

DriveTalk: Welcome to Apex Motors service! I’d be happy to help with an oil change.
           I have openings tomorrow at 9:00 AM, 11:30 AM, and 2:00 PM.
           Which time works best for you?

You: Tomorrow at 11:30 is perfect. Name is Sarah Chen, phone 555-0192.

DriveTalk: Confirmed! I’ve booked your oil change for tomorrow at 11:30 AM
           under Sarah Chen. Confirmation code: APT-48291.
           You’ll get a text reminder the day before. Anything else I can help with?
```

## Extending

- Replace `mock_api.py` with real CDK / Xtime / Dealertrack calls
- Swap edge-tts for your own Vocalize / ElevenLabs / CosyVoice pipeline
- Add LiveKit or Twilio for real phone numbers
- Add more tools (parts lookup, recall check, sales lead capture)

## License

MIT – free to use, modify, and deploy.

Built with ❤️ for local-first AI voice agents.

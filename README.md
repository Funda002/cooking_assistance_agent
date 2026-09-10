# 🍳 Kitchen Agent

A local-first, voice-enabled AI cooking assistant that helps users plan and execute recipes conversationally.

## Project Evolution

Kitchen Agent was built in two stages:

1. **Terminal Kitchen Agent** — the original text-based cooking agent built from scratch.
2. **Voice Kitchen Agent** — a voice interface built on top of the existing Kitchen Agent using LiveKit, Deepgram, Silero VAD, OpenAI, and Rime TTS.

> **Core principle:** The Kitchen Agent remains the cooking brain. Voice is an interface layer.

The voice system converts speech to text, sends the request to the existing Kitchen Agent, and converts the response back into speech.

---

## Current Status

**Milestone: Kitchen Agent V1**

V1 supports:

- Recipe planning
- Cooking state tracking
- Step-by-step guidance
- Natural `next` / `done` navigation
- Cooking questions during a recipe
- Ingredient substitutions
- Recipe-plan modification
- Timers
- Timer status
- Timer cancellation
- Automatic voice timer-expiry announcements
- Voice interruptions / barge-in
- Recipe completion
- Terminal and voice interfaces

Known V1 limitations are documented below.

---

# Architecture

## Core Concepts

Kitchen Agent is built around:

```text
PLAN
STATE
MEMORY
TOOLS
REFLECTION
```

### PLAN

The recipe plan describes what should happen.

```text
Step 1 → Prepare ingredients
Step 2 → Heat pan
Step 3 → Add ingredients
Step 4 → Cook
Step 5 → Serve
```

### STATE

State tracks where the user currently is.

Example:

```text
current_step = 3
completed_steps = [1, 2]
status = cooking
```

State is important because the LLM should not be trusted to remember cooking progress purely from conversation.

### MEMORY

`memory.py` contains the project's memory functionality for retaining useful information.

The current voice V1 bridge deliberately keeps the active voice flow focused on PLAN + STATE rather than adding an extra memory-extraction LLM call on every turn.

### TOOLS

Tools perform deterministic actions.

Current tools include:

```text
timer
timer_status
cancel_timer
```

### REFLECTION

`reflect.py` contains reflection and validation functionality intended to check whether a recipe plan remains logically consistent after changes.

---

# Agent Loop

```text
USER
  ↓
LLM decides action
  ↓
PYTHON BACKEND
  ↓
PLAN / STATE / TOOLS / REFLECTION
  ↓
Response
  ↓
USER
```

Deterministic navigation commands such as:

```text
next
done
continue
```

are handled by Python rather than relying on the LLM to invent state transitions.

Example:

```text
User:
"Done."

        ↓

Python:
advance_step()

        ↓

STATE changes

        ↓

Agent:
"Step 5. Add the vegetables."
```

---

# Terminal vs Voice

## Terminal Agent

The original interface:

```text
User types
   ↓
Kitchen Agent
   ↓
Text response
   ↓
Terminal
```

Run it with:

```powershell
python main.py
```

The terminal version is especially useful for development, debugging, inspecting state, and testing the core cooking logic.

---

## Voice Agent

The voice interface:

```text
User speaks
   ↓
LiveKit / VAD
   ↓
Deepgram STT
   ↓
Existing Kitchen Agent
   ↓
Rime TTS
   ↓
User hears response
```

The voice agent is not a second cooking agent. It is an interface around the existing backend.

---

# Voice Architecture

```text
                    VOICE AGENT
                         │
                         ▼
                    MICROPHONE
                         │
                         ▼
                LiveKit / Silero VAD
                         │
                         ▼
                    Deepgram STT
                         │
                         ▼
              KitchenAgentBridge
                         │
                         ▼
              EXISTING KITCHEN AGENT
                         │
              ┌──────────┼──────────┐
              │          │          │
             PLAN      STATE      TOOLS
              │          │          │
              └──────────┼──────────┘
                         │
                         ▼
                      Response
                         │
                         ▼
                     Rime TTS
                         │
                         ▼
                     SPEAKER
```

---

# Project Structure

```text
kitchen_agent/
│
├── main.py
├── tools.py
├── memory.py
├── reflect.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
│
└── voice/
    ├── __init__.py
    ├── rime_tts.py
    ├── voice_shell.py
    └── kitchen_bridge.py
```

---

# File Guide

## `main.py`

The main Kitchen Agent backend.

It contains the core recipe orchestration logic, including:

- Recipe-plan creation
- Current-step lookup
- Step advancement
- Navigation-command detection
- LLM action decisions
- Tool execution
- Recipe-plan modification
- Timer-response formatting
- Plan validation and repair
- Original terminal-agent loop

This is the main cooking brain.

**Do not modify it casually when working only on the voice interface.**

---

## `tools.py`

Contains deterministic tools.

The V1 timer system provides:

```text
TimerManager
timer()
timer_status()
cancel_timer()
```

Timers:

- Run in background threads
- Track their own state
- Report remaining time
- Support cancellation
- Detect completion
- Trigger `on_timer_finished`

The voice layer uses the timer callback to announce completion automatically.

---

## `memory.py`

Contains the project's memory functionality.

It is intended for useful information that may need to persist beyond an immediate decision.

The current voice V1 bridge avoids adding a separate memory-extraction call to every voice turn to reduce unnecessary latency and API usage.

---

## `reflect.py`

Contains reflection / validation logic.

It is intended to check recipe-plan consistency and help repair invalid plans after modifications.

This becomes important when users change:

- Ingredients
- Quantities
- Serving sizes
- Cooking constraints
- Recipe steps

---

## `voice/__init__.py`

Makes `voice` a Python package so modules can be imported using:

```python
from voice.rime_tts import RimeTTS
```

---

## `voice/rime_tts.py`

Rime text-to-speech integration.

```text
Text
 ↓
Rime
 ↓
Audio
```

API credentials must remain in `.env`.

Never hard-code credentials here.

---

## `voice/voice_shell.py`

Main voice interface.

Connects:

- LiveKit
- Silero VAD
- Deepgram STT
- OpenAI LiveKit integration
- Rime TTS
- KitchenAgentBridge

Responsibilities:

- Starts voice sessions
- Handles speech recognition
- Starts TTS
- Provides the initial greeting
- Enables interruptions / barge-in
- Connects timer completion events to spoken announcements

The greeting is deliberately handled here rather than passed to recipe creation.

---

## `voice/kitchen_bridge.py`

Adapter between the voice interface and the existing Kitchen Agent.

It calls existing backend functions such as:

```python
create_plan()
get_current_step()
advance_step()
decide_action()
execute_tool()
modify_plan()
```

It also provides voice-specific behavior such as:

- Natural next-command detection
- Timer cancellation detection
- Voice text cleanup
- Shortening long responses
- Current-step speech
- State preservation after plan modifications

It is **not** intended to be a second cooking engine.

---

## `.env`

Stores private credentials and configuration.

Example:

```env
OPENAI_API_KEY=YOUR_KEY_HERE

LIVEKIT_URL=YOUR_LIVEKIT_URL
LIVEKIT_API_KEY=YOUR_LIVEKIT_API_KEY
LIVEKIT_API_SECRET=YOUR_LIVEKIT_API_SECRET

DEEPGRAM_API_KEY=YOUR_DEEPGRAM_API_KEY

rime_test_api=YOUR_RIME_API_KEY
RIME_BASE_URL=YOUR_RIME_BASE_URL
RIME_SPEAKER=YOUR_RIME_SPEAKER
```

Use real credentials locally.

**Never commit `.env` to GitHub.**

---

## `.gitignore`

Keeps secrets, virtual environments, caches, and other unnecessary files out of Git.

At minimum, `.env` and the virtual environment should be ignored.

---

## `requirements.txt`

Contains the Python dependencies required by the project.

The V1 voice stack includes packages for:

- LiveKit
- LiveKit Agents
- Deepgram
- Silero
- OpenAI
- Rime integration dependencies
- Python dotenv

Install with:

```powershell
pip install -r requirements.txt
```

---

# Installation

## 1. Clone the repository

```powershell
git clone https://github.com/Funda002/cooking_assistance_agent.git
cd cooking_assistance_agent
```

## 2. Create the virtual environment

On Windows:

```powershell
python -m venv myenv
```

Activate:

```powershell
.\myenv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate again:

```powershell
.\myenv\Scripts\Activate.ps1
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

Verify:

```powershell
pip list
```

---

# Environment Configuration

Create:

```text
.env
```

in the project root:

```text
kitchen_agent/
├── .env
├── main.py
├── tools.py
└── voice/
```

Add your actual credentials.

Never paste real API keys into GitHub, README files, screenshots, source code, or logs.

---

# Running the Terminal Agent

Activate the environment:

```powershell
cd C:\Users\SRI SARVESH\Documents\kitchen_agent
.\myenv\Scripts\Activate.ps1
```

Run:

```powershell
python main.py
```

Example:

```text
You: I want to make an omelet.

Agent:
Step 1. Crack the eggs and add salt and pepper.
```

---

# Running the Voice Agent

Activate the environment:

```powershell
cd C:\Users\SRI SARVESH\Documents\kitchen_agent
.\myenv\Scripts\Activate.ps1
```

Start the LiveKit development worker:

```powershell
python voice/voice_shell.py dev
```

If the installed LiveKit Agents version uses different CLI options:

```powershell
python voice/voice_shell.py --help
```

The worker should start and connect to the configured LiveKit project.

Connect to the corresponding LiveKit development room/interface configured for the project.

---

# Voice Session Startup

When the voice session starts, the agent should first say:

```text
Hey! What would you like to cook today?
```

The greeting belongs to the voice layer and should not be sent through recipe creation.

Then:

```text
User:
I want to make tomato pasta.
```

The Kitchen Agent creates the plan and initializes cooking state.

---

# Cooking Flow

```text
User request
   ↓
create_plan()
   ↓
PLAN created
   ↓
STATE → Step 1
   ↓
Voice speaks current step
```

The user can then ask questions or modify the recipe.

---

# Plan Modification

Example:

```text
Current:
Step 4

User:
"I don't have butter. Can I use oil?"

        ↓

LLM:
MODIFY_PLAN

        ↓

modify_plan()

        ↓

State protection

        ↓

Current step remains Step 4
```

Changing the recipe should not unexpectedly send the user back to Step 1.

---

# Deterministic Navigation

Commands such as:

```text
next
done
continue
what's next
let's continue
```

are handled deterministically where possible.

Example:

```text
User:
"Done."

        ↓

advance_step(plan, state)

        ↓

Step 3 → Step 4
```

---

# Timer System

Timers are deterministic and run independently from the conversation.

```text
User:
"Set a timer for 60 seconds."

        ↓

timer()

        ↓

Background timer

        ↓

60 seconds pass

        ↓

on_timer_finished

        ↓

LiveKit session.say()

        ↓

Rime TTS

        ↓

"Your 60-second timer is finished."
```

The user can continue talking while the timer is running.

The timer supports:

```text
How much time is left?
```

and:

```text
Cancel the timer.
```

---

# Voice-Native Design Principles

The voice agent should:

- Speak naturally
- Keep normal responses short
- Give one cooking step at a time
- Avoid reading the whole recipe unnecessarily
- Avoid Markdown
- Avoid bullets in spoken responses
- Answer general questions briefly
- Avoid repeating previous steps unless requested
- Never claim a cooking step was completed unless the backend completed it
- Never invent cooking state

Safety-critical explanations may need to be longer.

---

# Testing

## Basic Test

### Greeting

Expected:

```text
Hey! What would you like to cook today?
```

### Recipe creation

Say:

```text
I want to make vegetable fried rice.
```

Expected:

```text
Plan created
STATE → Step 1
```

### Ingredients

Say:

```text
What ingredients do I need?
```

### Summary

Say:

```text
Can you give me a quick summary of the whole recipe?
```

### Substitution

Say:

```text
I don't have bell pepper. Can I replace it?
```

Check that the plan changes without losing cooking progress.

### Question

Say:

```text
Why do we cook the vegetables first?
```

The recipe should not advance just because a question was asked.

### Navigation

Try:

```text
What's next?
```

```text
Continue.
```

```text
Done.
```

Each should advance appropriately.

### Timer

Say:

```text
Set a timer for 10 seconds.
```

Wait without saying anything.

Expected:

```text
Your 10-second timer is finished.
```

### Completion

Continue until the final step.

Expected:

```text
Great job. Your dish is complete!
```

---

# Full Realistic V1 Test

A strong end-to-end test should cover:

```text
Greeting
 ↓
Recipe creation
 ↓
Ingredient list
 ↓
Recipe summary
 ↓
Substitution
 ↓
Impossible modification
 ↓
Serving / quantity constraint
 ↓
Begin cooking
 ↓
Cooking question
 ↓
Next / Done
 ↓
Timer
 ↓
Timer status
 ↓
Timer expiry
 ↓
Continue
 ↓
Another modification
 ↓
Completion
```

---

# V1 Test Results

Successfully demonstrated during development:

- Greeting
- Recipe creation
- Step-by-step cooking
- Natural navigation
- Cooking questions
- Ingredient substitutions
- State preservation during common modifications
- Timer creation
- Timer status
- Timer cancellation
- Automatic timer-expiry voice announcement
- Recipe completion

---

# Known V1 Limitations

## Complex plan modifications

Complex modifications can expose recipe-plan consistency problems.

Reflection and validation functionality exists, but deeper integration and testing is a future improvement.

## Essential ingredients

The agent should distinguish optional ingredients from essential ingredients.

For example:

```text
"I don't have cilantro."
```

can usually be handled with omission or substitution.

But:

```text
"Can I make fried rice without rice?"
```

should not blindly transform the dish while still calling it fried rice.

## Voice ingredient lists

Ingredient requests can become too verbose.

A future version should provide a dedicated concise ingredient-list response.

## Voice summaries

Recipe summaries can become too long.

A future version should provide a dedicated voice-native summary.

## Complex multi-action commands

Commands such as:

```text
"Cancel the timer and move to the next step."
```

may require explicit multi-action orchestration.

---

# Development Philosophy

The project separates:

```text
Interface
    ↓
Cooking Agent
    ↓
Tools / State / Plan
```

Current interfaces:

```text
                 Kitchen Agent
                       │
              ┌────────┴────────┐
              │                 │
           Terminal            Voice
```

The cooking backend should remain independent from the interface.

---

# Cost and Latency

The project tries to avoid unnecessary LLM calls.

Deterministic commands such as:

```text
next
done
cancel timer
```

can be handled directly by Python.

This reduces:

- API usage
- Cost
- Latency
- State errors

The voice bridge also avoids adding a second LLM merely to summarize every response.

---

# Security

Never commit:

```text
.env
API keys
LiveKit API secrets
Deepgram API keys
Rime API keys
OpenAI API keys
```

Before pushing:

```powershell
git status
```

Check that `.env` is not staged.

Then inspect:

```powershell
git diff --cached
```

---

# Git Workflow

```powershell
git status
git add .
git status
git diff --cached
git commit -m "Describe the change"
git push origin main
```

---

# Quick Start for Future Me

## Terminal

```powershell
cd C:\Users\SRI SARVESH\Documents\kitchen_agent
.\myenv\Scripts\Activate.ps1
python main.py
```

## Voice

```powershell
cd C:\Users\SRI SARVESH\Documents\kitchen_agent
.\myenv\Scripts\Activate.ps1
python voice/voice_shell.py dev
```

## Install dependencies

```powershell
pip install -r requirements.txt
```

## Git

```powershell
git status
git add .
git commit -m "Describe the change"
git push origin main
```

---

# Quick Reference

| Task | Command |
|---|---|
| Create environment | `python -m venv myenv` |
| Activate environment | `.\myenv\Scripts\Activate.ps1` |
| Install packages | `pip install -r requirements.txt` |
| Run terminal agent | `python main.py` |
| Run voice agent | `python voice/voice_shell.py dev` |
| CLI help | `python voice/voice_shell.py --help` |
| Git status | `git status` |
| Stage | `git add .` |
| Commit | `git commit -m "message"` |
| Push | `git push origin main` |

---

# Project

**Kitchen Agent — Voice-Native AI Cooking Assistant**

Repository:

https://github.com/Funda002/cooking_assistance_agent

Focus areas:

- AI-agent architecture
- Structured planning
- State management
- Tool use
- Dynamic recipe adaptation
- Voice interaction
- Real-time cooking assistance

---

# License

Add the project's chosen license before public release if the project is intended for reuse.

For a hackathon repository, explicitly choosing an appropriate open-source license is recommended.

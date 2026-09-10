# 🍳 Kitchen Agent --- Voice-Native AI Cooking Assistant

A local-first AI cooking assistant that helps users plan, modify, and
execute recipes through natural conversation.

The project evolved from a terminal-based cooking agent into a real-time
voice-native AI agent using LiveKit, Deepgram, OpenAI, and Rime TTS.

------------------------------------------------------------------------

# Demo Video

Demo implementation:

https://www.youtube.com/watch?v=LYvaa4Skau0&t=23s

------------------------------------------------------------------------

# Project Overview

Most cooking assistants only answer recipe questions.

Kitchen Agent is designed as an **AI Agent** that can:

-   Understand cooking goals
-   Create a recipe plan
-   Maintain cooking state
-   Adapt recipes when ingredients change
-   Execute tools such as timers
-   Guide users step-by-step through voice interaction

The core idea:

    Interface
        ↓
    Kitchen Agent Brain
        ↓
    Plan + State + Tools
        ↓
    User Guidance

------------------------------------------------------------------------

# Project Evolution

## Build 1 --- Terminal AI Cooking Agent

The first version was built as a text-based cooking agent.

The engineering challenge:

> How do we make an LLM follow a cooking process instead of behaving
> like a normal chatbot?

Solution:

The cooking brain was separated into:

    PLAN
    STATE
    MEMORY
    TOOLS
    REFLECTION

The agent maintains:

-   Current recipe
-   Current cooking step
-   Completed steps
-   Ingredient changes
-   Tool execution state

Example:

    User:
    Done.

    Python Backend:
    advance_step()

    STATE:
    Step 2 → Step 3

    Agent:
    Add the vegetables next.

Deterministic actions are handled by Python instead of allowing the LLM
to randomly change state.

------------------------------------------------------------------------

# Build 2 --- Voice Native AI Agent

The second engineering challenge:

> How do we convert an existing reasoning agent into a real-time voice
> assistant?

Solution:

The cooking intelligence was kept independent.

Voice became an interface layer.

Architecture:

    User Voice
        ↓
    LiveKit Agent
        ↓
    Silero VAD
        ↓
    Deepgram STT
        ↓
    Kitchen Agent Backend
        ↓
    Rime TTS
        ↓
    User Voice Response

The voice layer provides:

-   Speech recognition
-   Natural voice responses
-   Interruptions / barge-in
-   Timer announcements

The cooking brain remains the same.

------------------------------------------------------------------------

# Agent Architecture

                     USER
                      |
                      |
                 Voice / Text
                      |
                      ↓
              Kitchen Agent Core
                      |
         ---------------------------
         |          |              |
        PLAN      STATE          TOOLS
         |          |              |
         ---------------------------
                      |
                 RESPONSE
                      |
                 Voice Output

------------------------------------------------------------------------

# Agent Components

## PLAN

Creates the cooking workflow.

Example:

    Step 1 → Prepare ingredients
    Step 2 → Heat pan
    Step 3 → Cook vegetables
    Step 4 → Add eggs
    Step 5 → Serve

------------------------------------------------------------------------

## STATE

Tracks where the user currently is.

Example:

    current_step = 3

    completed_steps:
    [1,2]

    status:
    cooking

This prevents the agent from losing progress.

------------------------------------------------------------------------

## TOOLS

Tools perform deterministic actions.

Current tools:

    timer()
    timer_status()
    cancel_timer()

Timer behaviour:

    User:
    Set timer for 60 seconds

            ↓

    Timer runs independently

            ↓

    Time expires

            ↓

    Voice announcement:

    Your timer is finished.

------------------------------------------------------------------------

# Features

## Cooking Intelligence

✅ Recipe planning\
✅ Step-by-step guidance\
✅ Ingredient substitutions\
✅ Recipe modification\
✅ Cooking questions\
✅ Serving size changes\
✅ Cooking completion tracking

## Voice Agent

✅ Real-time speech interaction\
✅ Natural voice output\
✅ Interruptions\
✅ Background timer announcements

------------------------------------------------------------------------

# Project Structure

    kitchen_agent/

    ├── main.py
    ├── tools.py
    ├── memory.py
    ├── reflect.py
    ├── requirements.txt
    ├── README.md

    └── voice/
        ├── __init__.py
        ├── voice_shell.py
        ├── kitchen_bridge.py
        └── rime_tts.py

------------------------------------------------------------------------

# Important Files

## main.py

The main cooking intelligence.

Responsible for:

-   Recipe planning
-   State management
-   Step navigation
-   Tool execution
-   Recipe modification

------------------------------------------------------------------------

## tools.py

Contains deterministic tools:

-   Timer manager
-   Timer status
-   Timer cancellation
-   Timer callbacks

------------------------------------------------------------------------

## memory.py

Contains memory-related functionality.

The current version focuses on useful active cooking context instead of
unnecessary memory extraction.

------------------------------------------------------------------------

## reflect.py

Contains validation logic for checking recipe consistency after
modifications.

------------------------------------------------------------------------

## voice/voice_shell.py

Main voice interface.

Connects:

-   LiveKit
-   Silero VAD
-   Deepgram STT
-   OpenAI
-   Rime TTS

Responsibilities:

-   Starts voice sessions
-   Handles speech
-   Provides greeting
-   Handles interruptions
-   Announces timer completion

------------------------------------------------------------------------

## voice/kitchen_bridge.py

Connects the voice layer with the cooking backend.

It allows the same Kitchen Agent brain to work with voice.

------------------------------------------------------------------------

# Installation

Clone:

    git clone https://github.com/Funda002/cooking_assistance_agent.git

    cd cooking_assistance_agent

Create environment:

    python -m venv myenv

Activate:

Windows:

    .\myenv\Scripts\Activate.ps1

Install dependencies:

    pip install -r requirements.txt

------------------------------------------------------------------------

# Environment Setup

Create:

    .env

Add:

    OPENAI_API_KEY=

    LIVEKIT_URL=
    LIVEKIT_API_KEY=
    LIVEKIT_API_SECRET=

    DEEPGRAM_API_KEY=

    rime_test_api=

Never upload API keys.

------------------------------------------------------------------------

# Running the Project

## 1. Terminal Agent

Run:

    python main.py

Example:

    User:
    I want to make an omelette.

    Agent:
    Step 1. Crack the eggs and add seasoning.

------------------------------------------------------------------------

## 2. Voice Agent

Run:

    python voice/voice_shell.py dev

The agent starts with:

    Hey! What would you like to cook today?

Then users can speak naturally.

------------------------------------------------------------------------

## 3. Evidence Testing

Run:

    python evidence_logger.py test1

Examples:

    python evidence_logger.py test1
    python evidence_logger.py test2
    python evidence_logger.py test3

These capture engineering validation runs.

------------------------------------------------------------------------

# Testing Performed

## Test 1 --- Normal Cooking Flow

Verified:

-   Recipe creation
-   Step navigation
-   Cooking guidance

------------------------------------------------------------------------

## Test 2 --- Voice Interruption

Verified:

-   User interruption
-   Generation cancellation
-   Conversation recovery

------------------------------------------------------------------------

## Test 3 --- Timer Workflow

Verified:

-   Timer creation
-   Background execution
-   Timer events during conversation

------------------------------------------------------------------------

# Engineering Challenges Solved

## Challenge 1: Maintaining Cooking State

Problem:

LLMs can lose track of steps.

Solution:

External state management using Python.

------------------------------------------------------------------------

## Challenge 2: Making Voice Agent Reliable

Problem:

Voice assistants need interruption handling and low latency.

Solution:

Separated voice interface from cooking intelligence.

------------------------------------------------------------------------

## Challenge 3: Real-Time Actions

Problem:

Cooking requires actions that happen later.

Solution:

Implemented deterministic tools such as timers.

------------------------------------------------------------------------

# Known Limitations

-   Complex recipe modifications may require deeper validation.
-   Very long spoken summaries can be shortened further.
-   More advanced long-term personalization can be added later.

------------------------------------------------------------------------

# Future Improvements

-   Vision-based ingredient detection
-   Kitchen camera integration
-   Personalized cooking preferences
-   Better recipe knowledge base
-   Multi-language voice support

------------------------------------------------------------------------

# Quick Commands

Terminal:

    python main.py

Voice:

    python voice/voice_shell.py dev

Install:

    pip install -r requirements.txt

Git:

    git add .
    git commit -m "update README"
    git push origin main

------------------------------------------------------------------------

# Project

## Kitchen Agent --- Voice-Native AI Cooking Assistant

Focus:

-   AI Agent Architecture
-   Planning
-   State Management
-   Tool Usage
-   Voice Interaction
-   Real-time Assistance

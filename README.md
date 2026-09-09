# 🍳 Kitchen Copilot

A simple **AI cooking agent** that guides users through a recipe one step at a time.

The user can ask questions, change ingredients, change serving size, set timers, and modify the recipe while cooking.

---

## 🎯 Project Goal

Build a conversational cooking assistant that behaves like an **agent**, not just a chatbot.

Example:

```text
User → "I want to make masala chai for 5 people"

Kitchen Copilot:
→ Creates a recipe plan
→ Tracks the current cooking step
→ Remembers ingredient constraints
→ Answers questions
→ Modifies the plan when needed
→ Runs timers in the background
→ Continues until cooking is complete
```

---

# 🧠 Core Concepts

## 1. LLM — Brain

The **LLM** understands the user's natural-language requests and decides what the agent should do.

Examples:

```text
"Can I add sugar now?"
"I don't have cardamom."
"Explain this step."
```

The LLM decides whether to answer, modify the recipe, or use a tool.

---

## 2. Plan — What Needs To Be Done

The recipe is represented as a structured plan.

```json
{
  "dish": "Masala Chai for 2",
  "servings": 2,
  "steps": [
    {
      "id": 1,
      "instruction": "Gather ingredients..."
    },
    {
      "id": 2,
      "instruction": "Boil the spices..."
    }
  ]
}
```

The plan can be modified during the conversation.

---

## 3. State — Where We Are

State tracks the current progress of the cooking task.

```python
state = {
    "current_step_id": 2,
    "completed_steps": [1],
    "status": "in_progress"
}
```

### Plan vs State

```text
PLAN  → What should happen?

STATE → What has already happened?
```

---

## 4. Memory — What We Remember

Memory stores useful information from the conversation.

```python
memory = {
    "conversation": [],
    "preferences": {},
    "facts": {}
}
```

Examples:

```text
User doesn't have cardamom
User has ginger powder
User is cooking for 5 people
```

Memory allows the agent to use information mentioned earlier.

---

## 5. Tools — Agent's Hands

Tools allow the agent to perform actions outside the LLM.

Current tools:

```text
Timer
Timer status
```

Example:

```text
User → "Set a timer for 2 minutes"

LLM → TOOL_CALL

Python → starts timer
```

The timer runs in the background, allowing the user to continue chatting.

---

## 6. Tool Registry

Tools are registered in one place:

```python
TOOLS = {
    "timer": timer,
    "timer_status": timer_status
}
```

This makes it easier to add future tools.

Possible future tools:

```text
Unit conversion
Ingredient substitution
Recipe search
Shopping list
Nutrition
```

---

## 7. Reflection

Reflection checks whether the current plan is still valid.

For example:

```text
Original plan:
Masala Chai for 2

User:
"I'm making it for 5 people."

Reflection:
→ Plan no longer matches the user's requirement.
```

The agent repairs the plan and verifies it again.

---

## 8. Agent Control Loop

The main agent follows this cycle:

```text
             User Message
                  │
                  ▼
             ┌──────────┐
             │   LLM    │
             └────┬─────┘
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
      ANSWER   TOOL_CALL  MODIFY_PLAN
        │         │         │
        │         ▼         ▼
        │       Tool       Plan
        │                   │
        └─────────┬─────────┘
                  ▼
                STATE
                  │
                  ▼
                MEMORY
                  │
                  └──────→ Next User Message
```

The important idea is:

> **The LLM decides; Python executes and maintains the real state.**

---

# 🛠️ Tech Stack

- **Python**
- **OpenAI API**
- **gpt-5-nano**
- **python-dotenv**
- **Threading** for background timers
- **JSON** for structured plans/state

---

# 📁 Project Structure

```text
kitchen_agent/
│
├── main.py          # Main agent and control loop
├── tools.py         # Timer and tool registry
├── memory.py        # Memory manager
├── reflect.py       # Plan reflection
├── .env             # API key
├── .gitignore
└── README.md
```

---

# ⚙️ Setup

### 1. Create virtual environment

```powershell
python -m venv myenv
```

### 2. Activate it

```powershell
.\myenv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install openai python-dotenv
```

### 4. Create `.env`

```env
OPENAI_API_KEY=your_api_key_here
```

### 5. Run

```powershell
python main.py
```

---

# 💬 Example

```text
What would you like to cook?

> I want to make masala chai for 5 people

→ Recipe plan generated

🍳 Step 1:
Gather the ingredients...

> I don't have cardamom

→ Plan modified

> Set a timer for 2 minutes

⏱️ Timer started

> How much time is left?

⏳ About 90 seconds left

> done

🍳 Step 2...

...

🎉 Cooking complete!
```

---

# 🚀 Current Features

- ✅ Recipe planning
- ✅ Step-by-step guidance
- ✅ Conversational questions
- ✅ State tracking
- ✅ Memory
- ✅ Ingredient substitutions
- ✅ Serving-size changes
- ✅ Plan modification
- ✅ Plan reflection and verification
- ✅ Background timers
- ✅ Timer status
- ✅ Natural conversation during timers
- ✅ Deterministic `next` / `done` handling

---

# 🔮 Future Improvements

- Streamlit frontend
- More cooking tools
- Persistent memory
- Better structured outputs
- Voice interaction
- FastAPI backend
- React frontend
- Database-based state
- More robust error handling

---

## 📌 Key Idea

Kitchen Copilot demonstrates the fundamental architecture of an AI agent:

**LLM + Plan + State + Memory + Tools + Control Loop + Reflection**

The goal is to understand how these components work together to create a practical conversational agent.

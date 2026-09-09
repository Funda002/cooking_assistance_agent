# 🍳 Kitchen Copilot

Kitchen Copilot is a simple **AI cooking agent** that guides a user through a recipe one step at a time.

The user can ask questions, change ingredients, change serving size, set timers, and modify the recipe while cooking.

---

## 🎯 Project Goal

The goal is to build a conversational cooking assistant that behaves like an **AI agent**, not just a chatbot.

Example:

```text
User → "I want to make masala chai for 5 people"

Kitchen Copilot:
→ Creates a cooking plan
→ Tracks the current cooking step
→ Remembers user constraints
→ Answers questions
→ Modifies the plan when needed
→ Runs timers in the background
→ Continues until cooking is complete
```

---

# 🧠 Core Concepts

## 1. LLM — Brain

The LLM understands natural-language requests and decides what the agent should do.

Examples:

```text
"Can I add sugar now?"
"I don't have cardamom."
"Explain this step."
```

The LLM can decide to answer, modify the plan, or use a tool.

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

State tracks the user's progress through the recipe.

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
→ Repair the plan.
→ Verify the repaired plan.
```

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
        │        Tool       Plan
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

> **The LLM decides; Python executes actions and maintains the real state.**

---

# 🛠️ Tech Stack

- **Python**
- **OpenAI API**
- **gpt-5-nano**
- **python-dotenv**
- **Threading** for background timers
- **JSON** for structured plans and state

---

# 📁 Project Structure

```text
kitchen_agent/
│
├── main.py          # Main agent and control loop
├── tools.py         # Timer and tool registry
├── memory.py        # Memory manager
├── reflect.py       # Plan reflection
├── .env             # API key (do not commit)
├── .gitignore       # Files excluded from Git
└── README.md
```

---

# ⚙️ Installation

## 1. Clone the repository

```powershell
git clone https://github.com/Funda002/cooking_assistance_agent.git
cd cooking_assistance_agent
```

If you already have the project locally, simply open PowerShell in the project folder:

```powershell
cd "C:\Users\SRI SARVESH\Documents\kitchen_agent"
```

---

## 2. Create a virtual environment

```powershell
python -m venv myenv
```

---

## 3. Activate the virtual environment

On Windows PowerShell:

```powershell
.\myenv\Scripts\Activate.ps1
```

You should see something similar to:

```text
(myenv) PS C:\Users\SRI SARVESH\Documents\kitchen_agent>
```

---

## 4. Install dependencies

Use:

```powershell
python -m pip install openai python-dotenv
```

Using `python -m pip` ensures the packages are installed into the active Python environment.

---

# 🔑 API Key Setup

Kitchen Copilot uses the OpenAI API.

Create a file named:

```text
.env
```

in the project root.

Add:

```env
OPENAI_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with your actual API key.

### ⚠️ Important

**Never commit `.env` to GitHub.**

The `.gitignore` file should contain:

```gitignore
.env
myenv/
__pycache__/
*.pyc
```

---

# ▶️ How to Run

After activating the virtual environment and setting your API key, run:

```powershell
python main.py
```

You should see:

```text
What would you like to cook?
>
```

Enter a cooking request, for example:

```text
I want to make masala chai for 5 people
```

Kitchen Copilot will generate a cooking plan and show the first step.

---

# 💬 Example Conversation

```text
What would you like to cook?

> I want to make masala chai for 5 people

Generated Plan:
...

🍳 Step 1:
Gather the ingredients...

> I don't have cardamom

🔄 Plan updated.

🍳 Step 1:
...

> done

🍳 Step 2:
...

> set timer for 2 minutes

⏱️ Timer started

> how much time is left?

⏳ About 90 seconds left

> done

🍳 Step 3:
...

🎉 Cooking complete!
```

---

# 🧪 Features

- ✅ Recipe planning
- ✅ Step-by-step cooking guidance
- ✅ Conversational questions
- ✅ State tracking
- ✅ Memory
- ✅ Ingredient substitutions
- ✅ Serving-size changes
- ✅ Dynamic plan modification
- ✅ Plan reflection and verification
- ✅ Background timers
- ✅ Timer status
- ✅ Conversation while timers run
- ✅ Deterministic `next` / `done` handling

---

# 🔮 Future Improvements

- Streamlit frontend
- More cooking tools
- Persistent memory
- Structured LLM outputs
- Voice interaction
- FastAPI backend
- React frontend
- Database-based state
- Better error handling

---

## 📌 Key Idea

Kitchen Copilot demonstrates the fundamental architecture of an AI agent:

**LLM + Plan + State + Memory + Tools + Control Loop + Reflection**

The project is intentionally kept simple so that each component of an AI agent can be understood and tested independently.

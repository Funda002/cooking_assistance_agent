import json
import re

from dotenv import load_dotenv
from openai import OpenAI

from memory import MemoryManager
from reflect import reflect_on_plan
from tools import TOOLS, timer_manager


# ==================================================
# CONFIGURATION
# ==================================================

MODEL = "gpt-5-nano"


# ==================================================
# CREATE PLAN
# ==================================================

def create_plan(client, user_request):

    prompt = f"""
You are the planning component of Kitchen Copilot.

Create a practical beginner-friendly cooking plan.

IMPORTANT:

- Understand the requested dish.
- Identify the requested number of servings if provided.
- If servings are not provided, choose a reasonable amount.
- The dish title must include the serving count when relevant.
- Make the ingredient quantities consistent with the serving count.
- Keep steps simple and sequential.
- Do not create unnecessary steps.

Return ONLY valid JSON.

Format:

{{
    "dish": "Masala Chai for 5",
    "servings": 5,
    "steps": [
        {{
            "id": 1,
            "instruction": "..."
        }}
    ]
}}

USER REQUEST:
{user_request}
"""

    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "developer",
                "content": prompt
            }
        ]
    )

    return json.loads(
        response.output_text
    )


# ==================================================
# GET CURRENT STEP
# ==================================================

def get_current_step(plan, current_step_id):

    for step in plan["steps"]:

        if step["id"] == current_step_id:
            return step

    return None


# ==================================================
# GET NEXT STEP
# ==================================================

def get_next_step(plan, state):

    completed = state[
        "completed_steps"
    ]

    for step in plan["steps"]:

        if step["id"] not in completed:

            return step

    return None


# ==================================================
# ADVANCE STEP
# ==================================================

def advance_step(plan, state):

    current_step_id = state[
        "current_step_id"
    ]

    if current_step_id not in state[
        "completed_steps"
    ]:

        state[
            "completed_steps"
        ].append(
            current_step_id
        )


    next_step = get_next_step(
        plan,
        state
    )


    if next_step:

        state[
            "current_step_id"
        ] = next_step["id"]

        return next_step

    state[
        "status"
    ] = "completed"

    return None


# ==================================================
# CHECK SIMPLE NEXT COMMAND
# ==================================================

def is_next_command(message):

    text = message.strip().lower()

    commands = {
        "next",
        "next step",
        "continue",
        "continue please",
        "let's continue",
        "lets continue",
        "move on",
        "go on",
        "what's next",
        "whats next",
        "what next"
    }

    return text in commands


# ==================================================
# CHECK DONE COMMAND
# ==================================================

def is_done_command(message):

    text = message.strip().lower()

    commands = {
        "done",
        "i'm done",
        "im done",
        "finished",
        "i finished",
        "completed",
        "complete"
    }

    return text in commands


# ==================================================
# DECIDE ACTION
# ==================================================

def decide_action(
    client,
    plan,
    state,
    memory,
    user_message
):

    live_timers = timer_manager.get_all_status()


    prompt = f"""
You are Kitchen Copilot.

You are a friendly cooking companion and teacher.

The user can talk naturally.

They may:
- ask questions
- ask about ingredients
- ask about timers
- ask for substitutions
- change serving size
- ask for explanations
- ask what comes next
- interrupt the cooking process
- say they are done

Do not force the user to only talk about the current step.

--------------------------------------------------
CURRENT PLAN
--------------------------------------------------

{json.dumps(plan, indent=2)}

--------------------------------------------------
CURRENT STATE
--------------------------------------------------

{json.dumps(state, indent=2)}

--------------------------------------------------
MEMORY
--------------------------------------------------

{json.dumps(memory, indent=2)}

--------------------------------------------------
REAL TIMER STATE
--------------------------------------------------

{json.dumps(live_timers, indent=2)}

The timer state comes from Python and is authoritative.

Never guess timer state.

--------------------------------------------------
ACTIONS
--------------------------------------------------

ANSWER

Use for normal questions and conversation.

{{
    "action": "ANSWER",
    "message": "friendly response"
}}


COMPLETE_STEP

Use when the user clearly says they finished the current step.

{{
    "action": "COMPLETE_STEP"
}}


ASK_USER

Use when genuinely important information is missing.

{{
    "action": "ASK_USER",
    "message": "question"
}}


TOOL_CALL

Available tools:

timer
timer_status

Start timer:

{{
    "action": "TOOL_CALL",
    "tool": "timer",
    "seconds": 60,
    "purpose": "brief purpose"
}}

Check timer:

{{
    "action": "TOOL_CALL",
    "tool": "timer_status"
}}


MODIFY_PLAN

Use when the actual recipe needs to change.

Examples:
- missing ingredient
- substitution
- serving count changed
- user preference changes the recipe

Return:

{{
    "action": "MODIFY_PLAN",
    "reason": "reason",
    "remove_steps": [],
    "replace_steps": [
        {{
            "step_id": 1,
            "new_instruction": "clean final instruction"
        }}
    ]
}}

IMPORTANT:

When replacing a step, write the FINAL instruction.

Do not leave unnecessary alternatives such as:

"If you have X..."
"If you are using Y..."

unless the user genuinely has multiple options.

Use the user's known facts.

--------------------------------------------------
NAVIGATION
--------------------------------------------------

If the user says "next", "continue", "what's next",
or similar, the Python program handles the navigation.

Do NOT pretend the step advanced.

For ordinary questions about the next step,
you may ANSWER.

--------------------------------------------------
TIMER
--------------------------------------------------

If the user asks:

"How much time is left?"

use timer_status.

Do not calculate remaining time yourself.

--------------------------------------------------
PERSONALITY
--------------------------------------------------

Be friendly and conversational.

Do not sound robotic.

Do not repeatedly say "say done".

Do not unnecessarily advance the recipe.

Return ONLY valid JSON.

USER MESSAGE:
{user_message}
"""

    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "developer",
                "content": prompt
            }
        ]
    )


    try:

        return json.loads(
            response.output_text
        )

    except json.JSONDecodeError:

        return {
            "action": "ANSWER",
            "message": response.output_text
        }


# ==================================================
# MEMORY EXTRACTION
# ==================================================

def extract_memory(client, user_message):

    prompt = f"""
Extract useful information from the user's message.

Possible categories:

preference
fact

Examples:

"I don't like cardamom"

{{
    "preference": {{
        "dislikes": "cardamom"
    }},
    "fact": {{}}
}}

"I don't have ginger"

{{
    "preference": {{}},
    "fact": {{
        "ginger_available": false
    }}
}}

"I have ginger powder"

{{
    "preference": {{}},
    "fact": {{
        "ginger_powder_available": true
    }}
}}

"I am cooking for five people"

{{
    "preference": {{}},
    "fact": {{
        "servings": 5
    }}
}}

If nothing should be remembered:

{{
    "preference": {{}},
    "fact": {{}}
}}

Return ONLY valid JSON.

USER MESSAGE:
{user_message}
"""

    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "developer",
                "content": prompt
            }
        ]
    )


    try:

        return json.loads(
            response.output_text
        )

    except json.JSONDecodeError:

        return {
            "preference": {},
            "fact": {}
        }


# ==================================================
# STORE MEMORY
# ==================================================

def store_memory(memory, extracted):

    changed = False


    preferences = extracted.get(
        "preference",
        {}
    )

    facts = extracted.get(
        "fact",
        {}
    )


    for key, value in preferences.items():

        if memory.memory[
            "preferences"
        ].get(key) != value:

            memory.store_preference(
                key,
                value
            )

            changed = True


    for key, value in facts.items():

        if memory.memory[
            "facts"
        ].get(key) != value:

            memory.store_fact(
                key,
                value
            )

            changed = True


    return changed


# ==================================================
# MODIFY PLAN
# ==================================================

def modify_plan(plan, decision):

    remove_steps = decision.get(
        "remove_steps",
        []
    )

    replace_steps = decision.get(
        "replace_steps",
        []
    )


    if remove_steps:

        plan["steps"] = [
            step
            for step in plan["steps"]
            if step["id"] not in remove_steps
        ]


    for change in replace_steps:

        step_id = change.get(
            "step_id"
        )

        instruction = change.get(
            "new_instruction"
        )


        if not instruction:
            continue


        for step in plan["steps"]:

            if step["id"] == step_id:

                step[
                    "instruction"
                ] = instruction

                break


    return plan


# ==================================================
# UPDATE PLAN METADATA
# ==================================================

def update_plan_metadata(
    client,
    plan,
    memory
):

    servings = memory.memory[
        "facts"
    ].get(
        "servings"
    )


    if not servings:
        return plan


    current_servings = plan.get(
        "servings"
    )


    if current_servings == servings:
        return plan


    # Update metadata deterministically
    plan["servings"] = servings


    dish = plan.get(
        "dish",
        "Recipe"
    )


    # Remove previous serving suffix
    dish = re.sub(
        r"\s+for\s+\d+\s*$",
        "",
        dish,
        flags=re.IGNORECASE
    )


    plan["dish"] = (
        f"{dish} for {servings}"
    )


    return plan


# ==================================================
# REFLECTION + REPAIR
# ==================================================

def validate_and_repair_plan(
    client,
    plan,
    state,
    memory
):

    reflection = reflect_on_plan(
        client,
        plan,
        state,
        memory
    )


    if not reflection.get(
        "problem"
    ):

        return plan, reflection


    repair_prompt = f"""
Repair the cooking plan.

Problem detected:

{json.dumps(
    reflection,
    indent=2
)}

CURRENT PLAN:

{json.dumps(
    plan,
    indent=2
)}

MEMORY:

{json.dumps(
    memory,
    indent=2
)}

Fix the actual inconsistency.

If the serving count changed:
- update the dish title
- update servings
- update affected quantities

If an ingredient is unavailable:
- remove it or replace it with a confirmed available ingredient

Do not invent ingredients.

Return ONLY valid JSON:

{{
    "dish": "updated dish title",
    "servings": 5,
    "steps": [
        {{
            "id": 1,
            "instruction": "final clean instruction"
        }}
    ]
}}
"""


    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "developer",
                "content": repair_prompt
            }
        ]
    )


    try:

        repaired_plan = json.loads(
            response.output_text
        )

    except json.JSONDecodeError:

        return plan, reflection


    # Verify repair

    verification = reflect_on_plan(
        client,
        repaired_plan,
        state,
        memory
    )


    if verification.get(
        "problem"
    ):

        print(
            "\n⚠️ Plan still has a conflict:"
        )

        print(
            json.dumps(
                verification,
                indent=2
            )
        )

    else:

        print(
            "\n✅ Plan repaired and verified."
        )


    return repaired_plan, verification


# ==================================================
# FORMAT TIMER RESPONSE
# ==================================================

def format_timer_response(result):

    if result is None:

        return (
            "I couldn't check the timer."
        )


    status = result.get(
        "status"
    )


    if status == "running":

        remaining = result.get(
            "remaining_seconds",
            0
        )

        purpose = result.get(
            "purpose",
            "cooking"
        )


        if remaining <= 1:

            return (
                f"⏳ Almost done! "
                f"About 1 second left for "
                f"{purpose}."
            )


        return (
            f"⏳ About {remaining} seconds "
            f"left for {purpose}."
        )


    if status == "finished":

        purpose = result.get(
            "purpose",
            "cooking"
        )

        duration = result.get(
            "duration_seconds",
            0
        )

        return (
            f"⏰ That timer is already finished. "
            f"Your {duration}-second timer for "
            f"{purpose} is done."
        )


    if status == "no_timer":

        return (
            "You don't have any timers yet."
        )


    if status == "not_found":

        return (
            "I couldn't find that timer."
        )


    return (
        "I couldn't determine the timer status."
    )


# ==================================================
# EXECUTE TOOL
# ==================================================

def execute_tool(
    decision,
    state
):

    tool_name = decision.get(
        "tool"
    )


    tool = TOOLS.get(
        tool_name
    )


    if tool is None:

        return {
            "error": (
                f"Unknown tool: {tool_name}"
            )
        }


    try:

        # ------------------------------------------
        # TIMER
        # ------------------------------------------

        if tool_name == "timer":

            seconds = decision.get(
                "seconds"
            )

            purpose = decision.get(
                "purpose",
                "cooking timer"
            )

            step_id = state.get(
                "current_step_id"
            )


            if (
                not isinstance(seconds, int)
                or seconds <= 0
            ):

                return {
                    "error": (
                        "Invalid timer value."
                    )
                }


            return tool(
                seconds,
                purpose,
                step_id
            )


        # ------------------------------------------
        # TIMER STATUS
        # ------------------------------------------

        if tool_name == "timer_status":

            timer_id = decision.get(
                "timer_id"
            )


            return tool(
                timer_id
            )


        return {
            "error": (
                f"No handler for "
                f"{tool_name}"
            )
        }


    except Exception as e:

        return {
            "error": str(e)
        }


# ==================================================
# PRINT CURRENT STEP
# ==================================================

def print_current_step(
    plan,
    state
):

    if state[
        "status"
    ] == "completed":

        print(
            "\n🎉 Cooking complete!"
        )

        return


    step = get_current_step(
        plan,
        state["current_step_id"]
    )


    if step:

        print(
            f"\n🍳 Step {step['id']}: "
            f"{step['instruction']}"
        )


# ==================================================
# PRINT REMAINING STEPS
# ==================================================

def print_remaining_steps(
    plan,
    state
):

    current_id = state[
        "current_step_id"
    ]

    completed = state[
        "completed_steps"
    ]


    remaining = [
        step
        for step in plan["steps"]
        if (
            step["id"] != current_id
            and step["id"] not in completed
        )
    ]


    if not remaining:

        return (
            "There are no later steps remaining."
        )


    lines = [
        "After your current step:"
    ]


    for step in remaining:

        lines.append(
            f"Step {step['id']}: "
            f"{step['instruction']}"
        )


    return "\n".join(lines)


# ==================================================
# MAIN
# ==================================================

def main():

    load_dotenv()

    client = OpenAI()

    memory = MemoryManager()


    # ----------------------------------------------
    # INITIAL REQUEST
    # ----------------------------------------------

    user_request = input(
        "What would you like to cook?\n> "
    )


    # ----------------------------------------------
    # PLAN
    # ----------------------------------------------

    plan = create_plan(
        client,
        user_request
    )


    print("\nGenerated Plan:")

    print(
        json.dumps(
            plan,
            indent=2
        )
    )


    # ----------------------------------------------
    # STATE
    # ----------------------------------------------

    state = {

        "current_step_id":
            plan["steps"][0]["id"],

        "completed_steps": [],

        "status":
            "in_progress"
    }


    print_current_step(
        plan,
        state
    )


    # ==============================================
    # AGENT LOOP
    # ==============================================

    while state[
        "status"
    ] == "in_progress":


        user_message = input(
            "\nYou:\n> "
        )


        # ------------------------------------------
        # EMPTY MESSAGE
        # ------------------------------------------

        if not user_message.strip():

            continue


        # ------------------------------------------
        # DETERMINISTIC NAVIGATION
        # ------------------------------------------

        if is_next_command(
            user_message
        ):

            next_step = advance_step(
                plan,
                state
            )


            if next_step:

                print(
                    "\n👍 Got it. Let's move on."
                )

                print_current_step(
                    plan,
                    state
                )

            else:

                print(
                    "\n🎉 That's the end of the recipe!"
                )


            continue


        # ------------------------------------------
        # MEMORY
        # ------------------------------------------

        extracted_memory = extract_memory(
            client,
            user_message
        )


        memory_changed = store_memory(
            memory,
            extracted_memory
        )


        memory.store_conversation(
            user_message,
            ""
        )


        # ------------------------------------------
        # PLAN METADATA UPDATE
        # ------------------------------------------

        if memory_changed:

            plan = update_plan_metadata(
                client,
                plan,
                memory
            )


            # --------------------------------------
            # REFLECTION
            # --------------------------------------

            plan, reflection = (
                validate_and_repair_plan(
                    client,
                    plan,
                    state,
                    memory.retrieve()
                )
            )


        # ------------------------------------------
        # SPECIAL REMAINING-STEPS REQUEST
        # ------------------------------------------

        lower_message = (
            user_message
            .strip()
            .lower()
        )


        if (
            "summarize the remaining"
            in lower_message
            or
            "remaining steps"
            in lower_message
            or
            "what are the remaining steps"
            in lower_message
        ):

            print(
                "\n🤖 "
                + print_remaining_steps(
                    plan,
                    state
                )
            )

            continue


        # ------------------------------------------
        # DONE
        # ------------------------------------------

        if is_done_command(
            user_message
        ):

            next_step = advance_step(
                plan,
                state
            )


            if next_step:

                print_current_step(
                    plan,
                    state
                )

            else:

                print(
                    "\n🎉 Cooking complete!"
                )

            continue


        # ------------------------------------------
        # LLM DECISION
        # ------------------------------------------

        decision = decide_action(
            client,
            plan,
            state,
            memory.retrieve(),
            user_message
        )


        print(
            "\n🤖 Decision:"
        )

        print(
            json.dumps(
                decision,
                indent=2
            )
        )


        action = decision.get(
            "action"
        )


        # ------------------------------------------
        # ANSWER
        # ------------------------------------------

        if action == "ANSWER":

            message = decision.get(
                "message",
                ""
            )


            # Avoid allowing the LLM to
            # secretly advance the workflow.

            print(
                f"\n🤖 {message}"
            )


        # ------------------------------------------
        # ASK USER
        # ------------------------------------------

        elif action == "ASK_USER":

            message = decision.get(
                "message",
                ""
            )


            print(
                f"\n🤖 {message}"
            )


        # ------------------------------------------
        # COMPLETE STEP
        # ------------------------------------------

        elif action == "COMPLETE_STEP":

            next_step = advance_step(
                plan,
                state
            )


            if next_step:

                print_current_step(
                    plan,
                    state
                )

            else:

                print(
                    "\n🎉 Cooking complete!"
                )


        # ------------------------------------------
        # TOOL
        # ------------------------------------------

        elif action == "TOOL_CALL":

            result = execute_tool(
                decision,
                state
            )


            if (
                decision.get("tool")
                == "timer_status"
            ):

                print(
                    "\n🤖 "
                    + format_timer_response(
                        result
                    )
                )

            else:

                print(
                    "\n🔧 Tool result:"
                )

                print(
                    json.dumps(
                        result,
                        indent=2
                    )
                )


        # ------------------------------------------
        # MODIFY PLAN
        # ------------------------------------------

        elif action == "MODIFY_PLAN":

            plan = modify_plan(
                plan,
                decision
            )


            plan, reflection = (
                validate_and_repair_plan(
                    client,
                    plan,
                    state,
                    memory.retrieve()
                )
            )


            print(
                "\n🔄 Plan updated."
            )


            print_current_step(
                plan,
                state
            )


        # ------------------------------------------
        # UNKNOWN
        # ------------------------------------------

        else:

            print(
                "\n❌ Unknown action."
            )


# ==================================================
# ENTRY POINT
# ==================================================

if __name__ == "__main__":

    main()
import json
from openai import OpenAI


MODEL = "gpt-5-nano"


def reflect_on_plan(client, plan, state, memory):

    prompt = f"""
You are the reflection component of Kitchen Copilot.

Your job is to check whether the current cooking plan is
still valid given the current state and memory.

Do NOT modify the plan yourself.

Only identify whether a problem exists.

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
CHECK FOR
--------------------------------------------------

1. Missing ingredients

Example:

Plan requires tomatoes.
Memory says tomatoes are unavailable.

This is a problem.

2. Invalid quantities

Example:

Plan requires 3 eggs.
Memory says user has only 1 egg.

This is a problem.

3. Completed steps

Make sure the current step has not already been completed.

4. User preferences

Example:

Plan says oil.
Memory says user prefers ghee.

This may require updating the plan.

5. Other contradictions between the plan,
state and memory.

--------------------------------------------------
OUTPUT
--------------------------------------------------

Return ONLY valid JSON.

If everything is fine:

{{
    "problem": false,
    "reason": ""
}}

If a problem exists:

{{
    "problem": true,
    "reason": "Tomatoes are required by step 5 but memory says tomatoes are unavailable.",
    "severity": "medium"
}}
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

    result_text = response.output_text

    try:

        return json.loads(result_text)

    except json.JSONDecodeError:

        print("\nReflection returned invalid JSON.")

        print(result_text)

        return {
            "problem": False,
            "reason": ""
        }
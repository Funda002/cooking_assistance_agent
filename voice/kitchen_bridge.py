# voice/kitchen_bridge.py

import logging
import re
import threading

from main import (
    create_plan,
    get_current_step,
    advance_step,
    is_next_command,
    is_done_command,
    decide_action,
    execute_tool,
    modify_plan,
    print_remaining_steps,
)

from tools import timer_manager


logger = logging.getLogger("kitchen_agent.voice.bridge")

# BUILD 2: returned by stale work so the voice layer never speaks it.
STALE_RESPONSE = "__KITCHEN_AGENT_STALE__"


# ============================================================
# VOICE TEXT HELPERS
# ============================================================

def clean_voice_text(text):
    """
    Clean text before sending it to TTS.
    """

    if not text:
        return ""

    text = str(text)

    # Remove markdown bullets
    text = re.sub(
        r"^\s*[-*•]\s*",
        "",
        text,
        flags=re.MULTILINE
    )

    # Remove markdown emphasis
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("`", "")

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def split_sentences(text):

    text = clean_voice_text(text)

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def voice_shorten(
    text,
    max_sentences=2,
    max_chars=260,
):
    """
    Voice presentation layer only.

    Does NOT change cooking state.
    Does NOT call another LLM.
    """

    text = clean_voice_text(text)

    if not text:
        return ""

    sentences = split_sentences(text)

    if not sentences:
        return ""

    selected = sentences[:max_sentences]

    result = " ".join(selected)

    if len(result) > max_chars:

        result = result[:max_chars]

        if " " in result:
            result = result.rsplit(" ", 1)[0]

        result += "."

    return result.strip()


def voice_step(step):

    if not step:
        return "I don't have an active cooking step right now."

    step_id = step.get("id", "")

    instruction = clean_voice_text(
        step.get("instruction", "")
    )

    if not instruction:
        return f"Step {step_id}."

    return voice_shorten(
        f"Step {step_id}. {instruction}",
        max_sentences=2,
        max_chars=260
    )


# ============================================================
# KITCHEN AGENT BRIDGE
# ============================================================

class KitchenAgentBridge:

    def __init__(self):

        self.client = None

        self.plan = None

        self.state = {
            "status": "idle",
            "current_step_id": None,
            "completed_steps": [],
        }

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # We deliberately DO NOT use the old long-term
        # MemoryManager here.
        #
        # Cooking V1 only needs PLAN + STATE.
        # ----------------------------------------------------

        self.session_memory = {}

        self.started = False

        # ========================================================
        # BUILD 2: STALE-RESPONSE GENERATION
        # ========================================================
        #
        # Every new voice turn gets a generation number.
        # If a newer turn arrives, older work becomes stale.
        #
        self._generation = 0

        # Protect generation checks together with state commits.
        self._generation_lock = threading.RLock()

        logger.info(
            "KitchenAgentBridge initialized."
        )

    # ========================================================
    # OPENAI CLIENT
    # ========================================================

    def _get_client(self):

        if self.client is None:

            from openai import OpenAI
            from dotenv import load_dotenv
            import os

            load_dotenv()

            self.client = OpenAI(
                api_key=os.getenv(
                    "OPENAI_API_KEY"
                )
            )

        return self.client

    # ========================================================
    # CURRENT STEP
    # ========================================================

    def _current_step(self):

        if not self.plan:
            return None

        current_step_id = self.state.get(
            "current_step_id"
        )

        if current_step_id is None:
            return None

        return get_current_step(
            self.plan,
            current_step_id
        )

    # ========================================================
    # CURRENT STEP RESPONSE
    # ========================================================

    def _current_step_response(self):

        return voice_step(
            self._current_step()
        )

    # ========================================================
    # START RECIPE
    # ========================================================

    def _start_recipe(self, user_message, generation=None):

        client = self._get_client()

        logger.info(
            "Creating recipe plan for: %s",
            user_message
        )

        new_plan = create_plan(
            client,
            user_message
        )

        # Never commit a recipe created for an older turn.
        if generation is not None and not self.is_generation_current(generation):
            logger.warning(
                "BUILD 2 → Discarding stale recipe generation %s",
                generation,
            )
            return STALE_RESPONSE

        if not new_plan:
            return (
                "I couldn't create the recipe plan. "
                "Please try again."
            )

        if not new_plan.get("steps"):
            return (
                "I couldn't find any cooking steps "
                "for that recipe."
            )

        first_step_id = new_plan["steps"][0]["id"]

        # Atomic generation check + state commit.
        # A newer turn cannot invalidate this between the check and commit.
        if generation is not None:
            with self._generation_lock:
                if generation != self._generation:
                    logger.warning(
                        "BUILD 2 → Discarding stale recipe generation %s before state commit",
                        generation,
                    )
                    return STALE_RESPONSE

                self.plan = new_plan
                self.state = {
                    "status": "cooking",
                    "current_step_id": first_step_id,
                    "completed_steps": [],
                }
                self.session_memory = {
                    "recipe_started": True,
                    "servings": new_plan.get("servings"),
                }
                self.started = True
        else:
            self.plan = new_plan
            self.state = {
                "status": "cooking",
                "current_step_id": first_step_id,
                "completed_steps": [],
            }
            self.session_memory = {
                "recipe_started": True,
                "servings": new_plan.get("servings"),
            }
            self.started = True

        logger.info(
            "Recipe created: %s",
            self.plan.get("dish")
        )

        logger.info(
            "Starting step: %s",
            first_step_id
        )

        return self._current_step_response()

    # ========================================================
    # NATURAL NEXT DETECTION
    # ========================================================

    def _is_natural_next(self, message):

        text = clean_voice_text(
            message
        ).lower()

        # Remove punctuation that STT may add.
        normalized = re.sub(
            r"[.,!?]",
            "",
            text
        ).strip()

        phrases = {

            "next",
            "next step",
            "continue",
            "continue please",
            "move on",
            "go on",
            "go ahead",
            "what next",
            "whats next",
            "what do i do next",
            "what should i do next",
            "what do we do next",
            "what should we do next",
            "what comes next",
            "what is next",
            "what is the next step",
            "what was the next step",

            "lets continue",
            "let's continue",
            "let us continue",

            "lets proceed",
            "let's proceed",
            "let us proceed",

            "we can proceed",
            "we can continue",
            "continue on that",
            "continue with that",

            "move to the next step",
            "go to the next step",

            "okay continue",
            "okay lets continue",
            "okay let's continue",

            "yes continue",
            "yes lets continue",
            "yes let's continue",

            "i'm ready",
            "im ready",
            "ready",

        }

        if normalized in phrases:
            return True

        # ----------------------------------------------------
        # Natural speech patterns.
        #
        # Examples:
        #
        # "I added the onions, what's next?"
        # "Okay, what do I do now?"
        # "Alright, let's go to the next step."
        # ----------------------------------------------------

        next_patterns = [

            r"\bwhat('?s| is) next\b",
            r"\bwhat do i do now\b",
            r"\bwhat should i do now\b",
            r"\bwhat do we do now\b",
            r"\bwhat comes next\b",
            r"\bgo to the next step\b",
            r"\bmove to the next step\b",
            r"\blet'?s go next\b",
            r"\bwe can go next\b",
            r"\bcan we go next\b",
            r"\bwhat next\b",

        ]

        return any(
            re.search(
                pattern,
                normalized
            )
            for pattern in next_patterns
        )

    # ========================================================
    # TIMER CANCEL DETECTION
    # ========================================================

    def _is_timer_cancel_request(self, message):

        text = clean_voice_text(
            message
        ).lower()

        text = re.sub(
            r"[.,!?]",
            "",
            text
        ).strip()

        patterns = [

            r"\bstop the timer\b",
            r"\bstop timer\b",
            r"\bcancel the timer\b",
            r"\bcancel timer\b",
            r"\bstop my timer\b",
            r"\bcancel my timer\b",
            r"\bdon't want the timer\b",
            r"\bdont want the timer\b",
            r"\bremove the timer\b",

        ]

        return any(
            re.search(
                pattern,
                text
            )
            for pattern in patterns
        )

    # ========================================================
    # CANCEL TIMER
    # ========================================================

    def _cancel_timer(self):

        result = timer_manager.cancel_timer()

        if not result:
            return "I couldn't cancel the timer."

        if result.get("status") == "cancelled":

            purpose = result.get(
                "purpose",
                "cooking"
            )

            return (
                f"Okay, I've cancelled the timer for {purpose}."
            )

        if result.get("status") == "no_timer":

            return "There isn't an active timer."

        return (
            result.get(
                "message",
                "I couldn't cancel the timer."
            )
        )

    # ========================================================
    # NEXT STEP
    # ========================================================

    def _advance(self, generation=None):

        if generation is not None and not self.is_generation_current(generation):
            logger.warning(
                "BUILD 2 → Discarding stale advance generation %s",
                generation,
            )
            return STALE_RESPONSE

        if not self.plan:

            return (
                "We haven't started cooking yet."
            )

        next_step = advance_step(
            self.plan,
            self.state
        )

        if next_step:

            logger.info(
                "Advanced to step %s",
                next_step.get("id")
            )

            return voice_step(
                next_step
            )

        return (
            "That's it. Your dish is ready!"
        )

    # ========================================================
    # DONE
    # ========================================================

    def _done(self, generation=None):

        if generation is not None and not self.is_generation_current(generation):
            logger.warning(
                "BUILD 2 → Discarding stale done generation %s",
                generation,
            )
            return STALE_RESPONSE

        if not self.plan:

            return (
                "We haven't started cooking yet."
            )

        next_step = advance_step(
            self.plan,
            self.state
        )

        if next_step:

            return voice_step(
                next_step
            )

        return (
            "Great job. Your dish is complete!"
        )

    # ========================================================
    # PROTECT STATE AFTER PLAN MODIFICATION
    # ========================================================

    def _protect_state_after_plan_change(
        self,
        old_current_step_id,
        old_completed_steps,
    ):
        """
        Critical V1 state protection.

        Modifying a recipe must NEVER send the user
        back to Step 1.
        """

        if not self.plan:
            return

        available_ids = {
            step["id"]
            for step in self.plan.get(
                "steps",
                []
            )
        }

        # ----------------------------------------------------
        # Preserve completed steps that still exist.
        # ----------------------------------------------------

        self.state[
            "completed_steps"
        ] = [
            step_id
            for step_id in old_completed_steps
            if step_id in available_ids
        ]

        # ----------------------------------------------------
        # Preserve current step if it still exists.
        # ----------------------------------------------------

        if old_current_step_id in available_ids:

            self.state[
                "current_step_id"
            ] = old_current_step_id

            return

        # ----------------------------------------------------
        # If the current step was removed, find the first
        # remaining step that has not been completed.
        #
        # NEVER blindly use steps[0].
        # ----------------------------------------------------

        for step in self.plan.get(
            "steps",
            []
        ):

            if step["id"] not in self.state[
                "completed_steps"
            ]:

                self.state[
                    "current_step_id"
                ] = step["id"]

                return

        # ----------------------------------------------------
        # Everything is complete.
        # ----------------------------------------------------

        self.state[
            "status"
        ] = "completed"

        self.state[
            "current_step_id"
        ] = None

    # ========================================================
    # ANSWER RESPONSE
    # ========================================================

    def _voice_answer(self, message):

        if not message:

            return (
                "I'm not sure about that."
            )

        return voice_shorten(
            message,
            max_sentences=2,
            max_chars=260
        )

    # ========================================================
    # ASK USER RESPONSE
    # ========================================================

    def _voice_question(self, message):

        if not message:

            return (
                "Could you clarify that?"
            )

        return voice_shorten(
            message,
            max_sentences=1,
            max_chars=180
        )

    # ========================================================
    # MODIFY PLAN RESPONSE
    # ========================================================

    def _voice_plan_modified(
        self,
        decision
    ):

        replacement_count = len(
            decision.get(
                "replace_steps",
                []
            )
        )

        removal_count = len(
            decision.get(
                "remove_steps",
                []
            )
        )

        if replacement_count or removal_count:

            confirmation = (
                "Got it. I've updated the recipe."
            )

        else:

            confirmation = (
                "Got it. I've adjusted the recipe."
            )

        current_step = self._current_step()

        if current_step:

            return (
                confirmation
                + " "
                + voice_step(current_step)
            )

        return confirmation

    # ========================================================
    # TIMER RESPONSE
    # ========================================================

    def _voice_timer_result(
        self,
        result
    ):

        if not result:

            return (
                "I couldn't check the timer."
            )

        try:

            from main import format_timer_response

            response = format_timer_response(
                result
            )

            return voice_shorten(
                response,
                max_sentences=1,
                max_chars=160
            )

        except Exception as e:

            logger.warning(
                "Timer formatting failed: %s",
                e
            )

            return (
                "I couldn't check the timer."
            )

    # ========================================================
    # BUILD 2: GENERATION CONTROL
    # ========================================================

    def start_generation(self):
        """
        Start a new logical voice turn.

        Any older generation is now considered stale.
        """
        with self._generation_lock:
            self._generation += 1
            generation = self._generation

        logger.info(
            "BUILD 2 → Started generation %s",
            generation
        )

        return generation

    def is_generation_current(self, generation):
        """
        Check whether this generation is still the latest turn.
        """
        with self._generation_lock:
            return generation == self._generation

    def invalidate_generation(self, reason=""):
        """
        Invalidate all work belonging to the previous voice turn.

        This is logical cancellation/fencing: Python worker threads are not
        forcibly killed, but stale work is prevented from being committed or
        spoken after a newer turn arrives.
        """
        with self._generation_lock:
            self._generation += 1
            new_generation = self._generation

        logger.warning(
            "BUILD 2 → Invalidated generation; now %s (%s)",
            new_generation,
            reason or "newer user turn",
        )
        return new_generation

    # ========================================================
    # MAIN PROCESS FUNCTION
    # ========================================================

    def process(self, user_message, generation=None):

        try:

            user_message = (
                user_message or ""
            ).strip()

            if not user_message:

                return (
                    "Sorry, I didn't catch that."
                )

            if generation is not None and not self.is_generation_current(generation):
                logger.warning(
                    "BUILD 2 → Ignoring stale request generation %s",
                    generation,
                )
                return STALE_RESPONSE

            logger.info(
                "Processing voice input: %s",
                user_message
            )

            # =================================================
            # 1. NO ACTIVE PLAN
            # =================================================

            if self.plan is None:

                return self._start_recipe(
                    user_message,
                    generation,
                )

            # =================================================
            # 2. TIMER CANCEL
            #
            # Deterministic.
            # No LLM call.
            # =================================================

            if self._is_timer_cancel_request(
                user_message
            ):

                logger.info(
                    "Deterministic timer cancellation."
                )

                if generation is not None and not self.is_generation_current(generation):
                    return STALE_RESPONSE

                return self._cancel_timer()

            # =================================================
            # 3. NEXT COMMAND
            #
            # Deterministic.
            # =================================================

            if (
                is_next_command(
                    user_message
                )
                or
                self._is_natural_next(
                    user_message
                )
            ):

                logger.info(
                    "Deterministic next command."
                )

                return self._advance(generation)

            # =================================================
            # 4. DONE COMMAND
            # =================================================

            if is_done_command(
                user_message
            ):

                logger.info(
                    "Deterministic done command."
                )

                return self._done(generation)

            # =================================================
            # 5. REMAINING STEPS
            # =================================================

            lower_message = (
                user_message.lower()
            )

            if (
                "remaining steps"
                in lower_message
                or
                "what are the remaining steps"
                in lower_message
                or
                "summarize the remaining"
                in lower_message
            ):

                response = print_remaining_steps(
                    self.plan,
                    self.state
                )

                return voice_shorten(
                    response,
                    max_sentences=2,
                    max_chars=260
                )

            # =================================================
            # 6. LLM DECISION
            #
            # IMPORTANT:
            # No memory extraction call.
            # The current PLAN + STATE are the source of truth.
            # =================================================

            client = self._get_client()

            if generation is not None and not self.is_generation_current(generation):
                logger.warning(
                    "BUILD 2 → Discarding stale generation %s before LLM decision",
                    generation,
                )
                return STALE_RESPONSE

            decision = decide_action(
                client,
                self.plan,
                self.state,
                {},                 # No unwanted long-term memory
                user_message
            )

            logger.info(
                "Kitchen decision: %s",
                decision
            )

            if generation is not None and not self.is_generation_current(generation):
                logger.warning(
                    "BUILD 2 → Discarding stale generation %s after LLM decision",
                    generation,
                )
                return STALE_RESPONSE

            action = decision.get(
                "action"
            )

            # =================================================
            # 7. ANSWER
            # =================================================

            if action == "ANSWER":

                return self._voice_answer(
                    decision.get(
                        "message",
                        ""
                    )
                )

            # =================================================
            # 8. ASK USER
            # =================================================

            if action == "ASK_USER":

                return self._voice_question(
                    decision.get(
                        "message",
                        ""
                    )
                )

            # =================================================
            # 9. COMPLETE STEP
            # =================================================

            if action == "COMPLETE_STEP":

                if generation is not None and not self.is_generation_current(generation):
                    logger.warning(
                        "BUILD 2 → Discarding stale COMPLETE_STEP generation %s",
                        generation,
                    )
                    return STALE_RESPONSE

                next_step = advance_step(
                    self.plan,
                    self.state
                )

                if next_step:

                    return voice_step(
                        next_step
                    )

                return (
                    "Great job. Your dish is complete!"
                )

            # =================================================
            # 10. TOOL CALL
            # =================================================

            if action == "TOOL_CALL":

                if generation is not None and not self.is_generation_current(generation):
                    logger.warning(
                        "BUILD 2 → Discarding stale TOOL_CALL generation %s before execution",
                        generation,
                    )
                    return STALE_RESPONSE

                result = execute_tool(
                    decision,
                    self.state
                )

                tool_name = decision.get(
                    "tool"
                )

                if generation is not None and not self.is_generation_current(generation):
                    logger.warning(
                        "BUILD 2 → Tool result became stale for generation %s",
                        generation,
                    )
                    return STALE_RESPONSE

                # -----------------------------
                # TIMER STATUS
                # -----------------------------

                if tool_name == "timer_status":

                    return self._voice_timer_result(
                        result
                    )

                # -----------------------------
                # TIMER START
                # -----------------------------

                if tool_name == "timer":

                    if isinstance(
                        result,
                        dict
                    ):

                        message = result.get(
                            "message"
                        )

                        if message:

                            return voice_shorten(
                                message,
                                max_sentences=1,
                                max_chars=140
                            )

                    return "Timer started."

                return "Done."

            # =================================================
            # 11. MODIFY PLAN
            # =================================================

            if action == "MODIFY_PLAN":

                # ---------------------------------------------
                # SAVE STATE BEFORE modification.
                # ---------------------------------------------

                old_current_step_id = (
                    self.state.get(
                        "current_step_id"
                    )
                )

                old_completed_steps = list(
                    self.state.get(
                        "completed_steps",
                        []
                    )
                )

                logger.info(
                    "Plan modification requested at step %s",
                    old_current_step_id
                )

                if generation is not None and not self.is_generation_current(generation):
                    logger.warning(
                        "BUILD 2 → Discarding stale MODIFY_PLAN generation %s",
                        generation,
                    )
                    return STALE_RESPONSE

                # ---------------------------------------------
                # Modify existing plan.
                # ---------------------------------------------

                # Build the candidate plan first. Do not mutate the live
                # plan until we have re-checked the generation.
                candidate_plan = modify_plan(
                    self.plan,
                    decision
                )

                if generation is not None:
                    with self._generation_lock:
                        if generation != self._generation:
                            logger.warning(
                                "BUILD 2 → Discarding stale MODIFY_PLAN generation %s before state commit",
                                generation,
                            )
                            return STALE_RESPONSE

                        self.plan = candidate_plan

                        self._protect_state_after_plan_change(
                            old_current_step_id,
                            old_completed_steps
                        )
                else:
                    self.plan = candidate_plan

                    self._protect_state_after_plan_change(
                        old_current_step_id,
                        old_completed_steps
                    )

                # ---------------------------------------------
                # CRITICAL:
                #
                # Restore/protect cooking state.
                # The live plan/state were already committed atomically above.
                # ---------------------------------------------

                logger.info(
                    "State after modification: current=%s completed=%s",
                    self.state.get(
                        "current_step_id"
                    ),
                    self.state.get(
                        "completed_steps"
                    )
                )

                if generation is not None and not self.is_generation_current(generation):
                    logger.warning(
                        "BUILD 2 → Plan modification became stale for generation %s",
                        generation,
                    )
                    return STALE_RESPONSE

                return self._voice_plan_modified(
                    decision
                )

            # =================================================
            # 12. UNKNOWN ACTION
            # =================================================

            logger.warning(
                "Unknown action: %s",
                action
            )

            return (
                "I'm not sure how to handle that."
            )

        except Exception as e:

            logger.exception(
                "Voice bridge error"
            )

            return (
                "I had trouble processing that."
            )
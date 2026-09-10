import asyncio
import logging
import os

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    AgentServer,
    JobContext,
    UserStateChangedEvent,
    AgentStateChangedEvent,
    cli,
)

from livekit.plugins import deepgram, silero
from livekit.plugins import openai

from voice.rime_tts import RimeTTS
from voice.kitchen_bridge import KitchenAgentBridge
from tools import timer_manager


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kitchen_agent.voice")


# ============================================================
# KITCHEN VOICE AGENT
# ============================================================

class KitchenVoiceAgent(Agent):

    def __init__(self, bridge):

        self.bridge = bridge

        super().__init__(
            instructions="""
You are the voice interface for a cooking assistance AI.

The Kitchen Agent backend is the source of truth.

Do not invent recipes, ingredients, cooking steps, timers, or cooking state.

Speak like a real cooking assistant.

Keep responses very short:
normally one or two sentences,
and preferably under 20 spoken words.

Give only the information the user needs right now.

Never repeat the entire recipe.

Never repeat a previous cooking step unless the user asks.

Guide the user one step at a time.

If the user asks a general cooking question, answer briefly.

If the backend provides a cooking step, speak that step naturally.

Do not use Markdown, bullets, emojis, or long explanations.

Never claim a step was completed unless the backend actually completed it.
"""
        )

    # ========================================================
    # LLM NODE
    # ========================================================

    async def llm_node(
        self,
        chat_ctx,
        tools,
        model_settings,
    ):

        messages = chat_ctx.messages()

        user_message = None

        # Find the most recent user message.
        for message in reversed(messages):

            if message.role == "user":

                user_message = message.text_content

                break

        if not user_message:

            return "Sorry, I didn't catch that."

        logger.info(
            "USER → %s",
            user_message
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # The Kitchen Agent remains the source of truth.
        # Voice layer only passes the user request to it.
        # ----------------------------------------------------

        # BUILD 2: every completed user turn gets a logical generation.
        # A newer turn invalidates older work before it can be committed/spoken.
        generation = self.bridge.start_generation()
        logger.info(
            "BUILD 2 → Processing generation %s",
            generation
        )

        response = await asyncio.to_thread(
            self.bridge.process,
            user_message,
            generation
        )

        if response == "__KITCHEN_AGENT_STALE__":
            logger.warning(
                "BUILD 2 → Stale generation %s discarded; nothing will be spoken.",
                generation
            )
            return ""

        # A user may have interrupted while the worker was finishing.
        # Re-check before allowing the response into the voice pipeline.
        if not self.bridge.is_generation_current(generation):
            logger.warning(
                "BUILD 2 → Generation %s became stale before speech; discarding.",
                generation
            )
            return ""

        logger.info(
            "KITCHEN AGENT → %s",
            response
        )

        return response


# ============================================================
# LIVEKIT SERVER
# ============================================================

server = AgentServer()


# ============================================================
# LIVEKIT SESSION
# ============================================================

@server.rtc_session()
async def entrypoint(ctx: JobContext):

    logger.info(
        "Starting Kitchen Agent voice interface..."
    )

    # --------------------------------------------------------
    # Kitchen Agent backend
    # --------------------------------------------------------

    bridge = KitchenAgentBridge()

    # --------------------------------------------------------
    # Voice session
    # --------------------------------------------------------

    session = AgentSession(

        # Voice activity detection
        vad=silero.VAD.load(),

        # Speech-to-text
        stt=deepgram.STT(),

        # LLM used by LiveKit pipeline.
        # Actual cooking decisions are still routed through
        # KitchenAgentBridge.llm_node().
        llm=openai.responses.LLM(
            model="gpt-4o-mini"
        ),

        # Rime is the primary spoken output.
        tts=RimeTTS(
            api_key=os.getenv("rime_test_api")
        ),

        # Do not generate speculative responses before the
        # user's turn is complete.
        turn_handling={
            "endpointing": {
                "mode": "fixed",
                "min_delay": 0.8,
                "max_delay": 2.5,
            },
            "preemptive_generation": {
                "enabled": False,
            },
        },

        # ----------------------------------------------------
        # INTERRUPTION CONFIGURATION
        # ----------------------------------------------------

        allow_interruptions=True,

        # User must speak for at least this duration before
        # LiveKit treats it as an interruption.
        min_interruption_duration=0.1,

        # Do not automatically resume the old response after
        # a false interruption.
        resume_false_interruption=False,
    )

    # ========================================================
    # INTERRUPTION OBSERVABILITY
    # ========================================================
    #
    # These handlers do not change Kitchen Agent behavior.
    #
    # They allow us to observe what happens during an
    # interruption so that we can test and prove the hard
    # voice-engineering claim.
    # ========================================================

    @session.on("user_state_changed")
    def on_user_state_changed(
        event: UserStateChangedEvent
    ):

        logger.info(
            "USER STATE → %s → %s",
            event.old_state,
            event.new_state,
        )

        if event.new_state == "speaking":

            logger.warning(
                "🎤 USER STARTED SPEAKING"
            )

            # BUILD 2: immediately fence off any older in-flight work.
            bridge.invalidate_generation("user started speaking")

        elif event.new_state == "listening":

            logger.info(
                "🎤 USER STOPPED SPEAKING"
            )

    @session.on("agent_state_changed")
    def on_agent_state_changed(
        event: AgentStateChangedEvent
    ):

        logger.info(
            "AGENT STATE → %s → %s",
            event.old_state,
            event.new_state,
        )

        if event.new_state == "speaking":

            logger.info(
                "🔊 AGENT STARTED SPEAKING"
            )

        elif event.new_state == "listening":

            logger.info(
                "👂 AGENT LISTENING"
            )

        elif event.new_state == "thinking":

            logger.info(
                "🧠 AGENT THINKING"
            )

    @session.on("user_interruption_detected")
    def on_user_interruption(event):

        logger.warning(
            "🔥 USER INTERRUPTION DETECTED"
        )

        logger.warning(
            "Interruption probability: %.3f",
            event.probability
        )

        logger.warning(
            "Interruption timestamp: %.3f",
            event.timestamp
        )

    # --------------------------------------------------------
    # False interruption
    # --------------------------------------------------------
    #
    # Useful for debugging cases where LiveKit temporarily
    # thinks the user interrupted but later determines it
    # was not a real interruption.
    # --------------------------------------------------------

    @session.on("agent_false_interruption")
    def on_agent_false_interruption(event):

        logger.warning(
            "⚠️ FALSE INTERRUPTION DETECTED"
        )

    logger.info(
        "Voice components initialized."
    )

    # ========================================================
    # START SESSION
    # ========================================================

    await session.start(
        room=ctx.room,
        agent=KitchenVoiceAgent(bridge),
    )

    logger.info(
        "Voice session started."
    )

    # ========================================================
    # TIMER → VOICE CALLBACK
    # ========================================================

    loop = asyncio.get_running_loop()

    def timer_finished_callback(timer_data):

        try:

            purpose = timer_data.get(
                "purpose",
                "cooking"
            )

            seconds = timer_data.get(
                "duration",
                0
            )

            message = (
                f"Your {seconds}-second timer "
                f"for {purpose} is finished."
            )

            logger.info(
                "TIMER FINISHED → %s",
                message
            )

            async def announce_timer():

                try:

                    await session.say(
                        message,
                        allow_interruptions=False,
                    )

                except Exception as e:

                    logger.exception(
                        "Timer voice announcement failed: %s",
                        e
                    )

            # Timer runs in a background thread.
            #
            # Safely send the announcement back to
            # the LiveKit event loop.

            asyncio.run_coroutine_threadsafe(
                announce_timer(),
                loop,
            )

        except Exception as e:

            logger.exception(
                "Timer callback error: %s",
                e
            )

    timer_manager.on_timer_finished = (
        timer_finished_callback
    )

    logger.info(
        "Timer voice callback connected."
    )

    # ========================================================
    # GREETING
    # ========================================================

    await session.say(
        "Hey! What would you like to cook today?",
        allow_interruptions=True,
    )

    logger.info(
        "Greeting spoken. Waiting for user input."
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    cli.run_app(server)
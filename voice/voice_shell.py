import asyncio
import logging
import os

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    AgentServer,
    JobContext,
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

    async def llm_node(self, chat_ctx, tools, model_settings):

        messages = chat_ctx.messages()

        user_message = None

        for message in reversed(messages):
            if message.role == "user":
                user_message = message.text_content
                break

        if not user_message:
            return "Sorry, I didn't catch that."

        logger.info("USER → %s", user_message)

        response = await asyncio.to_thread(
            self.bridge.process,
            user_message
        )

        logger.info("KITCHEN AGENT → %s", response)

        return response


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):

    logger.info("Starting Kitchen Agent voice interface...")

    bridge = KitchenAgentBridge()

    session = AgentSession(
        vad=silero.VAD.load(),

        stt=deepgram.STT(),

        llm=openai.responses.LLM(
            model="gpt-4o-mini"
        ),

        tts=RimeTTS(
            api_key=os.getenv("rime_test_api")
        ),

        turn_handling={
            "preemptive_generation": {
                "enabled": False,
            },
        },

        allow_interruptions=True,
        min_interruption_duration=0.1,
        resume_false_interruption=False,
    )

    logger.info("Voice components initialized.")

    await session.start(
        room=ctx.room,
        agent=KitchenVoiceAgent(bridge),
    )

    logger.info("Voice session started.")

    # ==========================================================
    # TIMER → VOICE CALLBACK
    # ==========================================================

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
            # Safely send the announcement back
            # to the LiveKit event loop.
            asyncio.run_coroutine_threadsafe(
                announce_timer(),
                loop,
            )

        except Exception as e:
            logger.exception(
                "Timer callback error: %s",
                e
            )

    timer_manager.on_timer_finished = timer_finished_callback

    logger.info(
        "Timer voice callback connected."
    )

    # ==========================================================
    # GREETING
    # ==========================================================

    await session.say(
        "Hey! What would you like to cook today?",
        allow_interruptions=True,
    )

    logger.info(
        "Greeting spoken. Waiting for user input."
    )


if __name__ == "__main__":
    cli.run_app(server)
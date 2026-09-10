"""
Rime TTS provider for Kitchen Agent voice layer.

This module is isolated from the existing Kitchen Agent.
It converts text responses into audio using Rime mistv3.
"""

from __future__ import annotations

import asyncio

import aiohttp
from livekit.agents import (
    APIConnectOptions,
    APIStatusError,
    APITimeoutError,
    DEFAULT_API_CONNECT_OPTIONS,
    tts,
    utils,
)


RIME_TTS_URL = "https://users.rime.ai/v1/rime-tts"
RIME_MODEL_ID = "mistv3"
RIME_SAMPLE_RATE = 24_000
RIME_NUM_CHANNELS = 1


class RimeTTS(tts.TTS):
    """Rime TTS implementation for LiveKit Agents."""

    def __init__(
        self,
        *,
        api_key: str,
        speaker: str = "cove",
        base_url: str = RIME_TTS_URL,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=RIME_SAMPLE_RATE,
            num_channels=RIME_NUM_CHANNELS,
        )

        if not api_key:
            raise ValueError("A Rime API key is required")

        self._api_key = api_key
        self._speaker = speaker
        self._base_url = (base_url or RIME_TTS_URL).rstrip("/")

        self._active_streams: set[RimeTTSChunkedStream] = set()

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> tts.ChunkedStream:

        stream = RimeTTSChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
        )

        self._active_streams.add(stream)

        stream._synthesize_task.add_done_callback(
            lambda _: self._active_streams.discard(stream)
        )

        return stream

    async def abort_all(self) -> None:
        """Cancel all active Rime synthesis requests."""

        streams = list(self._active_streams)

        if streams:
            await asyncio.gather(
                *(stream.aclose() for stream in streams),
                return_exceptions=True,
            )


class RimeTTSChunkedStream(tts.ChunkedStream):
    """Receives Rime WAV data and feeds it into LiveKit."""

    def __init__(
        self,
        *,
        tts: RimeTTS,
        input_text: str,
        conn_options: APIConnectOptions,
    ) -> None:

        super().__init__(
            tts=tts,
            input_text=input_text,
            conn_options=conn_options,
        )

        self._tts: RimeTTS = tts

    async def _run(
        self,
        output_emitter: tts.AudioEmitter,
    ) -> None:

        headers = {
            "Accept": "audio/wav",
            "Authorization": f"Bearer {self._tts._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "text": self.input_text,
            "modelId": RIME_MODEL_ID,
            "speaker": self._tts._speaker,
            "lang": "en",
            "samplingRate": RIME_SAMPLE_RATE,
        }

        timeout = aiohttp.ClientTimeout(
            total=self._conn_options.timeout
        )

        try:
            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:

                async with session.post(
                    self._tts._base_url,
                    json=payload,
                    headers=headers,
                ) as response:

                    if response.status >= 400:
                        body = await response.text()

                        raise APIStatusError(
                            f"Rime TTS returned HTTP {response.status}",
                            status_code=response.status,
                            request_id=response.headers.get(
                                "x-request-id"
                            ),
                            body=body,
                            retryable=response.status >= 500,
                        )

                    request_id = (
                        response.headers.get("x-request-id")
                        or utils.shortuuid()
                    )

                    output_emitter.initialize(
                        request_id=request_id,
                        sample_rate=RIME_SAMPLE_RATE,
                        num_channels=RIME_NUM_CHANNELS,
                        mime_type="audio/wav",
                        stream=True,
                    )

                    output_emitter.start_segment(
                        segment_id=request_id
                    )

                    async for chunk in response.content.iter_chunked(
                        4096
                    ):
                        if chunk:
                            output_emitter.push(chunk)

                    output_emitter.end_segment()

        except asyncio.CancelledError:
            raise

        except aiohttp.ServerTimeoutError as exc:
            raise APITimeoutError(
                "Rime TTS request timed out"
            ) from exc

        except aiohttp.ClientError as exc:
            raise APIStatusError(
                f"Rime TTS request failed: {exc}",
                retryable=True,
            ) from exc
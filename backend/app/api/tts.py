"""
Text to speech for Chirpy's replies.

The whole reason this endpoint exists is that the ElevenLabs key must not
be in the browser. The marketing site and the classroom both POST here and
get audio back; the key stays in the environment on this side.

Unauthenticated, because the public demo on chatbot.html has no session,
which makes rate limiting the only thing standing between us and someone
spending the ElevenLabs balance. Hence: a short character cap, a per-IP
limit, and a refusal to synthesise anything that is not plain prose.

If ELEVENLABS_API_KEY is unset the endpoint reports 503 and the frontend
falls back to the browser's own speechSynthesis, which costs nothing and
sends nothing anywhere. That is the intended state until the key is
rotated and configured, so a 503 here is not an outage.

NOTE FOR WHOEVER SETS THE KEY: the key currently hardcoded in the Flutter
app (elevenlabs_service.dart) should be treated as compromised. Issue a
new one for this endpoint and revoke that one.
"""
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
import logging
import os
import re

import httpx

from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts", tags=["tts"])

# A reply to a small child is one or two sentences. This is several times
# the room a compliant answer needs and still caps what one request can
# cost us.
MAX_CHARS = 600

_ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

# Named voices, so the frontend never sends a raw provider id and cannot
# be used to drive somebody else's voice off our account.
_VOICES = {
    "chirpy": os.getenv("ELEVENLABS_VOICE_CHIRPY", ""),
    "mama": os.getenv("ELEVENLABS_VOICE_MAMA", ""),
}

# Anything that is not prose is either markup that leaked out of a bubble
# or an attempt to make us synthesise something odd. Strip, do not reject,
# so a stray entity does not break a child's lesson.
_STRIP = re.compile(r"<[^>]*>|&[a-zA-Z#0-9]+;")
_COLLAPSE = re.compile(r"\s+")


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice: str = Field(default="chirpy", max_length=20)


def _clean(text: str) -> str:
    return _COLLAPSE.sub(" ", _STRIP.sub(" ", text)).strip()[:MAX_CHARS]


@router.post("")
@limiter.limit("20/minute")
async def speak(request: Request, req: SpeakRequest) -> Response:
    """Synthesise one short line and return audio/mpeg."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        # Deliberate, and the frontend knows what to do with it.
        raise HTTPException(
            status_code=503,
            detail="Speech is not configured; the client should use the browser voice",
        )

    voice_id = _VOICES.get(req.voice, "").strip()
    if not voice_id:
        raise HTTPException(status_code=400, detail="Unknown voice")

    said = _clean(req.text)
    if not said:
        raise HTTPException(status_code=400, detail="Nothing to say")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(
                _ELEVEN_URL.format(voice_id=voice_id),
                headers={
                    "xi-api-key": api_key,
                    "accept": "audio/mpeg",
                    "content-type": "application/json",
                },
                json={
                    "text": said,
                    "model_id": os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2_5"),
                    "voice_settings": {
                        "stability": 0.45,
                        "similarity_boost": 0.75,
                        "style": 0.35,
                        "use_speaker_boost": True,
                    },
                },
            )
    except httpx.HTTPError:
        logger.exception("TTS: could not reach the speech provider")
        raise HTTPException(status_code=502, detail="Speech service unavailable")

    if res.status_code != 200:
        # Never pass the provider's body through: it can carry quota and
        # account detail that is none of the caller's business.
        logger.error("TTS: provider returned %s", res.status_code)
        raise HTTPException(status_code=502, detail="Speech service unavailable")

    return Response(
        content=res.content,
        media_type="audio/mpeg",
        headers={
            # The same line gets spoken again on a retry or a re-read, and
            # these are short and non-personal, so let the browser keep it.
            "Cache-Control": "public, max-age=86400",
        },
    )

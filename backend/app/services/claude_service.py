import os
import time
import logging
import anthropic
from dotenv import load_dotenv
from app.services.prompt_builder import build_system_prompt, build_lesson_plan_prompt
from app.services.circuit_breaker import anthropic_breaker
import json

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"          # lesson plans — quality-critical, not latency-sensitive
CHAT_MODEL = "claude-haiku-4-5"      # kid-facing chat — fast + cheap, plenty capable for spelling/phonics

# Cost per million tokens (USD), per model: (input, output)
_PRICING = {
    "claude-haiku-4-5":  (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
}

_FALLBACK_RESPONSE = (
    "Tweet tweet! 🐦 I need a tiny rest! "
    "Try again in a moment — I'll be right back!"
)

_TOOL_DEF = {
    "name": "record_progress",
    "description": (
        "Record the child's learning progress after each educational exchange. "
        "Call this after every response where the child attempted an answer."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "description": "Number of correct answers in this exchange (0 or 1 typically)",
            },
            "total": {
                "type": "integer",
                "description": "Total questions asked in this exchange (usually 1)",
            },
            "topic": {
                "type": "string",
                "description": "Specific topic practiced e.g. 'spelling - cat'",
            },
            "was_correct": {
                "type": "boolean",
                "description": "Whether the child got the answer correct",
            },
        },
        "required": ["score", "total", "topic", "was_correct"],
    },
}


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    cost_in, cost_out = _PRICING.get(model, (3.00, 15.00))
    return (input_tokens / 1_000_000 * cost_in) + (output_tokens / 1_000_000 * cost_out)


async def _call_claude(system_prompt: str, messages: list) -> anthropic.types.Message:
    """Raw Claude API call — wrapped in circuit breaker by callers."""
    client = _get_client()
    return client.messages.create(
        model=CHAT_MODEL,
        max_tokens=1000,
        system=system_prompt,
        messages=messages,
        tools=[_TOOL_DEF],
    )


async def _call_claude_followup(
    system_prompt: str, messages: list
) -> anthropic.types.Message:
    client = _get_client()
    return client.messages.create(
        model=CHAT_MODEL,
        max_tokens=1000,
        system=system_prompt,
        messages=messages,
        tools=[_TOOL_DEF],
    )


async def chat_with_character(
    config: dict,
    character: str,
    subject: str,
    child_age: int,
    conversation_history: list,
    new_message: str,
    child_name: str = "friend",
) -> dict:
    """
    Send a message to Claude and return {response, character, subject, progress, fallback}.
    Wrapped in circuit breaker; logs tokens + cost to caller for usage_logs write.
    """
    start_ms = int(time.monotonic() * 1000)
    system_prompt = build_system_prompt(
        config, character, subject, child_age, child_name
    )
    messages = conversation_history[-20:] + [
        {"role": "user", "content": new_message}
    ]

    response = await anthropic_breaker.call(
        _call_claude,
        system_prompt,
        messages,
        fallback=None,
    )

    if response is None:
        return {
            "response": _FALLBACK_RESPONSE,
            "character": character,
            "subject": subject,
            "progress": None,
            "fallback": True,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "duration_ms": int(time.monotonic() * 1000) - start_ms,
            "model": CHAT_MODEL,
        }

    response_text = ""
    progress_data = None

    for block in response.content:
        if block.type == "text":
            response_text += block.text
        elif block.type == "tool_use" and block.name == "record_progress":
            progress_data = block.input

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    # Only make a SECOND Claude call if progress was recorded but the first
    # response produced no spoken reply. When Claude both speaks and records
    # progress in one response (the common case), skip the follow-up — this
    # halves per-message latency vs. always doing two sequential generations.
    if progress_data and not response_text.strip():
        tool_use_id = next(
            b.id for b in response.content if b.type == "tool_use"
        )
        messages_with_tool = messages + [
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": "Progress recorded successfully",
                    }
                ],
            },
        ]

        final_response = await anthropic_breaker.call(
            _call_claude_followup,
            system_prompt,
            messages_with_tool,
            fallback=None,
        )

        if final_response:
            for block in final_response.content:
                if block.type == "text":
                    response_text = block.text
            input_tokens += final_response.usage.input_tokens
            output_tokens += final_response.usage.output_tokens

    cost_usd = _calculate_cost(CHAT_MODEL, input_tokens, output_tokens)
    duration_ms = int(time.monotonic() * 1000) - start_ms

    return {
        "response": response_text,
        "character": character,
        "subject": subject,
        "progress": progress_data,
        "fallback": False,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "duration_ms": duration_ms,
        "model": CHAT_MODEL,
    }


async def _call_lesson_plan(prompt: str) -> anthropic.types.Message:
    """Raw lesson plan API call — wrapped in circuit breaker by caller."""
    client = _get_client()
    return client.messages.create(
        model=MODEL,
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}],
    )


async def generate_lesson_plan(
    config: dict,
    subject: str,
    grade: str,
    duration: str,
    focus_areas: str = "",
) -> dict:
    """Generate a structured JSON lesson plan. Returns plan dict + token metadata."""
    prompt = build_lesson_plan_prompt(config, subject, grade, duration, focus_areas)

    response = await anthropic_breaker.call(
        _call_lesson_plan,
        prompt,
        fallback=None,
    )

    if response is None:
        return {
            "error": "Service temporarily unavailable. Please try again.",
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
        }

    raw = response.content[0].text.strip()
    # Extract JSON from markdown code fence if present
    if "```" in raw:
        parts = raw.split("```")
        # parts[1] is the fenced block, e.g. "json\n{...}"
        if len(parts) >= 2:
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
    # Fall back to extracting outermost { ... } if still not valid JSON
    if not raw.startswith("{"):
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            raw = raw[start:end + 1]

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost_usd = _calculate_cost(MODEL, input_tokens, output_tokens)

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        plan = {"raw_content": response.content[0].text}

    plan["_meta"] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
    }
    return plan

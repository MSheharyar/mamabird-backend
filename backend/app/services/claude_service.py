import os
import anthropic
from dotenv import load_dotenv
from app.services.prompt_builder import build_system_prompt, build_lesson_plan_prompt
import json

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-20250514"


def chat_with_character(
    config: dict,
    character: str,
    subject: str,
    child_age: int,
    conversation_history: list,
    new_message: str
) -> dict:
    """
    Main chat function — sends message to Claude and returns response + score.
    
    conversation_history format:
    [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    """

    # Build system prompt from config (white-label safe)
    system_prompt = build_system_prompt(config, character, subject, child_age)

    # Add the new message to history
    messages = conversation_history + [
        {"role": "user", "content": new_message}
    ]

    # Call Claude API with tool use for score extraction
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system_prompt,
        messages=messages,
        tools=[
            {
                "name": "record_progress",
                "description": "Record the child's learning progress after each educational exchange. Call this after every response where the child attempted an answer.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "score": {
                            "type": "integer",
                            "description": "Number of correct answers in this exchange (0 or 1 typically)"
                        },
                        "total": {
                            "type": "integer", 
                            "description": "Total questions asked in this exchange (usually 1)"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Specific topic practiced e.g. 'spelling - cat', 'addition - single digits'"
                        },
                        "was_correct": {
                            "type": "boolean",
                            "description": "Whether the child got the answer correct"
                        }
                    },
                    "required": ["score", "total", "topic", "was_correct"]
                }
            }
        ]
    )

    # Extract text response and tool use
    response_text = ""
    progress_data = None

    for block in response.content:
        if block.type == "text":
            response_text += block.text
        elif block.type == "tool_use" and block.name == "record_progress":
            progress_data = block.input

    # If Claude used the tool, we need to send tool result and get final response
    if progress_data:
        messages_with_tool = messages + [
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": next(
                            b.id for b in response.content if b.type == "tool_use"
                        ),
                        "content": "Progress recorded successfully"
                    }
                ]
            }
        ]

        # Get the final text response after tool use
        final_response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=system_prompt,
            messages=messages_with_tool,
            tools=[
                {
                    "name": "record_progress",
                    "description": "Record the child's learning progress",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "integer"},
                            "total": {"type": "integer"},
                            "topic": {"type": "string"},
                            "was_correct": {"type": "boolean"}
                        },
                        "required": ["score", "total", "topic", "was_correct"]
                    }
                }
            ]
        )

        for block in final_response.content:
            if block.type == "text":
                response_text = block.text

    return {
        "response": response_text,
        "character": character,
        "subject": subject,
        "progress": progress_data
    }


def generate_lesson_plan(
    config: dict,
    subject: str,
    grade: str,
    duration: str,
    focus_areas: str = ""
) -> dict:
    """Generate a structured lesson plan using Mama Bird."""

    prompt = build_lesson_plan_prompt(config, subject, grade, duration, focus_areas)

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response.content[0].text

    # Parse JSON response
    try:
        # Clean up any markdown formatting if present
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("```")[1]
            if clean_text.startswith("json"):
                clean_text = clean_text[4:]
        lesson_plan = json.loads(clean_text)
    except json.JSONDecodeError:
        # If JSON parsing fails, return as raw text
        lesson_plan = {"raw_content": response_text}

    return lesson_plan
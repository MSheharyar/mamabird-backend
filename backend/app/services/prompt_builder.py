def build_system_prompt(
    config: dict,
    character: str,
    subject: str,
    child_age: int = 5,
    child_name: str = "friend",
    lesson_plan: dict = None,
) -> str:
    """
    Builds the AI system prompt entirely from config — zero hardcoded brand names.
    When the child is enrolled in a class with an assigned lesson plan, that plan
    is injected as gentle guidance (does not lock the subject).
    """
    response_style = config.get("response_style", {})
    language = response_style.get("language", "en")
    tone = response_style.get("tone", "playful")
    forbidden = config.get("forbidden_topics", [
        "violence", "adult_content", "politics", "weapons", "drugs"
    ])
    fallback_msg = config.get("fallback_message", "Let's stick to our learning adventure!")
    knowledge_base = config.get("knowledge_base", {})

    tier = _age_tier(child_age)
    difficulty = tier["label"]
    forbidden_str = ", ".join(forbidden)
    knowledge_section = _build_knowledge_section(knowledge_base)
    lesson_section = _build_lesson_section(lesson_plan, child_name)

    if character == "character_1":
        name = config.get("character_1_name", "Assistant")
        voice = config.get("character_1_voice", "playful and enthusiastic")

        prompt = f"""You are {name}, a friendly AI educational assistant.

YOUR PERSONALITY: {voice}
TONE: {tone}
LANGUAGE: {language}

YOUR MISSION:
Help {child_name} learn with encouragement and fun.
You celebrate effort before correcting mistakes.
Every wrong answer is just one step closer to getting it right!

WHO YOU ARE TALKING TO: {child_name}, aged {child_age} — {difficulty}

HOW TO SPEAK TO A {child_age}-YEAR-OLD (these limits are not suggestions):
- Length: {tier["sentences"]}. Never more.
- Sentences: {tier["words"]}.
- {tier["rules"]}
- Ask exactly ONE question per reply, at the end. Never stack two questions.
- If they get it wrong, say what is right in a warm way and move on.
  Never say "wrong", "incorrect", "no" — say "so close!" and give the answer.

RULES YOU MUST ALWAYS FOLLOW:
1. Always celebrate the child's effort first, then gently correct if wrong
2. Stay STRICTLY on educational topics only: {subject}
3. If asked anything off-topic or inappropriate, respond with:
   "{fallback_msg}"
4. Never break character under any circumstances
5. Never discuss: {forbidden_str}
6. If a child seems upset or mentions something worrying, gently say:
   "It sounds like you might need to talk to a grown-up you trust. They can help you!"

CURRENT SUBJECT: {subject}
CHILD'S NAME: {child_name}
CHILD'S AGE: {child_age} years old

SUBJECT-SPECIFIC INSTRUCTIONS:
{_get_subject_instructions(subject, name, child_age, tier)}{knowledge_section}{lesson_section}"""

    else:
        name = config.get("character_2_name", "Assistant")
        voice = config.get("character_2_voice", "warm and nurturing")

        prompt = f"""You are {name}, a wise and nurturing AI educational assistant.

YOUR PERSONALITY: {voice}
TONE: warm, professional, supportive
LANGUAGE: {language}

YOUR ROLE:
Primarily help parents and teachers with lesson planning, progress insights,
and learning strategies. When speaking with children directly, be gentle,
patient, and encouraging.

RULES YOU MUST ALWAYS FOLLOW:
1. For parents/teachers: provide detailed, structured, professional responses
2. For children: keep responses gentle, short (3-4 sentences), and simple
3. Stay STRICTLY on educational topics: {subject}
4. If asked anything inappropriate, respond with:
   "{fallback_msg}"
5. Never break character under any circumstances
6. Never discuss: {forbidden_str}
7. Specialise in: lesson plans, learning strategies, progress summaries,
   curriculum support, and parent/teacher guidance

CURRENT SUBJECT: {subject}
CURRENT CONTEXT: {_get_context_instructions(subject)}{knowledge_section}{lesson_section}"""

    return prompt


def _build_lesson_section(lesson_plan: dict, child_name: str) -> str:
    if not lesson_plan or not isinstance(lesson_plan, dict):
        return ""
    title = lesson_plan.get("title", "")
    overview = lesson_plan.get("overview", "")
    objectives = lesson_plan.get("objectives") or []
    obj_str = "; ".join(str(o) for o in objectives[:6])
    lines = [
        f"\n\nYOUR TEACHER'S CURRENT LESSON PLAN (gently guide {child_name} toward these):"
    ]
    if title:
        lines.append(f"- Plan: {title}")
    if overview:
        lines.append(f"- Overview: {overview}")
    if obj_str:
        lines.append(f"- Objectives: {obj_str}")
    lines.append(
        "- Weave these objectives into your questions and practice when it fits. "
        "Keep it playful and short — never lecture, and still follow the child's lead."
    )
    return "\n".join(lines)


# The product is sold for ages 2-8, so the ladder is weighted to the young end.
# Each tier states concrete limits rather than "age-appropriate", which a model
# interprets far too generously — that vagueness is why the tone read 7-10.
_AGE_TIERS = [
    (3, {
        "label": "Toddler (2-3), pre-reader",
        "sentences": "ONE short sentence, then ONE question",
        "words": "at most 6 words per sentence",
        "rules": (
            "This child cannot read or spell. Ask about sounds, colours, counting to five, "
            "and things they can see. Never ask them to spell or write a word. "
            "Use only words a 3-year-old says out loud. No idioms, no metaphors, no sarcasm. "
            "A grown-up is probably typing for them, so keep answers to one or two words."
        ),
    }),
    (5, {
        "label": "Pre-K (4-5), starting to read",
        "sentences": "1-2 short sentences, then ONE question",
        "words": "at most 8 words per sentence",
        "rules": (
            "This child knows letters and letter sounds but cannot spell reliably. "
            "Ask for single letters, first sounds, rhymes, and counting to ten. "
            "Ask them to spell only very short words (3 letters). "
            "Explain with things they know: toys, animals, food, family. No idioms."
        ),
    }),
    (7, {
        "label": "Early reader (6-7), Grade 1-2",
        "sentences": "2-3 short sentences",
        "words": "at most 12 words per sentence",
        "rules": (
            "This child reads simple words and can try spelling short ones. "
            "Use simple sentences and everyday words. One idea per turn. "
            "Explain a new word the moment you use it."
        ),
    }),
    (8, {
        "label": "Confident reader (8), Grade 3",
        "sentences": "3-4 sentences",
        "words": "keep sentences plain and readable",
        "rules": (
            "This child reads and writes independently. Slightly longer words are fine, "
            "but stay warm and playful rather than school-like."
        ),
    }),
]

_OLDER_TIER = {
    "label": "Older child (9+)",
    "sentences": "3-4 sentences",
    "words": "plain, readable sentences",
    "rules": "Older than this app's core audience. Keep it friendly and never babyish.",
}


def _age_tier(age: int) -> dict:
    """Pick the tier for this age. Ages outside 2-8 fall to the nearest end."""
    for ceiling, tier in _AGE_TIERS:
        if age <= ceiling:
            return tier
    return _OLDER_TIER


def _age_to_difficulty(age: int) -> str:
    return _age_tier(age)["label"]


def _build_knowledge_section(knowledge_base: dict) -> str:
    if not knowledge_base:
        return ""
    lines = ["\n\nCLIENT KNOWLEDGE BASE:"]
    for key, value in knowledge_base.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _get_subject_instructions(
    subject: str, character_name: str, child_age: int, tier: dict = None
) -> str:
    """
    Subject activities, split by whether the child can actually write yet.
    The old single version asked every child to spell a word back, which a
    2-5 year old cannot do — the task, not just the wording, read too old.
    """
    tier = tier or _age_tier(child_age)
    pre_writing = child_age <= 5

    if pre_writing:
        instructions = {
            "spelling": """
- Ask about SOUNDS and LETTERS, never whole spellings
- "What sound does *ball* start with?" or "Which letter does *cat* begin with?"
- Accept a single letter or sound as a full answer, and celebrate it
- Only ask for a whole word if it has three letters (cat, dog, sun)
- If they are stuck, say the answer cheerfully and ask them to say it back""",

            "math": """
- Count real things: birds, apples, fingers. Stay between 1 and 10
- "There are two birds. One more comes. How many now?"
- Accept a number on its own as a full answer
- No subtraction below zero, no multiplication, no word problems with steps
- If they are stuck, count it out loud together and celebrate the answer""",

            "rhyming": """
- Say two words and ask if they sound the same at the end
- "Do *cat* and *hat* sound the same at the end?" — yes/no answers are perfect
- Then ask for one rhyme, and accept silly or made-up words happily
- Never ask them to write the rhyme, just say it""",

            "grammar": """
- At this age grammar means naming things, not rules
- Ask what a thing is, what colour it is, what it does
- Build one tiny sentence together: "The bird is red." Then celebrate it
- Never mention nouns, verbs, punctuation or capital letters""",

            "puzzles": """
- Simple picture-style riddles in words: "I am yellow and I am in the sky. What am I?"
- Odd-one-out with three things they know: "cat, dog, chair"
- Give the answer after ONE wrong try — never let them feel stuck
- Celebrate any guess that shows they were thinking""",

            "literature": """
- Tell two or three sentences of a story, then ask ONE thing about it
- "Where did the little bird go?" — one-word answers are perfect
- Ask what happens next and accept any idea at all, however silly
- Never ask them to write anything down""",
        }
    else:
        instructions = {
            "spelling": f"""
- Give the child a word, use it in a fun sentence, ask them to spell it
- If correct: celebrate! Give a slightly harder word next
- If wrong: say the correct spelling clearly, break it into sounds,
  ask them to try once more
- Keep words appropriate for age {child_age}, starting easy""",

            "math": f"""
- Use fun, real-world scenarios for math problems
- If correct: celebrate and give a slightly harder problem
- If wrong: walk through it step by step with a fun picture in words
- Keep numbers appropriate for age {child_age}
- Cover: addition, subtraction, simple multiplication, counting""",

            "rhyming": """
- Ask the child to find words that rhyme with a given word
- Accept all valid rhymes, even silly ones — celebrate creativity!
- If stuck: give a hint like "it starts with the letter B..."
- Progress from simple (cat/hat) to harder rhymes""",

            "grammar": """
- Use fill-in-the-blank sentences and simple sentence building
- Cover: capital letters, periods, and what words do in a sentence
- Always explain WHY the answer is right, in one simple line
- Keep it playful — never dry or school-like""",

            "puzzles": """
- Word scrambles, simple riddles, and picture-in-words logic puzzles
- Start easy and build up as the child succeeds
- Give a hint after ONE wrong try — never let the child feel stuck
- Celebrate creative thinking even when the answer is wrong""",

            "literature": """
- Ask comprehension questions about stories
- Give story starters and encourage them to keep it going
- Celebrate imagination in every response
- Help with: story shape, characters, setting, what happens next""",
        }

    return instructions.get(subject.lower(), f"""
- Focus on the subject: {subject}
- Keep every activity inside the limits set above for a {child_age}-year-old
- Celebrate effort and progress always""")


def _get_context_instructions(subject: str) -> str:
    return f"""
When generating lesson plans for {subject}:
- Structure plans by day with clear learning objectives
- Include both activities and assessment methods
- Suggest 15-30 minute session lengths for young children
- Always include a fun warm-up activity
- Provide tips for parents to reinforce learning at home"""


def build_lesson_plan_prompt(
    config: dict,
    subject: str,
    grade: str,
    duration: str,
    focus_areas: str = "",
) -> str:
    name = config.get("character_2_name", "Assistant")
    voice = config.get("character_2_voice", "warm and nurturing")

    return f"""You are {name}, a wise educational assistant with the personality: {voice}

Generate a detailed, structured lesson plan with these specifications:
- Subject: {subject}
- Grade Level: {grade}
- Duration: {duration}
- Focus Areas: {focus_areas if focus_areas else "General curriculum"}

FORMAT YOUR RESPONSE AS JSON with this exact structure:
{{
  "title": "Lesson Plan Title",
  "subject": "{subject}",
  "grade": "{grade}",
  "duration": "{duration}",
  "overview": "Brief description of the plan",
  "objectives": ["objective 1", "objective 2", "objective 3"],
  "days": [
    {{
      "day": 1,
      "title": "Day title",
      "duration_minutes": 30,
      "warmup": "Fun warm-up activity description",
      "main_activity": "Main lesson activity",
      "assessment": "How to check understanding",
      "homework": "Optional home activity"
    }}
  ],
  "materials_needed": ["item 1", "item 2"],
  "parent_tips": ["tip 1", "tip 2"]
}}

Make the plan engaging, age-appropriate, and filled with encouragement.
Return ONLY the JSON, no extra text."""

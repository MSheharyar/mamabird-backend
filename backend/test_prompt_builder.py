from app.services.prompt_builder import build_system_prompt, _age_to_difficulty

PIRATE_CONFIG = {
    "client_id": "test-uuid",
    "client_name": "Pirate Academy",
    "domain": "pirateacademy.com",
    "character_1_name": "Pirate Pete",
    "character_1_voice": "swashbuckling and adventurous",
    "character_2_name": "Captain Jane",
    "character_2_voice": "wise and nautical",
    "enabled_subjects": ["math", "spelling"],
    "response_style": {"max_length": "short", "formality": "casual", "tone": "pirate", "language": "en"},
    "knowledge_base": {},
    "forbidden_topics": ["violence", "adult_content"],
    "fallback_message": "Arrr, let's keep to our treasure hunt!",
    "schema_version": "1.0.0",
}

def test_no_chirpy_in_prompt():
    prompt = build_system_prompt(PIRATE_CONFIG, "character_1", "math", 7, "Jack")
    assert "Chirpy" not in prompt, "Chirpy leaked into non-Chirpy config!"
    assert "Pirate Pete" in prompt
    assert "Arrr, let's keep to our treasure hunt!" in prompt

def test_no_mama_bird_in_prompt():
    prompt = build_system_prompt(PIRATE_CONFIG, "character_2", "spelling", 8)
    assert "Mama Bird" not in prompt, "Mama Bird leaked into non-MamaBird config!"
    assert "Captain Jane" in prompt

def test_age_difficulty_bands():
    # Bands are weighted to the 2-8 audience the product is sold for.
    assert "Toddler" in _age_to_difficulty(2)
    assert "Toddler" in _age_to_difficulty(3)
    assert "Pre-K" in _age_to_difficulty(4)
    assert "Pre-K" in _age_to_difficulty(5)
    assert "Early reader" in _age_to_difficulty(6)
    assert "Early reader" in _age_to_difficulty(7)
    assert "Confident reader" in _age_to_difficulty(8)
    assert "Older child" in _age_to_difficulty(10)


def test_young_children_are_never_asked_to_spell():
    """A 2-5 year old cannot type a word back, so the spelling activity must
    ask for sounds and letters instead. This was the root of the 'too old' tone."""
    for age in (2, 3, 4, 5):
        prompt = build_system_prompt(PIRATE_CONFIG, "character_1", "spelling", age)
        assert "ask them to spell it" not in prompt, f"age {age} asked to spell a whole word"
        assert "SOUNDS and LETTERS" in prompt
    for age in (7, 8):
        prompt = build_system_prompt(PIRATE_CONFIG, "character_1", "spelling", age)
        assert "ask them to spell it" in prompt, f"age {age} should still spell"


def test_reply_length_shrinks_for_younger_children():
    toddler = build_system_prompt(PIRATE_CONFIG, "character_1", "math", 3)
    older   = build_system_prompt(PIRATE_CONFIG, "character_1", "math", 8)
    assert "ONE short sentence" in toddler
    assert "3-4 sentences" in older
    assert "3-4 sentences" not in toddler


def test_unknown_age_assumes_the_young_end():
    """Missing age used to default to 7. For a 2-8 product the safe assumption
    is younger: a too-simple tutor is recoverable, a too-hard one is not."""
    default_prompt = build_system_prompt(PIRATE_CONFIG, "character_1", "spelling")
    assert "Pre-K" in default_prompt

def test_knowledge_base_injected():
    config = {**PIRATE_CONFIG, "knowledge_base": {"school_name": "Jolly Roger Elementary"}}
    prompt = build_system_prompt(config, "character_1", "math", 7)
    assert "Jolly Roger Elementary" in prompt

def test_fallback_message_used():
    prompt = build_system_prompt(PIRATE_CONFIG, "character_1", "math", 7)
    assert "Arrr, let's keep to our treasure hunt!" in prompt

if __name__ == "__main__":
    test_no_chirpy_in_prompt()
    test_no_mama_bird_in_prompt()
    test_age_difficulty_bands()
    test_knowledge_base_injected()
    test_fallback_message_used()
    print("All prompt_builder tests PASSED (white-label safe)")

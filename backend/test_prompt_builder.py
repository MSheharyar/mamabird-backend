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
    assert "Pre-K" in _age_to_difficulty(4)
    assert "Pre-K" in _age_to_difficulty(5)
    assert "Grade 1-2" in _age_to_difficulty(6)
    assert "Grade 1-2" in _age_to_difficulty(7)
    assert "Grade 3-4" in _age_to_difficulty(8)
    assert "Grade 3-4" in _age_to_difficulty(9)
    assert "Grade 5+" in _age_to_difficulty(10)

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

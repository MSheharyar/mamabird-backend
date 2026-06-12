from fastapi import APIRouter
from app.config.client_config import get_client_config
from app.services.prompt_builder import build_system_prompt

router = APIRouter(prefix="/test", tags=["test"])

@router.get("/config")
def test_config():
    """Test that white-label config loads correctly from DB."""
    config = get_client_config("threebabybirdies.com")
    return {
        "config_loaded": True,
        "character_1": config["character_1_name"],
        "character_2": config["character_2_name"],
        "subjects": config["enabled_subjects"],
        "colors": config["theme_colors"]
    }

@router.get("/prompt/{character}/{subject}")
def test_prompt(character: str, subject: str):
    """Test that prompts build correctly from config — no hardcoding."""
    config = get_client_config("threebabybirdies.com")
    prompt = build_system_prompt(config, character, subject, child_age=7)
    return {
        "character_used": config[f"{character}_name"] if character in ["character_1", "character_2"] else "unknown",
        "subject": subject,
        "prompt_length": len(prompt),
        "prompt_preview": prompt[:300] + "..."
    }

@router.get("/whitelabel-check")
def whitelabel_check():
    """
    The most important test — proves zero Chirpy hardcoding.
    Loads a fake 'Pirate Pete' config and builds a prompt.
    If 'Chirpy' or 'Mama Bird' appear in the output, something is hardcoded.
    """
    fake_config = {
        "character_1_name": "Pirate Pete",
        "character_1_voice": "swashbuckling and adventurous, says Arrr!",
        "character_2_name": "Captain Wise",
        "character_2_voice": "commanding but kind, uses nautical metaphors",
        "enabled_subjects": ["math", "spelling"],
        "theme_colors": {"primary": "#8B4513", "secondary": "#FFD700"}
    }

    prompt = build_system_prompt(fake_config, "character_1", "math", child_age=8)

    chirpy_found = "Chirpy" in prompt
    mamabird_found = "Mama Bird" in prompt

    return {
        "test_passed": not chirpy_found and not mamabird_found,
        "chirpy_hardcoded": chirpy_found,
        "mamabird_hardcoded": mamabird_found,
        "character_used": "Pirate Pete",
        "prompt_preview": prompt[:300] + "...",
        "verdict": "✅ WHITE-LABEL SAFE" if not chirpy_found and not mamabird_found else "❌ HARDCODING DETECTED — FIX BEFORE CONTINUING"
    }
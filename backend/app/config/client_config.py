import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def get_client_config(domain: str = "threebabybirdies.com") -> dict:
    """
    Load all client-specific settings from DB.
    NOTHING Chirpy-specific is hardcoded here.
    This is what makes the whole system white-label.
    """
    result = supabase.table("clients").select(
        "*, client_configs(*)"
    ).eq("domain", domain).eq("active", True).execute()

    if not result.data:
        raise Exception(f"No active client found for domain: {domain}")

    client = result.data[0]
    configs = client.get("client_configs", [])

    if not configs:
        raise Exception(f"No config found for client: {domain}")

    config = configs[0]

    return {
        "client_id": client["id"],
        "client_name": client["name"],
        "domain": client["domain"],
        "character_1_name": config.get("character_1_name", "Character 1"),
        "character_1_voice": config.get("character_1_voice", "playful and enthusiastic"),
        "character_2_name": config.get("character_2_name", "Character 2"),
        "character_2_voice": config.get("character_2_voice", "warm and nurturing"),
        "enabled_subjects": config.get("enabled_subjects", [
            "spelling", "math", "rhyming", "grammar", "puzzles", "literature"
        ]),
        "theme_colors": config.get("theme_colors", {
            "primary": "#6EB4D4",
            "secondary": "#F5C200",
            "accent": "#4A8B3F"
        }),
        "subscription_tiers": config.get("subscription_tiers", {})
    }


def get_client_config_by_id(client_id: str) -> dict:
    """Load config by client_id instead of domain — used internally."""
    result = supabase.table("clients").select(
        "*, client_configs(*)"
    ).eq("id", client_id).execute()

    if not result.data:
        raise Exception(f"No client found for id: {client_id}")

    client = result.data[0]
    configs = client.get("client_configs", [])
    config = configs[0] if configs else {}

    return {
        "client_id": client["id"],
        "client_name": client["name"],
        "domain": client["domain"],
        "character_1_name": config.get("character_1_name", "Character 1"),
        "character_1_voice": config.get("character_1_voice", "playful and enthusiastic"),
        "character_2_name": config.get("character_2_name", "Character 2"),
        "character_2_voice": config.get("character_2_voice", "warm and nurturing"),
        "enabled_subjects": config.get("enabled_subjects", [
            "spelling", "math", "rhyming", "grammar", "puzzles", "literature"
        ]),
        "theme_colors": config.get("theme_colors", {}),
        "subscription_tiers": config.get("subscription_tiers", {})
    }
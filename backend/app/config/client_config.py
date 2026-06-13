import os
import time
import logging
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger(__name__)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# In-memory cache: {domain: {"config": dict, "expires_at": float}}
_cache: dict = {}
_CACHE_TTL = 300  # 5 minutes


def _build_config(client: dict, config: dict) -> dict:
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
            "accent": "#4A8B3F",
        }),
        "subscription_tiers": config.get("subscription_tiers", {}),
        "industry": config.get("industry", "education"),
        "target_audience": config.get("target_audience", "children_4_10"),
        "response_style": config.get("response_style", {
            "max_length": "short",
            "formality": "casual",
            "tone": "playful",
            "language": "en",
        }),
        "knowledge_base": config.get("knowledge_base", {}),
        "forbidden_topics": config.get("forbidden_topics", [
            "violence", "adult_content", "politics", "weapons", "drugs"
        ]),
        "welcome_message": config.get("welcome_message"),
        "fallback_message": config.get(
            "fallback_message", "Let's stick to our learning adventure!"
        ),
        "schema_version": config.get("schema_version", "1.0.0"),
    }


def validate_and_migrate_config(config: dict) -> dict:
    """Apply schema migrations as the config version evolves."""
    version = config.get("schema_version", "1.0.0")

    if version == "1.0.0":
        config.setdefault("response_style", {
            "max_length": "short",
            "formality": "casual",
            "tone": "playful",
            "language": "en",
        })
        config.setdefault("forbidden_topics", [
            "violence", "adult_content", "politics", "weapons", "drugs"
        ])
        config.setdefault("knowledge_base", {})
        config.setdefault("fallback_message", "Let's stick to our learning adventure!")

    return config


def get_client_config(domain: str = "threebabybirdies.com") -> dict:
    result = supabase.table("clients").select(
        "*, client_configs(*)"
    ).eq("domain", domain).eq("active", True).execute()

    if not result.data:
        raise Exception(f"No active client found for domain: {domain}")

    client_row = result.data[0]
    configs = client_row.get("client_configs", [])
    if not configs:
        raise Exception(f"No config found for client: {domain}")

    return _build_config(client_row, configs[0])


def get_client_config_cached(domain: str = "threebabybirdies.com") -> dict:
    """Return cached config, refreshing after TTL expiry."""
    entry = _cache.get(domain)
    if entry and entry["expires_at"] > time.monotonic():
        return entry["config"]

    config = get_client_config(domain)
    config = validate_and_migrate_config(config)
    _cache[domain] = {"config": config, "expires_at": time.monotonic() + _CACHE_TTL}
    logger.info("Config cache refreshed for domain: %s", domain)
    return config


def invalidate_cache(domain: str) -> None:
    _cache.pop(domain, None)


def get_client_config_by_id(client_id: str) -> dict:
    result = supabase.table("clients").select(
        "*, client_configs(*)"
    ).eq("id", client_id).execute()

    if not result.data:
        raise Exception(f"No client found for id: {client_id}")

    client_row = result.data[0]
    configs = client_row.get("client_configs", [])
    config = configs[0] if configs else {}

    return _build_config(client_row, config)

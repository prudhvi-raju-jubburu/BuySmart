import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# In-memory store for provider cooldown expirations
# Format: provider_name -> datetime when cooldown expires (or None)
_cooldown_expirations = {
    "gemini": None,
    "openai": None
}

def mark_provider_quota_failed(provider):
    """Mark a provider as on cooldown for 15 minutes due to quota/rate limiting"""
    if provider in _cooldown_expirations:
        cooldown_end = datetime.utcnow() + timedelta(minutes=15)
        _cooldown_expirations[provider] = cooldown_end
        logger.warning(f"AI Provider {provider} marked on cooldown for 15 minutes due to quota/rate limit failure.")

def is_provider_on_cooldown(provider):
    """Check if a provider is currently on cooldown"""
    if provider not in _cooldown_expirations:
        return False
    exp_time = _cooldown_expirations[provider]
    if not exp_time:
        return False
    if datetime.utcnow() > exp_time:
        # Cooldown period completed!
        _cooldown_expirations[provider] = None
        return False
    return True

def get_ai_status():
    """Get the current configuration and health status of all AI services"""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    gemini_configured = bool(gemini_key and gemini_key.strip())
    openai_configured = bool(openai_key and openai_key.strip())

    gemini_cooldown = is_provider_on_cooldown("gemini")
    openai_cooldown = is_provider_on_cooldown("openai")

    gemini_available = gemini_configured and not gemini_cooldown
    openai_available = openai_configured and not openai_cooldown

    # Fallback parser is active if Gemini and OpenAI are not available/configured
    fallback_active = (not gemini_available) and (not openai_available)

    return {
        "gemini_available": gemini_available,
        "openai_available": openai_available,
        "fallback_active": fallback_active
    }

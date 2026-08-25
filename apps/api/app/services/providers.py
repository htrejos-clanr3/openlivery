"""Supported AI providers (bring your own key, one per agency)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Agent, ProviderCredential
from ..security import decrypt_secret


PROVIDERS: dict[str, dict[str, str]] = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_style": "openai_responses",
    },
    "anthropic": {
        "label": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "api_style": "anthropic_messages",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "api_style": "openai_chat",
    },
    "moonshot": {
        "label": "Kimi (Moonshot)",
        "base_url": "https://api.moonshot.cn/v1",
        "api_style": "openai_chat",
    },
    "dashscope": {
        "label": "Qwen (DashScope)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_style": "openai_chat",
    },
}
SUPPORTED = tuple(PROVIDERS)
PROVIDER_PATTERN = r"^(" + "|".join(SUPPORTED) + r")$"


def base_url_for(provider: str) -> str:
    return PROVIDERS[provider]["base_url"]


def api_style_for(provider: str) -> str:
    return PROVIDERS[provider]["api_style"]


def resolve_provider_credentials(db: Session, agency_id, provider: str) -> tuple[str, str] | None:
    """(base_url, api_key) for an agency's provider key, or None if unknown or unset."""
    if provider not in PROVIDERS:
        return None
    credential = db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.agency_id == agency_id,
            ProviderCredential.provider == provider,
        )
    )
    if not credential:
        return None
    return base_url_for(provider), decrypt_secret(credential.encrypted_api_key)


def resolve_agent_credentials(db: Session, agent: Agent) -> tuple[str, str] | None:
    """(base_url, api_key) for the agent's provider using the agency's stored key."""
    return resolve_provider_credentials(db, agent.agency_id, agent.provider)

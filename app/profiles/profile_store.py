from copy import deepcopy
from typing import Any

from app.database.models import UserProfile
from app.database.repository import Repository
from app.profiles.user_profile import USER_PROFILE


DEFAULT_PROFILE_SLUG = "default"
DEFAULT_PREFERRED_SOURCE_TYPES = ["youtube", "openai", "anthropic"]
DEFAULT_NEWSLETTER_TOP_N = 10


def build_seed_user_profile() -> dict[str, Any]:
    seed = deepcopy(USER_PROFILE)
    return {
        "slug": seed.get("slug", DEFAULT_PROFILE_SLUG),
        "name": seed["name"],
        "title": seed["title"],
        "background": seed["background"],
        "expertise_level": seed["expertise_level"],
        "interests": list(seed.get("interests", [])),
        "preferred_source_types": list(
            seed.get("preferred_source_types", DEFAULT_PREFERRED_SOURCE_TYPES)
        ),
        "preferences": dict(seed.get("preferences", {})),
        "newsletter_top_n": int(seed.get("newsletter_top_n", DEFAULT_NEWSLETTER_TOP_N)),
    }


def user_profile_to_dict(profile: UserProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "slug": profile.slug,
        "name": profile.name,
        "title": profile.title,
        "background": profile.background,
        "expertise_level": profile.expertise_level,
        "interests": list(profile.interests or []),
        "preferred_source_types": list(profile.preferred_source_types or []),
        "preferences": dict(profile.preferences or {}),
        "newsletter_top_n": int(profile.newsletter_top_n),
    }


def get_runtime_user_profile(repo: Repository | None = None) -> dict[str, Any]:
    repo = repo or Repository()
    profile = repo.get_active_user_profile()
    if profile is None:
        existing_profiles = repo.list_user_profiles()
        if not existing_profiles:
            seed = build_seed_user_profile()
            repo.upsert_user_profile(**seed, is_active=True)
            profile = repo.get_active_user_profile()
        else:
            raise ValueError("No active user profile configured")

    if profile is None:
        raise ValueError("Unable to load or seed an active user profile")

    return user_profile_to_dict(profile)

from app.database.models import UserProfile
from app.database.repository import Repository
from app.profiles.profile_store import get_runtime_user_profile


def test_get_runtime_user_profile_bootstraps_default_profile(db_session):
    repo = Repository(session=db_session)

    profile = get_runtime_user_profile(repo=repo)

    rows = repo.list_user_profiles()

    assert len(rows) == 1
    assert rows[0].slug == "default"
    assert rows[0].is_active is True
    assert profile["slug"] == "default"
    assert profile["name"] == "Ali Jaffal"
    assert profile["preferred_source_types"] == ["youtube", "openai", "anthropic"]
    assert profile["newsletter_top_n"] == 10


def test_get_runtime_user_profile_does_not_duplicate_seeded_profile(db_session):
    repo = Repository(session=db_session)

    first = get_runtime_user_profile(repo=repo)
    second = get_runtime_user_profile(repo=repo)

    assert first["id"] == second["id"]
    assert db_session.query(UserProfile).count() == 1

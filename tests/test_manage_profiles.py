import json

from app.database.repository import Repository
from app.profiles import manage_profiles


def test_manage_profiles_upsert_writes_profile(db_session, monkeypatch, capsys):
    repo = Repository(session=db_session)
    monkeypatch.setattr(manage_profiles, "Repository", lambda: repo)

    exit_code = manage_profiles.main(
        [
            "upsert",
            "--slug",
            "ali",
            "--name",
            "Ali Jaffal",
            "--title",
            "AI Engineer",
            "--background",
            "Builds AI systems",
            "--expertise-level",
            "Intermediate",
            "--interest",
            "agents",
            "--interest",
            "rag",
            "--preferred-source-type",
            "openai",
            "--preferred-source-type",
            "youtube",
            "--preference",
            "prefer_practical=true",
            "--newsletter-top-n",
            "6",
            "--active",
        ]
    )

    out = capsys.readouterr().out
    profile = repo.get_active_user_profile()

    assert exit_code == 0
    assert "Upserted profile ali" in out
    assert profile is not None
    assert profile.slug == "ali"
    assert profile.preferences["prefer_practical"] is True
    assert profile.newsletter_top_n == 6


def test_manage_profiles_set_active_switches_profile(db_session, monkeypatch, capsys):
    repo = Repository(session=db_session)
    repo.upsert_user_profile(
        slug="ali",
        name="Ali",
        title="AI Engineer",
        background="Builds AI systems",
        expertise_level="Intermediate",
        interests=["agents"],
        preferred_source_types=["openai"],
        preferences={"prefer_practical": True},
        newsletter_top_n=5,
    )
    repo.upsert_user_profile(
        slug="team",
        name="Team",
        title="Research Team",
        background="Tracks AI news",
        expertise_level="Advanced",
        interests=["research"],
        preferred_source_types=["anthropic"],
        preferences={"prefer_research_breakthroughs": True},
        newsletter_top_n=8,
    )
    monkeypatch.setattr(manage_profiles, "Repository", lambda: repo)

    exit_code = manage_profiles.main(["set-active", "team"])

    out = capsys.readouterr().out
    active = repo.get_active_user_profile()

    assert exit_code == 0
    assert "Active profile set to team" in out
    assert active is not None
    assert active.slug == "team"


def test_manage_profiles_list_and_show_active_reflect_db_state(db_session, monkeypatch, capsys):
    repo = Repository(session=db_session)
    monkeypatch.setattr(manage_profiles, "Repository", lambda: repo)

    list_exit_code = manage_profiles.main(["list"])
    list_out = capsys.readouterr().out
    show_exit_code = manage_profiles.main(["show-active"])
    show_out = capsys.readouterr().out
    active = json.loads(show_out)

    assert list_exit_code == 0
    assert "No user profiles found." in list_out
    assert show_exit_code == 0
    assert active["slug"] == "default"
    assert active["name"] == "Ali Jaffal"

from app.agent import curator_agent


def test_curator_agent_prompt_includes_preferred_source_types(monkeypatch):
    monkeypatch.setattr(curator_agent.genai, "Client", lambda api_key: object())

    agent = curator_agent.CuratorAgent(
        {
            "name": "Ali",
            "title": "AI Engineer",
            "background": "Builds AI systems",
            "expertise_level": "Intermediate",
            "interests": ["agents", "rag"],
            "preferred_source_types": ["openai", "youtube"],
            "preferences": {"prefer_practical": True},
        }
    )

    assert "Preferred Source Types" in agent.system_prompt
    assert "- openai" in agent.system_prompt
    assert "- youtube" in agent.system_prompt

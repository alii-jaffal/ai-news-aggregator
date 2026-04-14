from app.content_normalization import (
    clean_markdown_text,
    clean_rss_summary,
    clean_transcript_text,
    select_normalized_content,
)


def test_clean_rss_summary_strips_html_and_collapses_whitespace():
    assert clean_rss_summary("<p>Hello <strong>AI</strong><br> world</p>") == "Hello AI world"


def test_clean_transcript_text_collapses_whitespace():
    assert (
        clean_transcript_text("Hello\n\n   world\tfrom transcript")
        == "Hello world from transcript"
    )


def test_clean_markdown_text_simplifies_markdown():
    markdown = "# Heading\n\n- First item\n- [Second](https://example.com)\n\n`inline` text"
    assert clean_markdown_text(markdown) == "Heading First item Second inline text"


def test_select_normalized_content_prefers_richer_sources():
    transcript_first = select_normalized_content(
        description="<p>summary</p>",
        transcript="full transcript",
        markdown="# markdown",
    )
    markdown_second = select_normalized_content(
        description="<p>summary</p>",
        markdown="# markdown body",
    )
    summary_last = select_normalized_content(description="<p>summary only</p>")
    missing = select_normalized_content()

    assert transcript_first.cleaned_content == "full transcript"
    assert transcript_first.content_source_type == "transcript"
    assert transcript_first.content_richness == "full"

    assert markdown_second.cleaned_content == "markdown body"
    assert markdown_second.content_source_type == "markdown"
    assert markdown_second.content_richness == "full"

    assert summary_last.cleaned_content == "summary only"
    assert summary_last.content_source_type == "rss"
    assert summary_last.content_richness == "summary"

    assert missing.cleaned_content is None
    assert missing.content_length is None
    assert missing.content_richness == "missing"

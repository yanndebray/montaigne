"""Tests for scripts.py - voiceover script generation and parsing."""

import pytest
from pathlib import Path

from montaigne.scripts import (
    _get_arc_position,
    _parse_field,
    _parse_numbered_list,
    _validate_overview_response,
)


class TestGetArcPosition:
    """Tests for narrative arc position determination."""

    def test_single_slide(self):
        """Single slide should return comprehensive overview."""
        result = _get_arc_position(1, 1)
        assert "Single slide" in result

    def test_opening_slides(self):
        """First ~15% should be opening."""
        # 1/10 = 10%, should be opening
        result = _get_arc_position(1, 10)
        assert "Opening" in result
        assert "inviting" in result.lower()

    def test_problem_slides(self):
        """15-25% should be problem/motivation section."""
        # 2/10 = 20%, should be problem section
        result = _get_arc_position(2, 10)
        assert "Problem" in result or "motivation" in result

    def test_body_slides(self):
        """25-75% should be body section."""
        # 5/10 = 50%, should be body
        result = _get_arc_position(5, 10)
        assert "Body" in result
        assert "technical" in result.lower() or "practical" in result.lower()

    def test_synthesis_slides(self):
        """75-90% should be synthesis section."""
        # 8/10 = 80%, should be synthesis
        result = _get_arc_position(8, 10)
        assert "Synthesis" in result

    def test_closing_slides(self):
        """Last 10% should be closing."""
        # 10/10 = 100%, should be closing
        result = _get_arc_position(10, 10)
        assert "Closing" in result
        assert "inspiring" in result.lower() or "action" in result.lower()

    def test_boundary_conditions(self):
        """Test boundary conditions for arc positions."""
        # Exactly at 15% boundary
        result = _get_arc_position(15, 100)
        assert "Opening" in result

        # Just after 15%
        result = _get_arc_position(16, 100)
        assert "Problem" in result or "motivation" in result

        # Exactly at 75%
        result = _get_arc_position(75, 100)
        assert "Body" in result

        # Just after 75%
        result = _get_arc_position(76, 100)
        assert "Synthesis" in result


class TestParseOverviewResponse:
    """Tests for parsing Gemini overview responses.

    Note: These test the parsing logic extracted from analyze_presentation_overview.
    The actual function makes API calls, so we test the parsing separately.
    """

    def test_parse_complete_response(self, sample_gemini_overview_response):
        """Parse a complete, well-formatted response."""
        text = sample_gemini_overview_response
        overview = _parse_overview_text(text, num_slides=5)

        assert overview["topic"] == "Introduction to Machine Learning"
        assert "developers" in overview["audience"].lower()
        assert "technical" in overview["tone"].lower()
        assert "8-10" in overview["total_duration"]
        assert len(overview["slide_summaries"]) >= 5
        assert "ML" in overview["terminology"]

    def test_parse_minimal_response(self, sample_gemini_overview_response_minimal):
        """Parse a response with minimal fields."""
        text = sample_gemini_overview_response_minimal
        overview = _parse_overview_text(text, num_slides=2)

        assert overview["topic"] == "Quick Overview"
        assert len(overview["slide_summaries"]) >= 2

    def test_parse_malformed_response(self, sample_gemini_overview_response_malformed):
        """Parse a malformed response - should use defaults."""
        text = sample_gemini_overview_response_malformed
        overview = _parse_overview_text(text, num_slides=3)

        # Should fall back to defaults
        assert overview["topic"] == "Presentation"
        assert overview["audience"] == "General audience"
        assert len(overview["slide_summaries"]) == 3

    def test_slide_summaries_padding(self):
        """Slide summaries should be padded if fewer than total slides."""
        text = """TOPIC: Test Topic

SLIDE_SUMMARIES:
1. First slide
2. Second slide
"""
        overview = _parse_overview_text(text, num_slides=5)
        assert len(overview["slide_summaries"]) == 5
        # Padded summaries should have generic names
        assert "Slide 3" in overview["slide_summaries"][2]


def _parse_overview_text(text: str, num_slides: int) -> dict:
    """
    Helper to parse overview text using the robust parsing functions.

    This uses the same logic as analyze_presentation_overview in scripts.py.
    """
    overview = {
        "topic": "Presentation",
        "audience": "General audience",
        "tone": "Professional and informative",
        "total_duration": f"{num_slides * 1}-{num_slides * 2} minutes",
        "slide_summaries": [f"Slide {i+1}" for i in range(num_slides)],
        "terminology": [],
        "narrative_notes": ""
    }

    # Extract each field using robust regex parsing
    if topic := _parse_field(text, "TOPIC"):
        overview["topic"] = topic

    if audience := _parse_field(text, "AUDIENCE"):
        overview["audience"] = audience

    if tone := _parse_field(text, "TONE"):
        overview["tone"] = tone

    if duration := _parse_field(text, "TOTAL_DURATION"):
        overview["total_duration"] = duration

    # Parse slide summaries (multiline section)
    if summaries_text := _parse_field(text, "SLIDE_SUMMARIES", multiline=True):
        summaries = _parse_numbered_list(summaries_text)
        if summaries:
            overview["slide_summaries"] = summaries

    # Parse terminology (comma-separated on single line)
    if term_line := _parse_field(text, "TERMINOLOGY"):
        overview["terminology"] = [t.strip() for t in term_line.split(",") if t.strip()]

    # Parse narrative notes (multiline)
    if notes := _parse_field(text, "NARRATIVE_NOTES", multiline=True):
        overview["narrative_notes"] = notes.split("\n\n")[0].strip()

    # Pad summaries if needed
    while len(overview["slide_summaries"]) < num_slides:
        overview["slide_summaries"].append(f"Slide {len(overview['slide_summaries']) + 1}")

    return overview


class TestParseField:
    """Tests for the _parse_field helper function."""

    def test_parse_simple_field(self):
        """Parse a simple single-line field."""
        text = "TOPIC: Machine Learning Basics"
        result = _parse_field(text, "TOPIC")
        assert result == "Machine Learning Basics"

    def test_parse_field_case_insensitive(self):
        """Field matching should be case-insensitive."""
        assert _parse_field("topic: lowercase", "TOPIC") == "lowercase"
        assert _parse_field("Topic: Title Case", "TOPIC") == "Title Case"
        assert _parse_field("TOPIC: UPPERCASE", "topic") == "UPPERCASE"

    def test_parse_field_with_whitespace_variations(self):
        """Handle various whitespace around colon."""
        assert _parse_field("TOPIC:No space", "TOPIC") == "No space"
        assert _parse_field("TOPIC:  Extra spaces", "TOPIC") == "Extra spaces"
        assert _parse_field("TOPIC :Space before", "TOPIC") == "Space before"
        assert _parse_field("TOPIC : Spaces both", "TOPIC") == "Spaces both"

    def test_parse_field_strips_markdown_bold(self):
        """Strip markdown bold formatting."""
        text = "TOPIC: **Bold Topic**"
        result = _parse_field(text, "TOPIC")
        assert result == "Bold Topic"

    def test_parse_field_strips_markdown_italic(self):
        """Strip markdown italic formatting."""
        text = "TOPIC: *Italic Topic*"
        result = _parse_field(text, "TOPIC")
        assert result == "Italic Topic"

    def test_parse_field_strips_markdown_code(self):
        """Strip markdown code formatting."""
        text = "TOPIC: `Code Topic`"
        result = _parse_field(text, "TOPIC")
        assert result == "Code Topic"

    def test_parse_field_multiline(self):
        """Parse multiline field value."""
        text = """NARRATIVE_NOTES: First line of notes.
Second line continues here.
Third line as well.

NEXT_FIELD: Something else"""
        result = _parse_field(text, "NARRATIVE_NOTES", multiline=True)
        assert "First line" in result
        assert "Second line" in result
        assert "Third line" in result
        assert "Something else" not in result

    def test_parse_field_not_found(self):
        """Return None when field not found."""
        text = "TOPIC: Something"
        result = _parse_field(text, "AUDIENCE")
        assert result is None

    def test_parse_field_avoids_partial_match(self):
        """Should not match partial field names."""
        text = "SUBTOPIC: This is a subtopic\nTOPIC: Main topic"
        result = _parse_field(text, "TOPIC")
        assert result == "Main topic"


class TestParseNumberedList:
    """Tests for the _parse_numbered_list helper function."""

    def test_parse_dot_format(self):
        """Parse '1. Item' format."""
        text = """1. First item
2. Second item
3. Third item"""
        result = _parse_numbered_list(text)
        assert result == ["First item", "Second item", "Third item"]

    def test_parse_parenthesis_format(self):
        """Parse '1) Item' format."""
        text = """1) First item
2) Second item"""
        result = _parse_numbered_list(text)
        assert result == ["First item", "Second item"]

    def test_parse_dash_format(self):
        """Parse '1 - Item' format."""
        text = """1 - First item
2 - Second item"""
        result = _parse_numbered_list(text)
        assert result == ["First item", "Second item"]

    def test_parse_with_leading_whitespace(self):
        """Handle leading whitespace on lines."""
        text = """  1. First item
    2. Second item"""
        result = _parse_numbered_list(text)
        assert result == ["First item", "Second item"]

    def test_parse_double_digit_numbers(self):
        """Handle double-digit slide numbers."""
        text = """10. Tenth item
11. Eleventh item
12. Twelfth item"""
        result = _parse_numbered_list(text)
        assert len(result) == 3
        assert result[0] == "Tenth item"

    def test_parse_empty_text(self):
        """Empty text returns empty list."""
        result = _parse_numbered_list("")
        assert result == []

    def test_parse_non_numbered_lines_ignored(self):
        """Non-numbered lines should be ignored."""
        text = """1. First item
Some random text
2. Second item
More random text"""
        result = _parse_numbered_list(text)
        assert result == ["First item", "Second item"]


class TestValidateOverviewResponse:
    """Tests for the _validate_overview_response function."""

    def test_complete_response_no_warnings(self):
        """Complete response should have no required field warnings."""
        text = """TOPIC: Test
AUDIENCE: Developers
TONE: Technical
SLIDE_SUMMARIES:
1. Slide one
TOTAL_DURATION: 10 minutes
TERMINOLOGY: ML, AI
NARRATIVE_NOTES: Some notes"""
        warnings = _validate_overview_response(text)
        required_missing = [w for w in warnings if "required" in w.lower()]
        assert len(required_missing) == 0

    def test_missing_required_field(self):
        """Missing required field should generate warning."""
        text = """AUDIENCE: Developers
TONE: Technical
SLIDE_SUMMARIES:
1. Slide one"""
        warnings = _validate_overview_response(text)
        assert any("TOPIC" in w for w in warnings)

    def test_missing_optional_field(self):
        """Missing optional field should generate warning."""
        text = """TOPIC: Test
AUDIENCE: Developers
TONE: Technical
SLIDE_SUMMARIES:
1. Slide one"""
        warnings = _validate_overview_response(text)
        # Should warn about missing optional fields
        assert any("TERMINOLOGY" in w or "optional" in w.lower() for w in warnings)

    def test_case_insensitive_validation(self):
        """Validation should be case-insensitive."""
        text = """topic: Test
audience: Developers
tone: Technical
slide_summaries:
1. Slide one"""
        warnings = _validate_overview_response(text)
        required_missing = [w for w in warnings if "required" in w.lower()]
        assert len(required_missing) == 0


class TestParseOverviewEdgeCases:
    """Edge case tests for overview parsing."""

    def test_topic_with_special_characters(self):
        """Topic with special characters should be handled."""
        text = "TOPIC: AI & Machine Learning: A Primer (2024)"
        overview = _parse_overview_text(text, num_slides=1)
        assert "AI & Machine Learning" in overview["topic"]

    def test_multiline_narrative_notes(self):
        """Narrative notes spanning multiple lines."""
        text = """TOPIC: Test
NARRATIVE_NOTES: This is the first line.
This is the second line.
This is the third line.

This paragraph should not be included."""
        overview = _parse_overview_text(text, num_slides=1)
        assert "first line" in overview["narrative_notes"]
        assert "third line" in overview["narrative_notes"]
        assert "should not be included" not in overview["narrative_notes"]

    def test_empty_terminology(self):
        """Empty terminology list should return empty list."""
        text = "TOPIC: Test\nTERMINOLOGY: "
        overview = _parse_overview_text(text, num_slides=1)
        assert overview["terminology"] == []

    def test_terminology_with_spaces(self):
        """Terminology items with surrounding spaces."""
        text = "TOPIC: Test\nTERMINOLOGY:  ML ,  AI ,  Deep Learning  "
        overview = _parse_overview_text(text, num_slides=1)
        assert "ML" in overview["terminology"]
        assert "AI" in overview["terminology"]
        assert "Deep Learning" in overview["terminology"]

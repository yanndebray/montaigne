"""Tests for scripts.py - voiceover script generation and parsing."""

import pytest
from pathlib import Path

from montaigne.scripts import (
    _get_arc_position,
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
    Helper to parse overview text - extracted from analyze_presentation_overview.

    This mirrors the parsing logic in scripts.py for testing purposes.
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

    # Extract each field
    if "TOPIC:" in text:
        overview["topic"] = text.split("TOPIC:")[1].split("\n")[0].strip()

    if "AUDIENCE:" in text:
        overview["audience"] = text.split("AUDIENCE:")[1].split("\n")[0].strip()

    if "TONE:" in text:
        overview["tone"] = text.split("TONE:")[1].split("\n")[0].strip()

    if "TOTAL_DURATION:" in text:
        overview["total_duration"] = text.split("TOTAL_DURATION:")[1].split("\n")[0].strip()

    if "SLIDE_SUMMARIES:" in text:
        summaries_section = text.split("SLIDE_SUMMARIES:")[1]
        end_markers = ["TERMINOLOGY:", "NARRATIVE_NOTES:"]
        for marker in end_markers:
            if marker in summaries_section:
                summaries_section = summaries_section.split(marker)[0]

        summaries = []
        for line in summaries_section.strip().split("\n"):
            line = line.strip()
            if line and line[0].isdigit():
                parts = line.split(".", 1)
                if len(parts) > 1:
                    summaries.append(parts[1].strip())
                else:
                    summaries.append(line)
        if summaries:
            overview["slide_summaries"] = summaries

    if "TERMINOLOGY:" in text:
        term_line = text.split("TERMINOLOGY:")[1].split("\n")[0].strip()
        if "NARRATIVE_NOTES:" in term_line:
            term_line = term_line.split("NARRATIVE_NOTES:")[0].strip()
        overview["terminology"] = [t.strip() for t in term_line.split(",") if t.strip()]

    if "NARRATIVE_NOTES:" in text:
        overview["narrative_notes"] = text.split("NARRATIVE_NOTES:")[1].strip().split("\n\n")[0]

    # Pad summaries if needed
    while len(overview["slide_summaries"]) < num_slides:
        overview["slide_summaries"].append(f"Slide {len(overview['slide_summaries']) + 1}")

    return overview


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

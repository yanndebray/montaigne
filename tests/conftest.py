"""Shared fixtures for montaigne tests."""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    dirpath = tempfile.mkdtemp()
    yield Path(dirpath)
    shutil.rmtree(dirpath)


@pytest.fixture
def sample_voiceover_script(temp_dir):
    """Create a sample voiceover script for testing."""
    script_content = """# Test Presentation - Voiceover Script

## MASTER PROMPT
**IMPORTANT: Each slide voiceover MUST NOT exceed 60 seconds.**

---

## SLIDE 1: Introduction
**Duration:** 30-45 seconds
**Tone:** Inviting

### Voice-Over:
Welcome to this presentation about artificial intelligence.
Today we'll explore the fundamentals of machine learning.

---

## SLIDE 2: Key Concepts
**Duration:** 45-60 seconds
**Tone:** Educational

### Voice-Over:
Machine learning is a subset of artificial intelligence.
It enables computers to learn from data without explicit programming.
Let's dive into the key concepts.

---

## SLIDE 3: Conclusion
**Duration:** 30-40 seconds
**Tone:** Inspiring

### Voice-Over:
In conclusion, AI is transforming every industry.
Thank you for joining us on this journey.
"""
    script_path = temp_dir / "voiceover.md"
    script_path.write_text(script_content, encoding="utf-8")
    return script_path


@pytest.fixture
def sample_voiceover_script_alt_format(temp_dir):
    """Create a voiceover script with alternative formatting."""
    script_content = """# Alternative Format Script

## SLIDE 1 - Welcome
**Duration:** 30 seconds

Welcome to our presentation.

---

## SLIDE 2 — Main Content
*Duration: 45-60 seconds*

This is the main content of our presentation.
We cover important topics here.

---

## SLIDE 3: Final Thoughts
Duration: 30s

Thank you for watching.
"""
    script_path = temp_dir / "voiceover_alt.md"
    script_path.write_text(script_content, encoding="utf-8")
    return script_path


@pytest.fixture
def sample_gemini_overview_response():
    """Sample Gemini API response for overview analysis."""
    return """TOPIC: Introduction to Machine Learning

AUDIENCE: Software developers and data scientists

TONE: Technical but accessible, practical and empowering

TOTAL_DURATION: 8-10 minutes

SLIDE_SUMMARIES:
1. Title slide introducing ML fundamentals
2. Definition of machine learning concepts
3. Types of machine learning algorithms
4. Real-world applications and examples
5. Best practices and next steps

TERMINOLOGY: ML, API, TensorFlow, PyTorch, neural networks, gradient descent

NARRATIVE_NOTES: The presentation flows from basic definitions through practical examples to actionable next steps. It maintains an educational tone throughout while building complexity gradually."""


@pytest.fixture
def sample_gemini_overview_response_minimal():
    """Minimal Gemini response with some fields missing."""
    return """TOPIC: Quick Overview

SLIDE_SUMMARIES:
1. Introduction
2. Content

Some extra text that should be ignored."""


@pytest.fixture
def sample_gemini_overview_response_malformed():
    """Malformed Gemini response for edge case testing."""
    return """This is a completely unstructured response
that doesn't follow the expected format at all.
It has no TOPIC or AUDIENCE markers."""


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for testing without API calls."""
    class MockResponse:
        def __init__(self, text):
            self._text = text

        @property
        def text(self):
            return self._text

    class MockModels:
        def __init__(self, response_text):
            self.response_text = response_text

        def generate_content(self, model, contents):
            return MockResponse(self.response_text)

    class MockClient:
        def __init__(self, response_text=""):
            self.models = MockModels(response_text)

    return MockClient

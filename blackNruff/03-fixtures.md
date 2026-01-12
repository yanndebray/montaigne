# Module 3: Fixtures & Test Organization

## What Are Fixtures?

Fixtures provide a fixed baseline for tests - they handle setup and teardown. Think of them as test dependencies that pytest automatically injects.

```python
import pytest

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"name": "test", "value": 42}

def test_with_fixture(sample_data):
    """Test automatically receives the fixture."""
    assert sample_data["name"] == "test"
    assert sample_data["value"] == 42
```

## The conftest.py File

Place shared fixtures in `conftest.py` - pytest automatically discovers them:

```
tests/
├── conftest.py          # Shared fixtures (auto-discovered)
├── test_audio.py
├── test_cli.py
└── test_config.py
```

### Real Example from montaigne

```python
# tests/conftest.py

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

## SLIDE 1: Introduction
**Duration:** 30-45 seconds
**Tone:** Inviting

### Voice-Over:
Welcome to this presentation about artificial intelligence.
Today we'll explore the fundamentals of machine learning.

---

## SLIDE 2: Key Concepts
**Duration:** 45-60 seconds

### Voice-Over:
Machine learning is a subset of artificial intelligence.
"""
    script_path = temp_dir / "voiceover.md"
    script_path.write_text(script_content, encoding="utf-8")
    return script_path
```

## Fixture Scopes

Control when fixtures are created and destroyed:

| Scope | Created | Destroyed |
|-------|---------|-----------|
| `function` (default) | Each test | After each test |
| `class` | Each test class | After class |
| `module` | Each test file | After file |
| `session` | Once per test run | After all tests |

```python
@pytest.fixture(scope="session")
def expensive_resource():
    """Created once, shared across all tests."""
    print("Setting up expensive resource...")
    resource = create_database_connection()
    yield resource
    print("Tearing down expensive resource...")
    resource.close()
```

## Fixture Dependencies

Fixtures can depend on other fixtures:

```python
@pytest.fixture
def temp_dir():
    """Base fixture: temporary directory."""
    dirpath = tempfile.mkdtemp()
    yield Path(dirpath)
    shutil.rmtree(dirpath)


@pytest.fixture
def sample_voiceover_script(temp_dir):  # Depends on temp_dir
    """Creates a script file in the temp directory."""
    script_path = temp_dir / "voiceover.md"
    script_path.write_text("# Script content", encoding="utf-8")
    return script_path


@pytest.fixture
def sample_voiceover_script_alt_format(temp_dir):  # Also depends on temp_dir
    """Alternative script format."""
    script_path = temp_dir / "voiceover_alt.md"
    script_path.write_text("# Alternative format", encoding="utf-8")
    return script_path
```

## Using Fixtures in Tests

### Simple Usage

```python
# From tests/test_audio.py

def test_parse_standard_format(self, sample_voiceover_script):
    """Parse a standard voiceover script."""
    slides = parse_voiceover_script(sample_voiceover_script)

    assert len(slides) == 3
    assert slides[0]["number"] == 1
    assert "Introduction" in slides[0]["title"]
```

### Multiple Fixtures

```python
def test_extract_nonexistent_pdf_raises_error(self, temp_dir):
    """Extracting from non-existent PDF should raise FileNotFoundError."""
    fake_pdf = temp_dir / "nonexistent.pdf"

    with pytest.raises(FileNotFoundError) as exc_info:
        extract_pdf_pages(fake_pdf)

    assert "PDF not found" in str(exc_info.value)
```

## Built-in Fixtures

pytest provides several useful built-in fixtures:

### `tmp_path` - Temporary Directory

```python
def test_with_tmp_path(tmp_path):
    """pytest's built-in temp directory fixture."""
    file = tmp_path / "test.txt"
    file.write_text("hello")
    assert file.read_text() == "hello"
```

### `capsys` - Capture stdout/stderr

```python
# From tests/test_cli.py

def test_no_command_prints_help(self, capsys):
    """No command should print help."""
    with patch.object(sys, 'argv', ['essai']):
        main()

    captured = capsys.readouterr()
    assert "Montaigne" in captured.out or "usage" in captured.out.lower()
```

### `monkeypatch` - Modify Objects

```python
def test_with_monkeypatch(monkeypatch):
    """Temporarily modify environment."""
    monkeypatch.setenv("API_KEY", "test-key")
    assert os.environ["API_KEY"] == "test-key"
    # Original value restored after test
```

## Fixture Factories

When you need multiple instances with different configurations:

```python
@pytest.fixture
def make_script(temp_dir):
    """Factory fixture for creating scripts."""
    created_files = []

    def _make_script(name, content):
        path = temp_dir / name
        path.write_text(content, encoding="utf-8")
        created_files.append(path)
        return path

    yield _make_script

    # Cleanup happens automatically via temp_dir fixture


def test_multiple_scripts(make_script):
    script1 = make_script("script1.md", "# First")
    script2 = make_script("script2.md", "# Second")

    assert script1.exists()
    assert script2.exists()
```

## Mock Fixtures

Create mock objects as fixtures:

```python
# From tests/conftest.py

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
```

## Test Data Fixtures

```python
@pytest.fixture
def sample_gemini_overview_response():
    """Sample Gemini API response for overview analysis."""
    return """TOPIC: Introduction to Machine Learning

AUDIENCE: Software developers and data scientists

TONE: Technical but accessible

TOTAL_DURATION: 8-10 minutes

SLIDE_SUMMARIES:
1. Title slide introducing ML fundamentals
2. Definition of machine learning concepts
3. Types of machine learning algorithms
4. Real-world applications and examples
5. Best practices and next steps

TERMINOLOGY: ML, API, TensorFlow, PyTorch, neural networks

NARRATIVE_NOTES: The presentation flows from basic definitions through practical examples."""


def test_parse_complete_response(self, sample_gemini_overview_response):
    """Parse a complete, well-formatted response."""
    text = sample_gemini_overview_response
    overview = _parse_overview_text(text, num_slides=5)

    assert overview["topic"] == "Introduction to Machine Learning"
    assert "developers" in overview["audience"].lower()
```

## Organizing Test Files

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_audio.py            # Tests for audio.py
│   ├── TestParseVoiceoverScript
│   ├── TestParseAudioMimeType
│   ├── TestDecodeAudioData
│   └── TestConvertToWav
├── test_cli.py              # Tests for cli.py
│   ├── TestMainArgParsing
│   ├── TestSetupCommand
│   ├── TestPdfCommand
│   └── ...
├── test_config.py           # Tests for config.py
├── test_pdf.py              # Tests for pdf.py
└── test_scripts.py          # Tests for scripts.py
```

## Best Practices

1. **Keep fixtures focused** - One fixture, one responsibility
2. **Use descriptive names** - `sample_voiceover_script` not `data1`
3. **Document fixtures** - Docstrings explain what they provide
4. **Minimize scope** - Use function scope unless sharing is needed
5. **Clean up resources** - Use `yield` for teardown

[← Previous: pytest Fundamentals](02-pytest-fundamentals.md) | [Next: Mocking →](04-mocking.md)

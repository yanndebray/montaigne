# Module 2: pytest Fundamentals

## Why pytest?

pytest is Python's most popular testing framework because it's:

- **Simple** - Plain `assert` statements, no boilerplate
- **Powerful** - Fixtures, parametrization, plugins
- **Flexible** - Works with unittest, doctest, and more

## Installation

```bash
pip install pytest pytest-cov
```

Or in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
]
```

## Writing Your First Test

```python
# tests/test_example.py

def test_addition():
    """Test that addition works."""
    assert 1 + 1 == 2

def test_string_contains():
    """Test string membership."""
    assert "hello" in "hello world"
```

Run with:
```bash
pytest tests/test_example.py -v
```

## Test Discovery

pytest automatically finds tests by:

1. Files named `test_*.py` or `*_test.py`
2. Functions named `test_*`
3. Classes named `Test*` with methods named `test_*`

```python
# All of these are discovered:

def test_function():  # ✓ Function starting with test_
    pass

class TestClass:  # ✓ Class starting with Test
    def test_method(self):  # ✓ Method starting with test_
        pass
```

## Organizing Tests with Classes

Group related tests in classes:

```python
# From tests/test_audio.py

class TestParseAudioMimeType:
    """Tests for audio MIME type parsing."""

    def test_parse_standard_mime(self):
        """Parse standard audio/L16 MIME type."""
        result = _parse_audio_mime_type("audio/L16;rate=24000")
        assert result["bits_per_sample"] == 16
        assert result["rate"] == 24000

    def test_parse_different_sample_rates(self):
        """Parse MIME types with different sample rates."""
        result = _parse_audio_mime_type("audio/L16;rate=44100")
        assert result["rate"] == 44100

    def test_parse_malformed_mime_defaults(self):
        """Malformed MIME type should return defaults."""
        result = _parse_audio_mime_type("audio/unknown")
        assert result["bits_per_sample"] == 16
        assert result["rate"] == 24000
```

## Assertions

pytest uses plain Python `assert` with helpful error messages:

```python
def test_assertions():
    # Simple equality
    assert 1 + 1 == 2

    # String comparison
    name = "montaigne"
    assert name == "montaigne"

    # Membership
    assert "pdf" in ["pdf", "png", "jpg"]

    # Boolean
    assert check_dependencies() is True

    # Approximate equality (for floats)
    import pytest
    assert 0.1 + 0.2 == pytest.approx(0.3)
```

### Assertion Introspection

When assertions fail, pytest shows detailed information:

```
def test_example():
>       assert result == expected
E       AssertionError: assert {'rate': 16000} == {'rate': 24000}
E         Differing items:
E         {'rate': 16000} != {'rate': 24000}
```

## Testing Exceptions

Use `pytest.raises` to verify exceptions:

```python
# From tests/test_pdf.py

def test_extract_nonexistent_pdf_raises_error(self, temp_dir):
    """Extracting from non-existent PDF should raise FileNotFoundError."""
    fake_pdf = temp_dir / "nonexistent.pdf"

    with pytest.raises(FileNotFoundError) as exc_info:
        extract_pdf_pages(fake_pdf)

    assert "PDF not found" in str(exc_info.value)
```

### Testing SystemExit

```python
# From tests/test_config.py

def test_load_api_key_missing_exits(self):
    """Missing API key should call sys.exit(1)."""
    original_key = os.environ.pop("GEMINI_API_KEY", None)
    try:
        with patch("dotenv.load_dotenv"):
            with pytest.raises(SystemExit) as exc_info:
                load_api_key()
            assert exc_info.value.code == 1
    finally:
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key
```

## Parametrized Tests

Run the same test with different inputs:

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("audio/L16;rate=24000", 24000),
    ("audio/L16;rate=44100", 44100),
    ("audio/L16;rate=16000", 16000),
])
def test_parse_sample_rates(input, expected):
    result = _parse_audio_mime_type(input)
    assert result["rate"] == expected
```

Output:
```
test_audio.py::test_parse_sample_rates[audio/L16;rate=24000-24000] PASSED
test_audio.py::test_parse_sample_rates[audio/L16;rate=44100-44100] PASSED
test_audio.py::test_parse_sample_rates[audio/L16;rate=16000-16000] PASSED
```

## Test Configuration

Configure pytest in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["montaigne"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
]
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific file
pytest tests/test_audio.py

# Run specific test class
pytest tests/test_audio.py::TestParseAudioMimeType

# Run specific test
pytest tests/test_audio.py::TestParseAudioMimeType::test_parse_standard_mime

# Run tests matching a pattern
pytest -k "mime"

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Show print statements
pytest -s

# Run with coverage
pytest --cov=montaigne --cov-report=term-missing
```

## Test Output

```
============================= test session starts =============================
platform win32 -- Python 3.10.10, pytest-9.0.2
configfile: pyproject.toml
plugins: cov-7.0.0

tests/test_audio.py::TestParseAudioMimeType::test_parse_standard_mime PASSED [  1%]
tests/test_audio.py::TestParseAudioMimeType::test_parse_different_sample_rates PASSED [  2%]
...
======================= 80 passed in 4.97s =======================
```

## Exercises

1. Write a test for a function that validates email addresses
2. Use `pytest.raises` to test invalid input handling
3. Create a parametrized test for multiple input scenarios
4. Run tests with coverage and identify untested code

[← Previous: Introduction](01-introduction.md) | [Next: Fixtures →](03-fixtures.md)

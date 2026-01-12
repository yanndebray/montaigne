# Module 8: Testing Best Practices

## Test Organization

### File Structure

Mirror your source structure in tests:

```
montaigne/              tests/
├── __init__.py         ├── __init__.py
├── cli.py       →      ├── test_cli.py
├── config.py    →      ├── test_config.py
├── pdf.py       →      ├── test_pdf.py
├── audio.py     →      ├── test_audio.py
└── scripts.py   →      └── test_scripts.py
```

### Group Related Tests

```python
class TestParseVoiceoverScript:
    """Tests for voiceover script parsing."""

    def test_parse_standard_format(self):
        ...

    def test_parse_alternative_format(self):
        ...

    def test_parse_empty_script(self):
        ...


class TestParseAudioMimeType:
    """Tests for audio MIME type parsing."""

    def test_parse_standard_mime(self):
        ...
```

## Naming Conventions

### Test Files
- `test_<module>.py` - Test files start with `test_`

### Test Classes
- `Test<Feature>` - Classes start with `Test`

### Test Methods
- `test_<scenario>` - Methods start with `test_`
- Be descriptive: `test_parse_standard_mime` not `test_1`

### Good Examples

```python
def test_extract_nonexistent_pdf_raises_error(self):
    """Extracting from non-existent PDF should raise FileNotFoundError."""

def test_wav_header_structure(self):
    """Generated WAV should have correct header structure."""

def test_api_key_with_whitespace_preserved(self):
    """API key with accidental whitespace should be preserved."""
```

## Writing Good Assertions

### Be Specific

```python
# Bad: Vague assertion
assert result is not None

# Good: Specific assertion
assert result["page_count"] == 10
assert result["title"] == "Test Presentation"
```

### Test One Thing Per Test

```python
# Bad: Testing multiple things
def test_everything():
    result = process_data(input)
    assert result["status"] == "success"
    assert result["count"] == 5
    assert len(result["items"]) == 5
    assert result["items"][0]["name"] == "first"

# Good: Focused tests
def test_process_data_returns_success_status():
    result = process_data(input)
    assert result["status"] == "success"

def test_process_data_returns_correct_count():
    result = process_data(input)
    assert result["count"] == 5
```

### Use Descriptive Messages

```python
# Better error messages
assert len(slides) == 3, f"Expected 3 slides, got {len(slides)}"
assert "Duration:" not in slide["text"], "Metadata leaked into voiceover text"
```

## Fixture Best Practices

### Keep Fixtures Focused

```python
# Bad: God fixture
@pytest.fixture
def setup_everything():
    db = create_database()
    user = create_user()
    api_client = create_client()
    return db, user, api_client

# Good: Focused fixtures
@pytest.fixture
def database():
    return create_database()

@pytest.fixture
def user(database):
    return create_user(database)

@pytest.fixture
def api_client(user):
    return create_client(user)
```

### Document Fixtures

```python
@pytest.fixture
def sample_voiceover_script(temp_dir):
    """
    Create a sample voiceover script for testing.

    Returns:
        Path to the created script file.

    The script contains 3 slides with standard formatting:
    - Slide 1: Introduction (30-45s)
    - Slide 2: Key Concepts (45-60s)
    - Slide 3: Conclusion (30-40s)
    """
    ...
```

### Use Appropriate Scope

```python
# Function scope (default) - fresh for each test
@pytest.fixture
def temp_file():
    ...

# Session scope - shared across all tests (use for expensive setup)
@pytest.fixture(scope="session")
def database_connection():
    ...
```

## Mocking Best Practices

### Mock at the Right Level

```python
# Mock external services, not internal code
with patch('mymodule.external_api.call'):  # Good
    ...

# Don't mock your own code
with patch('mymodule.helper_function'):  # Usually bad
    ...
```

### Verify Mock Interactions

```python
def test_document_closed_after_extraction(self, temp_dir):
    """PDF document should be closed after extraction."""
    ...
    mock_doc.close.assert_called_once()  # Verify cleanup
```

### Keep Mocks Simple

```python
# Only mock what you need
mock_client = MagicMock()
mock_client.get_data.return_value = {"key": "value"}

# Don't over-specify
# Bad: mock_client.method1.return_value.method2.return_value...
```

## Test Data Management

### Use Fixtures for Test Data

```python
@pytest.fixture
def sample_gemini_overview_response():
    """Sample API response for testing."""
    return """TOPIC: Introduction to Machine Learning
AUDIENCE: Software developers
TONE: Technical but accessible
..."""
```

### Keep Test Data Minimal

```python
# Bad: Huge test data
SAMPLE_RESPONSE = """... 500 lines of JSON ..."""

# Good: Minimal data that covers the test case
SAMPLE_RESPONSE = """TOPIC: Test
SLIDE_SUMMARIES:
1. First slide
2. Second slide"""
```

## Error Handling Tests

### Test Expected Errors

```python
def test_extract_nonexistent_pdf_raises_error(self, temp_dir):
    fake_pdf = temp_dir / "nonexistent.pdf"

    with pytest.raises(FileNotFoundError) as exc_info:
        extract_pdf_pages(fake_pdf)

    assert "PDF not found" in str(exc_info.value)
```

### Test Edge Cases

```python
def test_parse_empty_script(self, temp_dir):
    """Empty script should return empty list."""
    empty_script = temp_dir / "empty.md"
    empty_script.write_text("# Empty\n\nNo slides.", encoding="utf-8")

    slides = parse_voiceover_script(empty_script)
    assert slides == []

def test_parse_malformed_mime_defaults(self):
    """Malformed MIME type should return defaults."""
    result = _parse_audio_mime_type("audio/unknown")
    assert result["bits_per_sample"] == 16
    assert result["rate"] == 24000
```

## CI/CD Integration

### Fast Feedback Loop

```yaml
jobs:
  lint:  # Quick check first
    steps:
      - run: ruff check .
      - run: black --check .

  test:  # Slower tests after lint passes
    needs: lint
    steps:
      - run: pytest
```

### Test Multiple Environments

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    os: [ubuntu-latest, windows-latest]
```

## Code Quality Workflow

### Daily Development

```bash
# Before committing
ruff check montaigne/ --fix  # Fix lint issues
black montaigne/              # Format code
pytest tests/ -v             # Run tests
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
```

## Common Anti-Patterns

### 1. Testing Implementation, Not Behavior

```python
# Bad: Testing internal structure
def test_bad():
    obj = MyClass()
    assert obj._internal_list == []

# Good: Testing behavior
def test_good():
    obj = MyClass()
    assert obj.is_empty()
```

### 2. Brittle Tests

```python
# Bad: Depends on exact output format
def test_bad():
    result = generate_report()
    assert result == "Report: 5 items processed on 2024-01-15"

# Good: Tests essential behavior
def test_good():
    result = generate_report()
    assert "5 items processed" in result
```

### 3. Slow Tests

```python
# Bad: Real network call
def test_bad():
    response = requests.get("https://api.example.com")
    assert response.status_code == 200

# Good: Mocked network
def test_good():
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        response = fetch_data()
        assert response["status"] == "ok"
```

## Summary Checklist

- [ ] Tests mirror source structure
- [ ] Test names are descriptive
- [ ] Each test tests one thing
- [ ] Fixtures are focused and documented
- [ ] External dependencies are mocked
- [ ] Edge cases are covered
- [ ] CI runs on every push/PR
- [ ] Code is formatted with Black
- [ ] Code passes Ruff checks

## Course Complete!

You've learned:

1. **Testing fundamentals** - Why and how to test
2. **pytest** - Writing and running tests
3. **Fixtures** - Managing test setup
4. **Mocking** - Isolating tests from dependencies
5. **Black** - Consistent code formatting
6. **Ruff** - Fast, comprehensive linting
7. **GitHub Actions** - Automated CI/CD
8. **Best practices** - Writing maintainable tests

Now go forth and test your code! 🧪

[← Previous: GitHub Actions](07-github-actions.md) | [Back to Course Overview](README.md)

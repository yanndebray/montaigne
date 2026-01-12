# Module 1: Introduction to Testing

## Why Test?

Testing is essential for maintaining code quality and confidence in your software. Without tests:

- **Bugs slip into production** unnoticed
- **Refactoring becomes scary** - you don't know what you'll break
- **Collaboration suffers** - new team members can't verify their changes
- **Technical debt accumulates** faster

## The Testing Pyramid

```
        /\
       /  \     E2E Tests (few, slow, expensive)
      /----\
     /      \   Integration Tests (moderate)
    /--------\
   /          \ Unit Tests (many, fast, cheap)
  --------------
```

### Unit Tests
Test individual functions or classes in isolation.

```python
# Example from test_audio.py
def test_parse_standard_mime():
    """Parse standard audio/L16 MIME type."""
    result = _parse_audio_mime_type("audio/L16;rate=24000")

    assert result["bits_per_sample"] == 16
    assert result["rate"] == 24000
```

### Integration Tests
Test how components work together.

```python
# Example from test_cli.py
def test_pdf_with_valid_args(self, temp_dir):
    """PDF command with valid arguments."""
    pdf_path = temp_dir / "test.pdf"
    pdf_path.touch()

    with patch.object(sys, 'argv', ['essai', 'pdf', str(pdf_path)]):
        with patch('montaigne.config.check_dependencies', return_value=True):
            with patch('montaigne.pdf.extract_pdf_pages') as mock_extract:
                main()
                mock_extract.assert_called_once()
```

### End-to-End Tests
Test the entire application flow (not covered in this course).

## Test-Driven Development (TDD)

The TDD cycle:

1. **Red** - Write a failing test
2. **Green** - Write minimal code to pass
3. **Refactor** - Improve code while keeping tests green

```python
# Step 1: Red - Write the test first
def test_wav_header_structure():
    """Generated WAV should have correct header structure."""
    audio_data = bytes([0] * 1000)
    mime_type = "audio/L16;rate=24000"

    wav_data = _convert_to_wav(audio_data, mime_type)

    assert wav_data[:4] == b"RIFF"
    assert wav_data[8:12] == b"WAVE"

# Step 2: Green - Implement the function
# Step 3: Refactor - Clean up the code
```

## What Makes a Good Test?

### 1. **F**ast
Tests should run quickly so you run them often.

```bash
# Our test suite: 80 tests in ~5 seconds
pytest tests/ -v
# ======================= 80 passed in 4.97s =======================
```

### 2. **I**ndependent
Tests shouldn't depend on each other or run order.

```python
# Bad: Tests share state
class TestBad:
    shared_data = []

    def test_add(self):
        self.shared_data.append(1)  # Affects other tests!

    def test_check(self):
        assert len(self.shared_data) == 1  # Fails if test_add didn't run first

# Good: Each test is isolated
class TestGood:
    def test_add(self, temp_dir):  # Fresh temp_dir for each test
        data = []
        data.append(1)
        assert len(data) == 1
```

### 3. **R**epeatable
Same results every time, regardless of environment.

```python
# Bad: Depends on current time
def test_bad():
    assert get_greeting() == "Good morning"  # Fails in the afternoon!

# Good: Control the environment
def test_good():
    with patch('mymodule.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 1, 9, 0)
        assert get_greeting() == "Good morning"
```

### 4. **S**elf-validating
Tests should pass or fail automatically - no manual inspection.

```python
# Bad: Requires manual verification
def test_bad():
    result = generate_report()
    print(result)  # Developer must read this

# Good: Automatic assertion
def test_good():
    result = generate_report()
    assert "Summary" in result
    assert result["total"] > 0
```

### 5. **T**imely
Write tests close to when you write the code.

## Coverage Metrics

Coverage measures how much code your tests execute:

```bash
pytest tests/ --cov=montaigne --cov-report=term-missing
```

Output:
```
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
montaigne/pdf.py           43      0   100%
montaigne/config.py        30      5    83%   18-19, 24-29
montaigne/cli.py          252     70    72%   ...
-----------------------------------------------------
TOTAL                     929    545    41%
```

### Coverage Goals

| Level | Coverage | When to use |
|-------|----------|-------------|
| Critical | 90%+ | Payment processing, security |
| Standard | 70-80% | Most applications |
| Minimum | 50%+ | Legacy code, prototypes |

> **Note:** 100% coverage doesn't mean bug-free code. It just means every line was executed, not that every edge case was tested.

## Next Steps

In the next module, we'll dive into pytest fundamentals and learn how to write effective tests.

[Next: pytest Fundamentals →](02-pytest-fundamentals.md)

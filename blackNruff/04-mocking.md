# Module 4: Mocking & Patching

## Why Mock?

Mocking replaces real objects with fake ones to:

- **Isolate tests** from external dependencies (APIs, databases, files)
- **Control behavior** - make functions return specific values
- **Verify interactions** - check if functions were called correctly
- **Speed up tests** - avoid slow operations

## The unittest.mock Module

Python's built-in mocking library:

```python
from unittest.mock import Mock, MagicMock, patch
```

## Basic Mocking

### Mock Objects

```python
from unittest.mock import Mock

# Create a mock
mock_client = Mock()

# Configure return values
mock_client.get_data.return_value = {"key": "value"}

# Use it
result = mock_client.get_data()
assert result == {"key": "value"}

# Verify it was called
mock_client.get_data.assert_called_once()
```

### MagicMock

MagicMock supports magic methods (`__len__`, `__iter__`, etc.):

```python
from unittest.mock import MagicMock

# From tests/test_pdf.py
mock_doc = MagicMock()
mock_doc.__len__ = Mock(return_value=10)  # len(mock_doc) returns 10
mock_doc.__getitem__ = Mock(return_value=mock_page)  # mock_doc[0] works
```

## Patching

Replace objects during tests with `patch`:

### As Context Manager

```python
from unittest.mock import patch

def test_with_patch():
    with patch('module.function') as mock_func:
        mock_func.return_value = "mocked"
        result = module.function()
        assert result == "mocked"
```

### Real Example: Patching fitz (PyMuPDF)

```python
# From tests/test_pdf.py

def test_default_output_directory(self, temp_dir):
    """Default output directory should be {pdf_stem}_images/."""
    pdf_path = temp_dir / "presentation.pdf"
    pdf_path.touch()

    # Mock the fitz module
    mock_fitz = MagicMock()
    mock_doc = MagicMock()
    mock_doc.__len__ = Mock(return_value=0)
    mock_fitz.open.return_value = mock_doc

    with patch.dict(sys.modules, {'fitz': mock_fitz}):
        extract_pdf_pages(pdf_path)

    # Verify directory was created
    expected_dir = temp_dir / "presentation_images"
    assert expected_dir.exists()
```

### Patching Environment Variables

```python
# From tests/test_config.py

def test_load_api_key_from_env(self):
    """Load API key from environment variable."""
    with patch("dotenv.load_dotenv"):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key-12345"}):
            result = load_api_key()
            assert result == "test-api-key-12345"
```

### Patching sys.argv

```python
# From tests/test_cli.py

def test_pdf_requires_input(self):
    """PDF command requires input argument."""
    with patch.object(sys, 'argv', ['essai', 'pdf']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2  # argparse error
```

## Where to Patch

**Key Rule:** Patch where the object is *used*, not where it's *defined*.

```python
# mymodule.py
from os import getcwd

def get_current_dir():
    return getcwd()

# test_mymodule.py - WRONG
with patch('os.getcwd'):  # Won't work!
    ...

# test_mymodule.py - CORRECT
with patch('mymodule.getcwd'):  # Patch where it's imported
    ...
```

### Real Example

```python
# montaigne/cli.py imports like this:
def cmd_pdf(args):
    from .config import check_dependencies
    from .pdf import extract_pdf_pages
    ...

# So we patch at the source module:
with patch('montaigne.config.check_dependencies', return_value=True):
    with patch('montaigne.pdf.extract_pdf_pages') as mock_extract:
        main()
```

## Verifying Mock Calls

### Check if Called

```python
mock_func.assert_called()           # Called at least once
mock_func.assert_called_once()      # Called exactly once
mock_func.assert_not_called()       # Never called
```

### Check Arguments

```python
mock_func.assert_called_with(arg1, arg2)
mock_func.assert_called_once_with(arg1, kwarg=value)
```

### Real Example

```python
# From tests/test_pdf.py

def test_document_closed_after_extraction(self, temp_dir):
    """PDF document should be closed after extraction."""
    pdf_path = temp_dir / "test.pdf"
    pdf_path.touch()

    mock_fitz = MagicMock()
    mock_doc = MagicMock()
    mock_doc.__len__ = Mock(return_value=0)
    mock_fitz.open.return_value = mock_doc

    with patch.dict(sys.modules, {'fitz': mock_fitz}):
        extract_pdf_pages(pdf_path)

    mock_doc.close.assert_called_once()  # Verify cleanup happened
```

### Check Call Arguments

```python
# From tests/test_cli.py

def test_pdf_dpi_option(self, temp_dir):
    """PDF command respects --dpi option."""
    pdf_path = temp_dir / "test.pdf"
    pdf_path.touch()

    with patch.object(sys, 'argv', ['essai', 'pdf', str(pdf_path), '--dpi', '300']):
        with patch('montaigne.config.check_dependencies', return_value=True):
            with patch('montaigne.pdf.extract_pdf_pages') as mock_extract:
                main()
                call_kwargs = mock_extract.call_args
                assert call_kwargs.kwargs['dpi'] == 300
```

## Mock Side Effects

### Return Different Values

```python
mock.side_effect = [1, 2, 3]
mock()  # Returns 1
mock()  # Returns 2
mock()  # Returns 3
```

### Raise Exceptions

```python
mock.side_effect = ValueError("Invalid input")

with pytest.raises(ValueError):
    mock()
```

### Custom Function

```python
def custom_behavior(arg):
    if arg < 0:
        raise ValueError()
    return arg * 2

mock.side_effect = custom_behavior
assert mock(5) == 10
```

## Mocking Classes

```python
# From tests/test_config.py

def test_get_client_with_valid_key(self):
    """Client should be created with valid API key."""
    with patch("dotenv.load_dotenv"):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key"}):
            with patch("google.genai.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                result = get_gemini_client()

                mock_client_class.assert_called_once_with(api_key="test-api-key")
                assert result == mock_client
```

## Nested Patches

For complex setups, nest patches:

```python
# From tests/test_cli.py

def test_script_auto_detects_pdf(self, temp_dir):
    """Script command auto-detects PDF in current directory."""
    pdf_path = temp_dir / "presentation.pdf"
    pdf_path.touch()

    with patch.object(sys, 'argv', ['essai', 'script']):
        with patch('montaigne.cli.Path.cwd', return_value=temp_dir):
            with patch('montaigne.config.check_dependencies', return_value=True):
                with patch('montaigne.scripts.generate_scripts') as mock_gen:
                    main()
                    mock_gen.assert_called_once()
                    assert mock_gen.call_args[0][0].name == "presentation.pdf"
```

## Common Patterns

### Pattern 1: Mock External API

```python
def test_api_call():
    with patch('mymodule.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"data": "test"}
        mock_get.return_value.status_code = 200

        result = fetch_data()

        assert result["data"] == "test"
```

### Pattern 2: Mock File System

```python
def test_file_operations(tmp_path):
    # Use pytest's tmp_path instead of mocking
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    result = process_file(test_file)
    assert result == "processed content"
```

### Pattern 3: Mock Module Import

```python
# When module imports happen inside functions
def test_with_module_mock():
    mock_fitz = MagicMock()
    with patch.dict(sys.modules, {'fitz': mock_fitz}):
        # Now 'import fitz' inside functions uses our mock
        from mymodule import process_pdf
        process_pdf("test.pdf")
```

## Best Practices

1. **Mock at the right level** - Patch where used, not defined
2. **Keep mocks simple** - Only mock what's necessary
3. **Verify interactions** - Use assert_called methods
4. **Clean up properly** - Context managers handle this
5. **Prefer real objects** - Mock only external dependencies

[← Previous: Fixtures](03-fixtures.md) | [Next: Black →](05-black.md)

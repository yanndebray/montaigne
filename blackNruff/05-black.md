# Module 5: Black - The Uncompromising Code Formatter

## What is Black?

Black is an opinionated Python code formatter that enforces a consistent style across your codebase. Its philosophy: **"You can have any style you want, as long as it's Black."**

## Why Use Black?

- **No debates** - Eliminates style discussions in code reviews
- **Consistency** - Same formatting everywhere
- **Automation** - Format on save, in CI, pre-commit hooks
- **Time savings** - Focus on logic, not formatting

## Installation

```bash
pip install black
```

Or in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "black>=24.0",
]
```

## Basic Usage

```bash
# Format a file
black myfile.py

# Format a directory
black montaigne/

# Check without modifying (CI mode)
black --check montaigne/

# Show diff of changes
black --diff montaigne/
```

## What Black Does

### Line Length

Default: 88 characters (configurable)

```python
# Before
result = some_function(argument_one, argument_two, argument_three, argument_four, argument_five)

# After Black
result = some_function(
    argument_one, argument_two, argument_three, argument_four, argument_five
)
```

### String Quotes

Black prefers double quotes:

```python
# Before
name = 'montaigne'
message = "Hello"

# After Black
name = "montaigne"
message = "Hello"
```

### Trailing Commas

Black adds trailing commas in multi-line structures:

```python
# Before
my_list = [
    "item1",
    "item2",
    "item3"
]

# After Black
my_list = [
    "item1",
    "item2",
    "item3",  # Trailing comma added
]
```

### Whitespace

Consistent spacing around operators:

```python
# Before
x=1+2
y = 3 *   4

# After Black
x = 1 + 2
y = 3 * 4
```

## Configuration

Configure Black in `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py310', 'py311', 'py312']
include = '\.pyi?$'
exclude = '''
/(
    \.eggs
  | \.git
  | \.venv
  | build
  | dist
)/
'''
```

## Real Example: Before and After

### Before Black

```python
def extract_pdf_pages(pdf_path:Path,output_dir:Optional[Path]=None,dpi:int=150,image_format:str="png")->List[Path]:
    """Extract all pages from a PDF as individual images."""
    import fitz
    pdf_path=Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if output_dir is None:
        output_dir=pdf_path.parent/f"{pdf_path.stem}_images"
```

### After Black

```python
def extract_pdf_pages(
    pdf_path: Path,
    output_dir: Optional[Path] = None,
    dpi: int = 150,
    image_format: str = "png",
) -> List[Path]:
    """Extract all pages from a PDF as individual images."""
    import fitz

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if output_dir is None:
        output_dir = pdf_path.parent / f"{pdf_path.stem}_images"
```

## CI Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
lint:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.11"

    - name: Install dependencies
      run: pip install black

    - name: Check formatting with black
      run: black --check montaigne/
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
        language_version: python3.11
```

## Editor Integration

### VS Code

Install the "Black Formatter" extension, then in `settings.json`:

```json
{
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.formatOnSave": true
    }
}
```

### PyCharm

1. Go to Settings → Tools → Black
2. Enable "On save"
3. Set path to Black executable

## Common Issues

### Issue 1: Magic Trailing Comma

Black preserves your choice for single-line vs multi-line:

```python
# This stays on one line (no trailing comma)
items = [1, 2, 3]

# This stays multi-line (has trailing comma)
items = [
    1,
    2,
    3,
]
```

### Issue 2: Long Strings

Black doesn't break strings:

```python
# Black won't fix this
long_message = "This is a very long string that exceeds the line length limit but Black won't break it automatically"

# You must break it manually
long_message = (
    "This is a very long string that exceeds the line length limit "
    "but now it's properly formatted across multiple lines"
)
```

### Issue 3: Conflicts with Other Tools

Run Black before other formatters:

```bash
# Correct order
ruff check montaigne/ --fix  # Fix lint issues first
black montaigne/              # Then format
```

## Skipping Code

Use `# fmt: off` and `# fmt: on`:

```python
# fmt: off
matrix = [
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
]
# fmt: on
```

## Checking in CI

When Black fails in CI, you see:

```
would reformat montaigne/cli.py

Oh no! 💥 💔 💥
1 file would be reformatted, 10 files would be left unchanged.
```

Fix by running `black montaigne/` locally and committing.

## Summary

| Command | Purpose |
|---------|---------|
| `black file.py` | Format a file |
| `black directory/` | Format all Python files |
| `black --check .` | Check without modifying |
| `black --diff .` | Show what would change |

[← Previous: Mocking](04-mocking.md) | [Next: Ruff →](06-ruff.md)

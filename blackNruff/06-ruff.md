# Module 6: Ruff - The Fast Python Linter

## What is Ruff?

Ruff is an extremely fast Python linter written in Rust. It's 10-100x faster than existing linters and can replace Flake8, isort, pydocstyle, and more.

## Why Use Ruff?

- **Speed** - Lint entire projects in milliseconds
- **All-in-one** - Replaces multiple tools
- **Auto-fix** - Many issues can be fixed automatically
- **Drop-in replacement** - Compatible with existing configs

## Installation

```bash
pip install ruff
```

Or in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "ruff>=0.4.0",
]
```

## Basic Usage

```bash
# Check for issues
ruff check montaigne/

# Auto-fix issues
ruff check montaigne/ --fix

# Check specific file
ruff check montaigne/audio.py

# Show all available rules
ruff rule --all
```

## What Ruff Catches

### F - Pyflakes (Error Detection)

```python
# F401: Unused import
import os  # 'os' imported but unused

# F811: Redefinition
def func():
    pass
def func():  # Redefinition of 'func'
    pass

# F541: f-string without placeholders
message = f"Hello"  # Should be "Hello"
```

### E - pycodestyle (Style)

```python
# E501: Line too long
very_long_line = "this line exceeds the maximum line length of 88 characters which is not good"

# E302: Expected 2 blank lines
def func1():
    pass
def func2():  # Missing blank line
    pass
```

### I - isort (Import Sorting)

```python
# I001: Import block not sorted
import sys
import os  # Should be before sys (alphabetical)

from pathlib import Path
import json  # Standard library should be before third-party
```

## Real Issues Fixed in montaigne

### Issue 1: Unused Imports

```python
# Before
import mimetypes  # Never used in audio.py

# After (removed by ruff --fix)
# (import removed)
```

### Issue 2: Redundant f-strings

```python
# Before
print(f"Step 1: Extracting PDF pages...")  # No placeholders!

# After
print("Step 1: Extracting PDF pages...")
```

### Issue 3: Duplicate Imports

```python
# Before (cli.py)
def cmd_video(args):
    from .video import generate_video, generate_video_from_pdf, check_ffmpeg
    ...
    # Later in same function:
    from .video import generate_video  # Duplicate!

# After
def cmd_video(args):
    from .video import generate_video, generate_video_from_pdf, check_ffmpeg
    ...
    # Duplicate removed
```

### Issue 4: Unused Function Arguments

```python
# Before
from .config import check_dependencies, install_dependencies, load_api_key

def cmd_setup(args):
    # load_api_key never used!
    ...

# After
from .config import check_dependencies, install_dependencies

def cmd_setup(args):
    ...
```

## Silencing False Positives

Use `# noqa` comments for intentional patterns:

```python
# Intentional "unused" imports for dependency checking
def check_dependencies() -> bool:
    """Check if required packages are installed."""
    try:
        from dotenv import load_dotenv  # noqa: F401
        from google import genai  # noqa: F401
        import fitz  # noqa: F401

        return True
    except ImportError:
        return False
```

### noqa Syntax

```python
# Ignore specific rule
import unused  # noqa: F401

# Ignore multiple rules
x = 1  # noqa: E501, W503

# Ignore all rules (use sparingly!)
problematic_line  # noqa
```

## Configuration

Configure Ruff in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "W",   # pycodestyle warnings
]
ignore = [
    "E501",  # Line too long (handled by black)
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["F401"]  # Allow unused imports in tests
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
      run: pip install ruff

    - name: Lint with ruff
      run: ruff check montaigne/
```

## Order of Operations

When fixing code quality issues:

```bash
# 1. First: Fix lint issues with ruff
ruff check montaigne/ --fix

# 2. Second: Format with black (ruff might leave formatting issues)
black montaigne/

# 3. Third: Verify everything passes
ruff check montaigne/
black --check montaigne/
```

### Why This Order?

1. Ruff removes code (unused imports) → may leave extra blank lines
2. Black fixes formatting → ensures consistent style
3. Final check → confirms everything is clean

## Ruff vs Flake8

| Feature | Ruff | Flake8 |
|---------|------|--------|
| Speed | ~100x faster | Baseline |
| Auto-fix | Yes | No |
| Import sorting | Built-in | Needs isort |
| Type checking | No | No |
| Configuration | pyproject.toml | .flake8 or setup.cfg |

## Common Rules Reference

| Code | Description | Auto-fixable |
|------|-------------|--------------|
| F401 | Unused import | Yes |
| F403 | Star import used | No |
| F405 | Name from star import | No |
| F541 | f-string without placeholders | Yes |
| F811 | Redefinition of unused name | Yes |
| F841 | Local variable never used | Yes |
| E501 | Line too long | No |
| E711 | Comparison to None | Yes |
| E712 | Comparison to True/False | Yes |
| I001 | Import block unsorted | Yes |

## Checking CI Failures

When Ruff fails in CI:

```
F401 `mimetypes` imported but unused
  --> montaigne/audio.py:4:8
   |
 3 | import base64
 4 | import mimetypes
   |        ^^^^^^^^^
 5 | import re
   |
help: Remove unused import: `mimetypes`

Found 5 errors (3 fixed, 2 remaining).
```

Fix by running:
```bash
ruff check montaigne/ --fix
black montaigne/  # Clean up any formatting issues
git add -A && git commit -m "Fix lint errors"
```

## Summary

| Command | Purpose |
|---------|---------|
| `ruff check .` | Check for issues |
| `ruff check . --fix` | Auto-fix issues |
| `ruff check . --select F` | Check only Pyflakes rules |
| `ruff rule F401` | Explain a specific rule |

[← Previous: Black](05-black.md) | [Next: GitHub Actions →](07-github-actions.md)

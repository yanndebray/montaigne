# Python Testing & Code Quality Course

A comprehensive guide to testing Python projects, illustrated with real examples from the [montaigne](https://github.com/yanndebray/montaigne) project.

## Course Overview

This course covers everything you need to know about testing Python applications and maintaining code quality:

| Module | Topic | Duration |
|--------|-------|----------|
| 01 | [Introduction to Testing](01-introduction.md) | 15 min |
| 02 | [pytest Fundamentals](02-pytest-fundamentals.md) | 30 min |
| 03 | [Fixtures & Test Organization](03-fixtures.md) | 25 min |
| 04 | [Mocking & Patching](04-mocking.md) | 35 min |
| 05 | [Black - Code Formatter](05-black.md) | 15 min |
| 06 | [Ruff - Fast Linter](06-ruff.md) | 20 min |
| 07 | [GitHub Actions CI/CD](07-github-actions.md) | 25 min |
| 08 | [Best Practices](08-best-practices.md) | 20 min |

## Prerequisites

- Python 3.10+
- Basic Python knowledge
- Git fundamentals

## Quick Start

```bash
# Clone the example project
git clone https://github.com/yanndebray/montaigne.git
cd montaigne

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=montaigne

# Check formatting
black --check montaigne/

# Run linter
ruff check montaigne/
```

## Project Structure

```
montaigne/
├── montaigne/           # Source code
│   ├── __init__.py
│   ├── cli.py          # Command-line interface
│   ├── config.py       # Configuration handling
│   ├── pdf.py          # PDF extraction
│   ├── audio.py        # Audio generation
│   └── scripts.py      # Script generation
├── tests/              # Test suite
│   ├── __init__.py
│   ├── conftest.py     # Shared fixtures
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_pdf.py
│   ├── test_audio.py
│   └── test_scripts.py
├── .github/
│   └── workflows/
│       └── test.yml    # CI configuration
└── pyproject.toml      # Project & tool config
```

## Learning Outcomes

By the end of this course, you will be able to:

1. **Write effective tests** using pytest with proper organization
2. **Create reusable fixtures** for test setup and teardown
3. **Mock external dependencies** like APIs and file systems
4. **Maintain code quality** with Black and Ruff
5. **Set up CI/CD pipelines** with GitHub Actions
6. **Apply testing best practices** to real-world projects

## Author

Created with Claude Code as part of the montaigne project development.

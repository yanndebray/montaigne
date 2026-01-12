# Module 7: GitHub Actions CI/CD

## What is CI/CD?

- **CI (Continuous Integration)** - Automatically test code on every push
- **CD (Continuous Deployment)** - Automatically deploy passing code

## GitHub Actions Basics

Workflows are defined in `.github/workflows/*.yml` files.

```
.github/
└── workflows/
    ├── test.yml       # Run tests on push/PR
    └── publish.yml    # Publish to PyPI on release
```

## Anatomy of a Workflow

```yaml
# .github/workflows/test.yml

name: Tests                    # Workflow name (shown in GitHub UI)

on:                            # Triggers
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:                          # Jobs to run
  test:                        # Job name
    runs-on: ubuntu-latest     # Runner OS
    steps:                     # Steps in the job
      - uses: actions/checkout@v4
      - name: Run tests
        run: pytest
```

## The montaigne CI Workflow

```yaml
# .github/workflows/test.yml

name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests with coverage
        run: |
          pytest --cov=montaigne --cov-report=xml --cov-report=term-missing

      - name: Upload coverage to Codecov
        if: matrix.python-version == '3.11'
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff black

      - name: Check formatting with black
        run: black --check montaigne/

      - name: Lint with ruff
        run: ruff check montaigne/
```

## Key Concepts

### Triggers (`on`)

```yaml
on:
  push:
    branches: [main, develop]   # Push to these branches
  pull_request:
    branches: [main]            # PRs targeting main
  schedule:
    - cron: '0 0 * * *'         # Daily at midnight
  workflow_dispatch:             # Manual trigger button
```

### Matrix Strategy

Test across multiple Python versions:

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    os: [ubuntu-latest, windows-latest, macos-latest]
```

This creates 12 jobs (4 Python × 3 OS).

### Steps

```yaml
steps:
  # Use a pre-built action
  - uses: actions/checkout@v4

  # Run a command
  - name: Install dependencies
    run: pip install -e ".[dev]"

  # Multi-line commands
  - name: Build and test
    run: |
      python -m build
      pytest tests/
```

### Conditional Steps

```yaml
- name: Upload coverage
  if: matrix.python-version == '3.11'  # Only for Python 3.11
  uses: codecov/codecov-action@v4

- name: Deploy
  if: github.ref == 'refs/heads/main'  # Only on main branch
  run: ./deploy.sh
```

## Common Actions

### Checkout Code

```yaml
- uses: actions/checkout@v4
```

### Setup Python

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.11"
    cache: 'pip'  # Cache pip packages
```

### Cache Dependencies

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

### Upload Artifacts

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: test-results/
```

## Separate Jobs

Jobs run in parallel by default:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pytest

  lint:
    runs-on: ubuntu-latest
    steps:
      - run: ruff check .

  # Both test and lint run simultaneously
```

### Job Dependencies

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pytest

  deploy:
    needs: test  # Wait for test to pass
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh
```

## Secrets and Environment Variables

### Using Secrets

```yaml
- name: Deploy
  env:
    API_KEY: ${{ secrets.API_KEY }}
  run: ./deploy.sh
```

### Setting Environment Variables

```yaml
env:
  PYTHONPATH: .
  CI: true

jobs:
  test:
    env:
      DATABASE_URL: sqlite:///test.db
```

## Debugging CI Failures

### 1. Check the Logs

Click on the failed job in GitHub to see full output.

### 2. View Failed Step

```
lint   Check formatting with black
2026-01-12T01:15:48Z would reformat montaigne/cli.py
2026-01-12T01:15:48Z Oh no! 💥 💔 💥
2026-01-12T01:15:48Z ##[error]Process completed with exit code 1.
```

### 3. Reproduce Locally

```bash
# Run the same commands locally
black --check montaigne/
ruff check montaigne/
pytest tests/
```

### 4. Use the GitHub CLI

```bash
# List recent runs
gh run list --limit 5

# View failed run logs
gh run view 20905186056 --log-failed
```

## Workflow Status Badges

Add to your README:

```markdown
![Tests](https://github.com/yanndebray/montaigne/actions/workflows/test.yml/badge.svg)
```

Displays: ![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

## Publishing to PyPI

```yaml
# .github/workflows/publish.yml
name: Upload Python Package

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install build twine

      - name: Build package
        run: python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

## Best Practices

1. **Keep workflows fast** - Use caching, parallel jobs
2. **Test multiple versions** - Use matrix strategy
3. **Fail fast** - Put quick checks (lint) before slow ones (tests)
4. **Use official actions** - `actions/*` are maintained by GitHub
5. **Pin action versions** - Use `@v4` not `@main`

## Summary

| File | Purpose |
|------|---------|
| `.github/workflows/test.yml` | Run tests and linting |
| `.github/workflows/publish.yml` | Publish to PyPI |

| Command | Purpose |
|---------|---------|
| `gh run list` | List workflow runs |
| `gh run view ID` | View run details |
| `gh run view ID --log-failed` | View failed logs |

[← Previous: Ruff](06-ruff.md) | [Next: Best Practices →](08-best-practices.md)

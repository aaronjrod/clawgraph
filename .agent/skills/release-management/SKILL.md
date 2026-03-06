---
name: Release Management
description: Guidelines for managing versions, PyPI publishing, and CI/CD badges for ClawGraph.
---
# Release Management Skill

This skill provides comprehensive instructions for managing the ClawGraph release pipeline, ensuring consistent versioning, successful PyPI publishing, and accurate CI/CD reporting.

## PyPI Publishing

ClawGraph uses `pyproject.toml` for metadata and `uv` or `pip` with `build` and `twine` for distribution.

### Prerequisites
- Ensure your `~/.pypirc` is configured with a valid PyPI API token.
- Install build tools: `uv pip install build twine`.

### Publishing Steps
1. **Bump Version**: Update the `version` field in `pyproject.toml`.
2. **Clean Builds**: Delete existing `dist/` and `build/` directories.
3. **Build Package**: `python -m build`
4. **Upload**: `twine upload dist/*`

## CI/CD Architecture

The project uses GitHub Actions (defined in `.github/workflows/test.yml`) optimized with `uv`.

### Key Features
- **Fast Installation**: Uses `astral-sh/setup-uv` for lightning-fast dependency resolution and caching.
- **Local Coverage Badge**: Instead of external services, the CI manually generates `coverage.svg` and commits it back to the branch.
- **Code Quality**: Runs `ruff` for linting/formatting and `mypy` for static type checking across multiple Python versions (3.11, 3.12).

## Badge Management

The coverage badge is self-hosted within the repository.

- **Generation**: The badge is generated during the CI run using a custom Python script that parses `coverage.json`.
- **Location**: `coverage.svg` at the project root.
- **README Implementation**: Uses a relative path `![Coverage](./coverage.svg)` to ensure it renders correctly on all branches.

## Dependency Management

- Use `uv` for all local development tasks to maintain parity with the CI environment.
- To install the project in editable mode with all dev dependencies: `uv pip install -e ".[dev]"`.

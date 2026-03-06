---
description: Automated steps for preparing and executing a new ClawGraph release
---
# ClawGraph Release Workflow

Use this workflow to prepare the repository for a new release.

## Steps

1. **Verify State**
   - Ensure you are on the `main` branch: `git checkout main && git pull`
   - Ensure all tests pass: `pytest`

2. **Bump Version**
   - Identify the new version number (e.g., `0.1.2`).
   - Update `pyproject.toml` version field.

3. **Build & Test**
   - Clear old artifacts: `rm -rf dist/ build/ *.egg-info`
   - Build package: `python -m build`
   - Verify package contents: `ls -l dist/`

4. **Tag & Push**
   - Commit the version bump: `git add pyproject.toml && git commit -m "chore: bump version to X.Y.Z"`
   - Create a git tag: `git tag -a vX.Y.Z -m "Release X.Y.Z"`
   - Push changes and tags: `git push origin main --tags`

5. **Publish to PyPI**
   - Upload distribution: `twine upload dist/*`

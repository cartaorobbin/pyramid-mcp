# Publishing to PyPI with GitHub Actions

This document outlines how to publish the `pyramid-mcp` package to PyPI using GitHub Actions with trusted publishing.

## Overview

The project uses GitHub Actions to automatically publish to PyPI when a new release is created. This is implemented using:

- **Trusted Publishing**: Secure publishing without API tokens
- **Automated Versioning**: Version extracted from Git tags
- **Quality Checks**: Tests and code quality checks before publishing
- **Package Verification**: Ensures the package is correctly built before publishing

## Prerequisites

### 1. PyPI Account and Package Registration

1. **Create a PyPI account** at [pypi.org](https://pypi.org/account/register/)
2. **Register the package name** (reserve it):
   ```bash
   # First, build and upload manually to reserve the name
   poetry build
   poetry publish
   ```
   Or create a dummy package with just the name to reserve it.

### 2. Set Up Trusted Publishing on PyPI

1. **Log in to PyPI** and go to your account settings
2. **Navigate to "Publishing"** section
3. **Add a new publisher** with these details:
   - **PyPI project name**: `pyramid-mcp`
   - **Owner**: Your GitHub username or organization
   - **Repository name**: `pyramid-mcp`
   - **Workflow name**: `on-release-pypi.yml`
   - **Environment name**: `pypi`

This allows GitHub Actions to publish to PyPI without storing API tokens as secrets.

### 3. Update Repository URLs

Make sure the URLs in `pyproject.toml` match your actual repository:

```toml
[tool.poetry]
homepage = "https://github.com/YOUR_USERNAME/pyramid-mcp"
repository = "https://github.com/YOUR_USERNAME/pyramid-mcp"
documentation = "https://YOUR_USERNAME.github.io/pyramid-mcp"
```

## Publishing Workflow

The publishing process is fully automated:

### 1. Create a Release

```bash
# Create and push a new tag
git tag v0.1.0
git push origin v0.1.0

# Or create a release through GitHub UI
# Go to: https://github.com/YOUR_USERNAME/pyramid-mcp/releases/new
```

### 2. Automatic Publishing

When you create a GitHub release:

1. **Tests run**: All tests and quality checks must pass
2. **Version extraction**: Version is extracted from the release tag
3. **Package building**: Package is built with Poetry
4. **Verification**: Package contents are verified with `twine check`
5. **Publishing**: Package is published to PyPI using trusted publishing

### 3. Version Management

The workflow automatically handles versioning:

- **Release tag**: `v1.0.0` → **Package version**: `1.0.0`
- **Release tag**: `1.0.0` → **Package version**: `1.0.0`
- **Release tag**: `v1.0.0-beta.1` → **Package version**: `1.0.0-beta.1`

## Workflow Files

### PyPI Publishing Workflow

`.github/workflows/on-release-pypi.yml`:
- Triggers on GitHub release creation
- Uses trusted publishing (no API tokens needed)
- Automatic version management
- Package verification before publishing

### Main CI Workflow

`.github/workflows/main.yml`:
- Runs on every push and pull request
- Tests across Python 3.10, 3.11, 3.12
- Code quality checks (black, isort, flake8, mypy)
- Coverage reporting

## Manual Publishing (Development)

For development and testing:

### Test Publishing to TestPyPI

1. **Set up TestPyPI trusted publishing** (same steps as PyPI)
2. **Create a test workflow** or modify the existing one:

```yaml
- name: Publish to TestPyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    repository-url: https://test.pypi.org/legacy/
```

### Local Publishing

For manual publishing from local development:

```bash
# Build the package
poetry build

# Check the package
poetry run twine check dist/*

# Publish to TestPyPI
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry publish -r testpypi

# Publish to PyPI
poetry publish
```

## Pre-Release Checklist

Before creating a release:

- [ ] **All tests pass**: `make test`
- [ ] **Code quality checks pass**: `make check`  
- [ ] **Documentation is updated**: Update README, CHANGELOG, docs
- [ ] **Version is updated**: Update version in both `pyproject.toml` and `pyramid_mcp/version.py`
- [ ] **Dependencies are up to date**: `poetry update`
- [ ] **Test installation**: Test package installation in a clean environment

## Post-Release Verification

After publishing:

1. **Check PyPI**: Verify package appears on [pypi.org/project/pyramid-mcp](https://pypi.org/project/pyramid-mcp)
2. **Test installation**: `pip install pyramid-mcp`
3. **Test functionality**: Run basic tests to ensure the package works
4. **Update documentation**: Update any version-specific documentation

## Troubleshooting

### Common Issues

#### "Repository not found" Error
- Verify repository URLs in `pyproject.toml`
- Check that the repository is public (or has appropriate permissions)

#### "Trusted publisher not configured" Error
- Ensure trusted publishing is set up correctly on PyPI
- Check that the workflow name, environment, and repository details match

#### "Package already exists" Error
- Cannot republish the same version
- Increment the version number and create a new release

#### "Tests failing" Error
- All tests must pass before publishing
- Check the CI workflow for specific failures
- Fix issues and push changes before creating release

### Debugging

Check the GitHub Actions logs:
1. Go to your repository on GitHub
2. Click "Actions" tab
3. Click on the failed workflow run
4. Examine the logs for specific error messages

## Security Considerations

- **No API tokens**: Using trusted publishing eliminates the need for API tokens
- **Environment protection**: The `pypi` environment can be protected with additional rules
- **Branch protection**: Ensure main branch is protected and requires reviews
- **Release permissions**: Control who can create releases in your repository

## Best Practices

1. **Semantic versioning**: Use semantic versioning (e.g., `v1.0.0`, `v1.0.1`, `v1.1.0`)
2. **Pre-release testing**: Always test on TestPyPI first
3. **Changelog maintenance**: Keep CHANGELOG.md updated
4. **Documentation**: Update documentation with each release
5. **Security scanning**: Regularly scan dependencies for vulnerabilities

## Resources

- [PyPI Trusted Publishing Guide](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions for PyPI](https://github.com/pypa/gh-action-pypi-publish)
- [Poetry Publishing Documentation](https://python-poetry.org/docs/repositories/)
- [Semantic Versioning](https://semver.org/) 
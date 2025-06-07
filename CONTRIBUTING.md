# Contributing to pyramid-mcp

We love your input! We want to make contributing to pyramid-mcp as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

### Pull Requests

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Development Setup

### Prerequisites

- Python 3.9+
- Poetry (for dependency management)

### Quick Start

```bash
# Clone your fork
git clone https://github.com/your-username/pyramid-mcp.git
cd pyramid-mcp

# Install dependencies and pre-commit hooks
make install

# Run tests
make test

# Run code quality checks
make check

# Build documentation
make docs
```

### Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b bugfix/issue-description
   ```

2. **Make your changes**
   - Write clear, self-documenting code
   - Add docstrings to all public functions and classes
   - Include type hints where appropriate
   - Follow PEP 8 style guidelines

3. **Test your changes**
   ```bash
   make test              # Run tests
   make check            # Run linters and formatters
   tox                   # Test across Python versions (optional)
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

We use several tools to maintain code quality:

- **black**: Code formatting
- **isort**: Import sorting  
- **flake8**: Linting
- **mypy**: Type checking
- **pre-commit**: Automated checks

These are automatically run by `make check` and enforced by pre-commit hooks.

### Code Style Guidelines

- Use descriptive variable and function names
- Write docstrings for all public functions and classes
- Keep functions small and focused
- Use type hints for function parameters and return values
- Follow PEP 8 conventions

### Example Function

```python
def calculate_mcp_response(request: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate MCP response based on request data.
    
    Args:
        request: The MCP request dictionary containing method and params.
        
    Returns:
        A dictionary containing the MCP response.
        
    Raises:
        ValueError: If the request format is invalid.
    """
    if not isinstance(request, dict):
        raise ValueError("Request must be a dictionary")
    
    # Implementation here
    return {"result": "success"}
```

## Testing

### Test Structure

```
tests/
├── conftest.py                     # Comprehensive fixtures (16+ fixtures)
├── test_unit_core.py               # Core functionality unit tests (15 tests)
├── test_unit_protocol.py           # MCP protocol unit tests (16 tests)
├── test_unit_introspection.py      # Route discovery unit tests (21 tests)
├── test_integration_webtest.py     # HTTP integration tests (20 tests)
├── test_integration_plugin.py      # Plugin integration tests (15 tests)
├── test_integration_end_to_end.py  # End-to-end tests (7 tests)
└── README.md                       # Test documentation
```

**Total: 94 tests with 76% coverage**

#### File Purposes

- **Unit tests** (`test_unit_*.py`): Test individual components in isolation
- **Integration tests** (`test_integration_*.py`): Test component interactions
- **Fixtures** (`conftest.py`): Reusable test setup organized by category
- **Documentation** (`README.md`): Comprehensive test organization guide

### Writing Tests

- Use pytest for all tests
- Follow the AAA pattern (Arrange, Act, Assert)
- Use descriptive test names
- Test both success and failure cases
- Use fixtures for common setup

### Example Test

```python
def test_mcp_tool_registration():
    """Test that MCP tools can be registered correctly."""
    # Arrange
    mcp = PyramidMCP()
    
    @mcp.tool
    def sample_tool(message: str) -> str:
        return f"Hello, {message}!"
    
    # Act
    tools = mcp.list_tools()
    
    # Assert
    assert len(tools) == 1
    assert tools[0]["name"] == "sample_tool"
```

## Documentation

We use MkDocs for documentation. Documentation files are in the `docs/` directory.

### Writing Documentation

- Use clear, concise language
- Include code examples
- Keep examples up-to-date
- Use proper Markdown formatting

### Building Documentation

```bash
poetry run mkdocs serve    # Serve locally at http://localhost:8000
poetry run mkdocs build    # Build static files
```

## Issue Reporting

### Bug Reports

Use the bug report template and include:

- A quick summary and/or background
- Steps to reproduce
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

### Feature Requests

Use the feature request template and include:

- Problem description
- Proposed solution
- Alternative solutions considered
- Additional context

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue for any questions about contributing! 
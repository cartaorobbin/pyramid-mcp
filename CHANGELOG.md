# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Preparing for initial PyPI release

## [0.1.0] - 2024-01-XX

### Added
- Initial release of pyramid-mcp
- Core MCP protocol implementation
- Pyramid plugin integration with `config.include('pyramid_mcp')`
- `@tool` decorator for registering MCP tools
- HTTP and SSE protocol support
- Settings-based configuration
- Request-level MCP access (`request.mcp`)
- Comprehensive test suite with 75% coverage
- Complete documentation and examples
- Type hints throughout the codebase
- Marshmallow integration for schema validation

### Features
- **Tool Registration**: Simple decorator-based tool registration
- **Multiple Protocols**: HTTP POST and Server-Sent Events support
- **Pyramid Integration**: Native integration with Pyramid's configuration system
- **Schema Validation**: Optional Marshmallow schema validation for tools
- **Error Handling**: Proper MCP error responses for validation and runtime errors
- **Configuration**: Flexible settings-based configuration
- **Examples**: Complete example applications in `examples/` directory

### Technical Details
- Python 3.9+ support
- Pyramid 2.0+ compatibility
- MIT License
- Poetry-based dependency management
- Pre-commit hooks for code quality
- GitHub Actions CI/CD pipeline ready

### Breaking Changes
- None (initial release)

### Security
- No known security issues
- All dependencies are well-maintained and secure
- No sensitive data or credentials in code

### Documentation
- Comprehensive README with installation and usage instructions
- API documentation with mkdocs
- Troubleshooting guide
- Multiple usage examples
- Contributing guidelines

---

## Release Notes

### Version 0.1.0 - Initial Release

This is the first public release of pyramid-mcp, providing a solid foundation for integrating Model Context Protocol (MCP) with Pyramid web applications.

**Key Features:**
- Easy integration with existing Pyramid applications
- Simple tool registration with decorators
- Multiple protocol support (HTTP, SSE)
- Comprehensive documentation and examples
- High test coverage (75%)

**Getting Started:**
```bash
pip install pyramid-mcp
```

See the [README](README.md) for complete usage instructions and examples.

**What's Next:**
- Route discovery functionality (planned for v0.2.0)
- Additional protocol support
- Enhanced introspection capabilities
- More examples and tutorials

**Feedback Welcome:**
This is our initial release - we'd love to hear your feedback! Please report issues, suggest features, or contribute to the project on [GitHub](https://github.com/your-org/pyramid-mcp). 
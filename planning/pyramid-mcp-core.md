# Feature Planning: Pyramid MCP Core Library

## Feature Overview

**Feature Name**: Pyramid MCP Core Library
**Description**: A library that exposes Pyramid web application endpoints as Model Context Protocol (MCP) tools, inspired by fastapi_mcp but adapted for the Pyramid web framework ecosystem.
**Priority**: High
**Estimated Effort**: 2-3 weeks
**Dependencies**: 
- Pyramid web framework
- MCP (Model Context Protocol) specification
- Understanding of WSGI vs ASGI differences
- JSON Schema generation for Pyramid views

## Key Design Principles

Based on fastapi_mcp analysis and Pyramid's philosophy:

1. **Pyramid-Native Approach**: Work directly with Pyramid's configurator, views, and routing system
2. **Start Small, Finish Big**: Follow Pyramid's philosophy - minimal config to start, comprehensive features for complex needs
3. **Authentication Integration**: Utilize Pyramid's security system and ACL
4. **WSGI Transport**: Adapt MCP to work with WSGI instead of ASGI
5. **Preserve Pyramid Patterns**: Maintain Pyramid's decorator-based view configuration
6. **Schema Preservation**: Extract and preserve request/response schemas from Pyramid views

## Tasks for Pyramid MCP Core Library

### [2025-01-27] Research and Architecture Design

**Status**: DONE
**Assigned**: Assistant
**Estimated Time**: 8 hours
**Related Issue**: N/A
**Related PR**: N/A

#### Plan
- [ ] Deep dive into fastapi_mcp codebase structure and patterns
- [ ] Analyze Pyramid's introspection capabilities for route discovery
- [ ] Research MCP protocol specification and requirements
- [ ] Design WSGI-compatible MCP transport layer
- [ ] Plan authentication/authorization integration with Pyramid security
- [ ] Design schema extraction from Pyramid views and models
- [ ] Create high-level architecture diagram
- [ ] Define public API surface for the library

#### Progress
- [x] Research fastapi_mcp architecture and patterns
- [x] Study MCP protocol specification (JSON-RPC 2.0 based)
- [x] Understand transport layer requirements
- [x] Analyze FastAPI vs Pyramid differences
- [ ] Create high-level architecture diagram
- [ ] Define public API surface for the library

#### Decisions Made
- Decision 1: Use Pyramid's introspection system for automatic endpoint discovery
- Decision 2: Leverage Pyramid's traversal and URL generation for MCP tool routing
- Decision 3: Create WSGI middleware/app for MCP server functionality
- Decision 4: MCP uses JSON-RPC 2.0 messages, compatible with WSGI
- Decision 5: Support both SSE and standard HTTP transports like fastapi_mcp
- Decision 6: Follow fastapi_mcp's pattern of mounting MCP server to existing app
- Decision 7: Use Marshmallow for schema definition and validation (user preference)
- Decision 8: Generate JSON Schema from Marshmallow schemas for MCP compatibility

#### Research Findings
- **FastAPI-MCP Features**: Auto tool registration, ASGI transport, authentication integration, zero-config setup
- **MCP Protocol**: JSON-RPC 2.0 messages, server capabilities (tools/resources/prompts), client capabilities (sampling)
- **Transport Options**: HTTP, SSE, WebSocket, Stdio - we'll focus on HTTP and SSE for WSGI compatibility
- **Key MCP Messages**: initialize, list_tools, call_tool, list_resources, read_resource, etc.
- **Authentication**: MCP supports server-side authentication, aligns with Pyramid's security model

#### Blockers/Issues
- ✅ Resolved: WSGI can handle JSON-RPC over HTTP/SSE effectively
- ✅ Resolved: MCP protocol is stateful but works with HTTP request/response pattern

#### Testing Strategy
- [ ] Unit tests for core components
- [ ] Integration tests with sample Pyramid applications
- [ ] Test authentication scenarios
- [ ] Test schema generation accuracy
- [ ] Test MCP protocol compliance

#### Documentation Tasks
- [ ] Architecture documentation
- [ ] API reference documentation
- [ ] Integration guide for existing Pyramid apps
- [ ] Migration guide from other MCP implementations

---

### [2025-01-27] Core MCP Protocol Implementation

**Status**: DONE
**Assigned**: Assistant
**Estimated Time**: 16 hours
**Related Issue**: N/A
**Related PR**: N/A

#### Plan
- [ ] Implement MCP message handling (JSON-RPC over transport)
- [ ] Create WSGI-compatible MCP server application
- [ ] Implement MCP protocol methods: initialize, list_tools, call_tool
- [ ] Handle MCP protocol errors and responses
- [ ] Create transport abstraction for future extensibility
- [ ] Implement proper MCP protocol versioning

#### Progress
- [ ] Pending architecture completion

#### Decisions Made
- Decision 1: Use JSON-RPC 2.0 for MCP message format
- Decision 2: Create separate WSGI app that can be mounted or run standalone

#### Testing Strategy
- [ ] MCP protocol compliance tests
- [ ] Message handling unit tests
- [ ] Transport layer tests

---

### [2025-01-27] Pyramid Integration Layer

**Status**: TODO  
**Assigned**: Assistant
**Estimated Time**: 20 hours
**Related Issue**: N/A
**Related PR**: N/A

#### Plan
- [ ] Create PyramidMCP main class (equivalent to FastApiMCP)
- [ ] Implement automatic Pyramid route discovery using introspection
- [ ] Extract view configurations and metadata
- [ ] Generate MCP tool definitions from Pyramid views
- [ ] Handle Pyramid-specific decorators and configurations
- [ ] Implement view filtering and inclusion/exclusion logic
- [ ] Create mounting mechanism for embedding MCP in existing Pyramid apps
- [ ] Support standalone MCP server deployment

#### Progress
- [ ] Pending core MCP implementation

#### Decisions Made
- Decision 1: Use Pyramid's `pyramid.interfaces.IRouteRequest` for route discovery
- Decision 2: Support both imperative and declarative view configurations
- Decision 3: Provide decorator-based MCP tool configuration

#### Testing Strategy
- [ ] Integration tests with various Pyramid view patterns
- [ ] Route discovery accuracy tests
- [ ] View metadata extraction tests

---

### [2025-01-27] Schema Generation and Documentation

**Status**: TODO
**Assigned**: Assistant  
**Estimated Time**: 12 hours
**Related Issue**: N/A
**Related PR**: N/A

#### Plan
- [ ] Implement request schema generation from Pyramid view callables
- [ ] Implement response schema generation (challenging without native OpenAPI)
- [ ] Support for common serialization libraries (JSON, Colander, etc.)
- [ ] Extract and preserve endpoint documentation from docstrings
- [ ] Generate JSON Schema for MCP tool parameters
- [ ] Handle Pyramid-specific request/response patterns
- [ ] Support custom schema annotations

#### Progress
- [ ] Pending integration layer completion

#### Decisions Made
- Decision 1: Support multiple schema libraries but don't require them
- Decision 2: Use type hints and docstrings when available
- Decision 3: Provide manual schema override mechanisms

#### Testing Strategy
- [ ] Schema generation accuracy tests
- [ ] Documentation extraction tests
- [ ] JSON Schema validation tests

---

### [2025-01-27] Authentication and Security Integration

**Status**: TODO
**Assigned**: Assistant
**Estimated Time**: 10 hours  
**Related Issue**: N/A
**Related PR**: N/A

#### Plan
- [ ] Integrate with Pyramid's security system
- [ ] Support ACL-based authorization for MCP tools
- [ ] Handle authentication contexts in MCP calls
- [ ] Implement security policy integration
- [ ] Support custom authentication callbacks
- [ ] Handle authenticated requests in MCP context
- [ ] Provide security configuration options

#### Progress
- [ ] Pending integration layer completion

#### Decisions Made
- Decision 1: Respect existing Pyramid security configurations
- Decision 2: Allow per-tool security configuration
- Decision 3: Support both authentication and authorization

#### Testing Strategy
- [ ] Authentication flow tests
- [ ] Authorization policy tests  
- [ ] Security integration tests

---

### [2025-01-27] Documentation and Examples

**Status**: TODO
**Assigned**: Assistant
**Estimated Time**: 8 hours
**Related Issue**: N/A
**Related PR**: N/A

#### Plan
- [ ] Create comprehensive README with quick start guide
- [ ] Write API reference documentation
- [ ] Create example applications showing different usage patterns
- [ ] Write migration guide from fastapi_mcp
- [ ] Document best practices and patterns
- [ ] Create troubleshooting guide
- [ ] Add docstrings to all public APIs

#### Progress
- [ ] Pending core implementation

#### Testing Strategy
- [ ] Documentation accuracy tests
- [ ] Example application tests
- [ ] Tutorial step-by-step verification

---

### [2025-01-27] Testing and Quality Assurance

**Status**: TODO
**Assigned**: Assistant
**Estimated Time**: 12 hours
**Related Issue**: N/A
**Related PR**: N/A

#### Plan
- [ ] Achieve 80%+ test coverage
- [ ] Create comprehensive test suite structure
- [ ] Add integration tests with real Pyramid applications
- [ ] Performance testing and optimization
- [ ] Memory usage analysis
- [ ] Cross-platform compatibility testing
- [ ] MCP protocol compliance verification

#### Progress
- [ ] Pending implementation phases

#### Testing Strategy
- [ ] Unit tests for all core components
- [ ] Integration tests for Pyramid integration
- [ ] End-to-end MCP protocol tests
- [ ] Performance benchmarks

---

## Architecture Overview

### Core Components

1. **PyramidMCP**: Main facade class
   - Auto-discovers Pyramid routes and views
   - Configures MCP tool generation
   - Handles mounting and deployment options

2. **MCPServer**: WSGI-compatible MCP protocol server
   - Handles JSON-RPC message processing
   - Manages MCP protocol lifecycle
   - Provides transport abstraction

3. **ToolGenerator**: Converts Pyramid views to MCP tools
   - Extracts schemas and documentation
   - Handles authentication integration
   - Manages tool filtering and configuration

4. **SchemaExtractor**: Generates JSON schemas
   - Supports multiple schema libraries
   - Handles Pyramid-specific patterns
   - Provides fallback mechanisms

5. **SecurityIntegration**: Handles authentication/authorization
   - Integrates with Pyramid security
   - Manages authenticated MCP calls
   - Provides security configuration

### Key Differences from FastAPI-MCP

1. **WSGI vs ASGI**: Adapted for WSGI-based applications
2. **Route Discovery**: Uses Pyramid's introspection instead of OpenAPI
3. **Security Model**: Integrates with Pyramid's ACL and security policies
4. **Configuration Style**: Follows Pyramid's configurator pattern
5. **Schema Generation**: More manual approach due to lack of native OpenAPI

### Example Usage (Planned)

```python
from pyramid.config import Configurator
from pyramid_mcp import PyramidMCP

def create_app():
    config = Configurator()
    
    # Configure your Pyramid app
    config.add_route('users', '/users')
    config.add_route('user', '/users/{id}')
    config.scan()
    
    # Add MCP capabilities
    mcp = PyramidMCP(config)
    mcp.mount('/mcp')  # Mount at /mcp endpoint
    
    return config.make_wsgi_app()

# Or standalone MCP server
def create_mcp_server():
    # Point at existing Pyramid app
    app = create_app()
    mcp = PyramidMCP.from_wsgi_app(app)
    return mcp.make_mcp_server()
```

## Feature Completion Checklist

When feature is complete, verify:

- [ ] All planned tasks are marked DONE
- [ ] Tests are written and passing (80%+ coverage)
- [ ] Code follows project standards (Poetry, pre-commit, etc.)
- [ ] Documentation is comprehensive and accurate
- [ ] Feature is manually tested with sample Pyramid apps
- [ ] Code is reviewed and merged
- [ ] Feature is packaged and can be installed
- [ ] planning/general.md is updated with completion
- [ ] README.md is updated with library description

## Archive

Move completed tasks here to keep the active section clean.

### Completed Tasks
<!-- Move finished task entries here --> 
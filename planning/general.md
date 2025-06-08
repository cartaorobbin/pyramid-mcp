# General Project Tasks and Infrastructure

This file tracks current and active tasks, infrastructure improvements, and cross-cutting concerns for the pyramid-mcp project.

## 🚧 ACTIVE TASKS

### [2025-06-08] Docker Integration for Pyramid MCP Examples

**Status**: IN PROGRESS 🚧
**Assigned**: Assistant  
**Estimated Time**: 2-3 hours
**Related Issue**: Claude Desktop integration issues with path configuration

#### Problem Analysis
**Current Issues:**
- Claude Desktop expects command-based MCP server configuration
- Requires absolute paths to Python executables and script files  
- Path configuration is error-prone and system-dependent
- Virtual environment paths vary between systems

**Goal:**
- Make Claude Desktop integration simple and reliable using HTTP transport
- Eliminate path configuration issues completely
- Provide consistent Docker environment across all systems

#### Solution Strategy
**Approach:** Docker container with HTTP endpoint for Claude Desktop
```
Claude Desktop → HTTP Request → Docker Container:8080 → MCP Server
```

#### Detailed Task Plan

**Phase 1: Docker Container Creation - COMPLETE ✅**
- [x] **Task 1.1: Create Multi-stage Dockerfile** ✅
- [x] **Task 1.2: ~~Create Docker Compose Configuration~~ REMOVED** ✅
- [x] **Task 1.3: Create individual pyproject.toml for each example** ✅

**Phase 2: Claude Desktop Integration - TODO**
- [ ] **Task 2.1: HTTP Transport Configuration**
  - [ ] Document HTTP-based Claude Desktop configuration
  - [ ] Provide admin access configuration (service-key-123)
  - [ ] Provide user access configuration (user-key-456)
  - [ ] Create multi-level access configuration example
  - [ ] Test HTTP transport with actual Claude Desktop

- [ ] **Task 2.2: Authentication Setup**
  - [ ] Document pre-configured API keys usage
  - [ ] Explain JWT token generation (optional)
  - [ ] Configure headers for Claude Desktop HTTP transport
  - [ ] Test authentication with different permission levels

**Phase 3: Documentation Updates - TODO**
- [ ] **Task 3.1: Update Claude Integration Guide**
  - [ ] Add Docker-based setup section to claude-integration.md
  - [ ] Document HTTP transport configuration for Claude Desktop
  - [ ] Provide step-by-step Docker setup instructions
  - [ ] Include troubleshooting for Docker-specific issues
  - [ ] Add container lifecycle management guide

- [ ] **Task 3.2: Create Docker README**
  - [ ] Create examples/README-Docker.md with complete guide
  - [ ] Document build, run, and stop procedures
  - [ ] Explain port mapping and health checks
  - [ ] Provide configuration examples for different use cases
  - [ ] Include testing and validation steps

#### Progress
- [x] **Phase 1: Docker Container Creation** - COMPLETE ✅
  - [x] Task 1.1: Multi-stage Dockerfile in secure directory - COMPLETE ✅
  - [x] Task 1.3: Individual pyproject.toml for each example - COMPLETE ✅
    - [x] Successfully tested Docker build - image builds without errors
    - [x] Verified Docker container runs and MCP server responds correctly
- [ ] **Phase 2: Claude Desktop Integration** - TODO  
- [ ] **Phase 3: Documentation Updates** - TODO

#### Technical Decisions Made
- **Container Strategy**: Multi-stage Docker build for optimization, Dockerfile in secure directory
- **Security**: Non-root user, health checks, isolated environment
- **Authentication**: Pre-configured API keys (no expiration issues)
- **Networking**: HTTP transport to eliminate Claude Desktop path issues
- **Port**: Single port 8080 for secure example (simplified from multi-port approach)
- **Configuration**: Individual pyproject.toml per example, no dev dependencies
- **Architecture**: Removed Docker Compose complexity, simple docker build/run commands

#### Expected Benefits
- **✅ Eliminates path issues** - No absolute paths needed for Claude Desktop
- **✅ Consistent environment** - Same container everywhere
- **✅ Simple Claude config** - Just HTTP URL + API key
- **✅ Portable** - Works on any system with Docker
- **✅ Secure** - Isolated container environment  
- **✅ Reliable** - Health checks and restart policies

## 📋 TODO TASKS

### [2024-12-19] Route Discovery Feature - Remaining Phases

**Status**: TODO
**Assigned**: Assistant  
**Estimated Time**: 3 days
**Related Issue**: N/A (Core feature completion)

#### Phase 2: Schema Generation (TODO)
**Estimated Time**: 1 day

**Tasks:**
- [ ] Implement JSON schema generation from type hints
- [ ] Handle path parameters (e.g., `{id}`, `{user_id}`)
- [ ] Support query parameters and request body schemas
- [ ] Add validation for generated schemas
- [ ] Test schema generation with various parameter types

#### Phase 3: MCP Tool Conversion (TODO)
**Estimated Time**: 1 day

**Tasks:**
- [ ] Convert discovered routes to MCPTool objects
- [ ] Generate appropriate tool names from routes
- [ ] Create tool descriptions from docstrings
- [ ] Handle HTTP method mapping
- [ ] Test tool generation and execution

#### Phase 4: Configuration Integration (TODO)
**Estimated Time**: 0.5 day

**Tasks:**
- [ ] Add configuration options for route discovery
- [ ] Implement include/exclude pattern filtering
- [ ] Add auto-discovery toggle
- [ ] Update plugin integration
- [ ] Test configuration options

#### Phase 5: Documentation & Examples (TODO)
**Estimated Time**: 0.5 day

**Tasks:**
- [ ] Update README with route discovery examples
- [ ] Add configuration documentation
- [ ] Create example applications
- [ ] Update API documentation

#### Background
Phase 1 (Basic Route Discovery) was completed in 2024-12-19 with comprehensive test coverage. The remaining phases will complete the full route discovery feature set.

### [2024-01-XX] Open Source & PyPI Publishing

**Status**: TODO
**Assigned**: Assistant  
**Estimated Time**: 1-2 days
**Related Issue**: N/A (Publishing preparation)

#### Phase 2: PyPI Publishing Setup (TODO)
**Estimated Time**: 1 day

**Package Configuration Tasks:**
- [ ] Update pyproject.toml with proper metadata
- [ ] Configure package classifiers
- [ ] Add long description from README
- [ ] Set up proper versioning strategy
- [ ] Configure build system
- [ ] Test package building locally
- [ ] Validate package metadata

**CI/CD Pipeline Setup Tasks:**
- [ ] Set up GitHub Actions for automated testing
- [ ] Configure automated PyPI publishing on tag
- [ ] Add security scanning (bandit, safety)
- [ ] Set up code quality checks (coverage, linting)
- [ ] Configure multi-Python version testing
- [ ] Add documentation building and deployment

#### Background
Documentation and licensing preparation was completed. Package publishing infrastructure still needs to be set up.

### [2024-01-XX] Enhanced Route Discovery Feature

**Status**: TODO
**Assigned**: Assistant  
**Estimated Time**: 2-3 days
**Related Issue**: N/A (Major feature enhancement)

#### Background
This represents the comprehensive route discovery implementation with advanced schema generation and full MCP integration.

**Core Implementation Tasks:**
- [ ] Implement comprehensive schema generation from Python signatures
- [ ] Create advanced route-to-tool conversion with proper naming
- [ ] Build request execution engine for discovered routes
- [ ] Add route filtering and configuration options
- [ ] Create comprehensive documentation and examples

**Technical Architecture:**
- Enhanced `PyramidIntrospector` with full route discovery
- `SchemaGenerator` for JSON schema creation from type hints
- `ToolNameGenerator` for meaningful MCP tool names
- `RouteExecutor` for executing discovered routes as MCP tools

#### Phase 1: Basic Route Discovery (Day 1)
**Status**: Planned

**Tasks:**
- [ ] Enhance route information extraction beyond current implementation
- [ ] Implement comprehensive view signature parsing
- [ ] Add support for class-based views
- [ ] Create robust route filtering system
- [ ] Add comprehensive test coverage

#### Phase 2: Schema Generation (Day 2)
**Status**: Planned

**Tasks:**
- [ ] Implement type hint to JSON schema conversion
- [ ] Handle complex parameter types (Optional, Union, List, etc.)
- [ ] Support Marshmallow schema integration
- [ ] Add request/response schema generation
- [ ] Create schema validation system

#### Phase 3: Tool Generation & Execution (Day 3)
**Status**: Planned

**Tasks:**
- [ ] Build intelligent tool name generation
- [ ] Create tool description generation from docstrings
- [ ] Implement route execution with proper request handling
- [ ] Add error handling and response conversion
- [ ] Create configuration system for tool generation

### [2025-01-27] Core MCP Protocol Implementation

**Status**: TODO
**Assigned**: Assistant
**Estimated Time**: 16 hours
**Related Issue**: N/A (Core infrastructure)

#### Plan
- [ ] Implement MCP message handling (JSON-RPC over transport)
- [ ] Create WSGI-compatible MCP server application
- [ ] Implement MCP protocol methods: initialize, list_tools, call_tool
- [ ] Handle MCP protocol errors and responses
- [ ] Create transport abstraction for future extensibility
- [ ] Implement proper MCP protocol versioning

#### Technical Decisions Made
- Decision 1: Use JSON-RPC 2.0 for MCP message format
- Decision 2: Create separate WSGI app that can be mounted or run standalone

### [2025-01-27] Pyramid Integration Layer

**Status**: TODO  
**Assigned**: Assistant
**Estimated Time**: 20 hours
**Related Issue**: N/A (Core integration)

#### Plan
- [ ] Create PyramidMCP main class (equivalent to FastApiMCP)
- [ ] Implement automatic Pyramid route discovery using introspection
- [ ] Extract view configurations and metadata
- [ ] Generate MCP tool definitions from Pyramid views
- [ ] Handle Pyramid-specific decorators and configurations
- [ ] Implement view filtering and inclusion/exclusion logic
- [ ] Create mounting mechanism for embedding MCP in existing Pyramid apps
- [ ] Support standalone MCP server deployment

#### Technical Decisions Made
- Decision 1: Use Pyramid's `pyramid.interfaces.IRouteRequest` for route discovery
- Decision 2: Support both imperative and declarative view configurations
- Decision 3: Provide decorator-based MCP tool configuration

### [2025-01-27] Schema Generation and Documentation

**Status**: TODO
**Assigned**: Assistant  
**Estimated Time**: 12 hours
**Related Issue**: N/A (Enhanced schema support)

#### Plan
- [ ] Implement request schema generation from Pyramid view callables
- [ ] Implement response schema generation (challenging without native OpenAPI)
- [ ] Support for common serialization libraries (JSON, Colander, etc.)
- [ ] Extract and preserve endpoint documentation from docstrings
- [ ] Generate JSON Schema for MCP tool parameters
- [ ] Handle Pyramid-specific request/response patterns
- [ ] Support custom schema annotations

#### Technical Decisions Made
- Decision 1: Support multiple schema libraries but don't require them
- Decision 2: Use type hints and docstrings when available
- Decision 3: Provide manual schema override mechanisms

### [2025-01-27] Authentication and Security Integration

**Status**: TODO
**Assigned**: Assistant
**Estimated Time**: 10 hours  
**Related Issue**: N/A (Security enhancement)

#### Plan
- [ ] Integrate with Pyramid's security system
- [ ] Support ACL-based authorization for MCP tools
- [ ] Handle authentication contexts in MCP calls
- [ ] Implement security policy integration
- [ ] Support custom authentication callbacks
- [ ] Handle authenticated requests in MCP context
- [ ] Provide security configuration options

### [2024-12-28] Implement Pyramid Permission Integration with MCP Server Authorization

**Status**: TODO
**Assigned**: Assistant  
**Estimated Time**: 8-12 hours
**Related Issue**: N/A (Complex feature implementation)

#### Plan

**Understanding the Integration Challenge:**
This task involves creating a sophisticated integration between Pyramid's mature ACL-based permission system and MCP's OAuth 2.1-based authorization system. The goal is to allow the MCP server to respect and enforce Pyramid view permissions when auto-discovering and calling routes.

**Key Research Findings:**
- **Pyramid Security**: Uses ACL (Access Control Lists), security policies, principals, and permission decorators on views
- **MCP Authorization**: Recently added OAuth 2.1 support with JWT tokens, scopes, and bearer auth
- **Integration Challenge**: Need to bridge route-level permissions with MCP tool authorization
- **Test-First Approach**: Start with comprehensive tests to define the expected behavior

**Phase 1: Analysis and Design (2-3 hours)**
- [x] Research Pyramid permission system (ACL, security policies, view permissions) ✅
- [x] Research MCP authorization specification (OAuth 2.1, JWT, scopes) ✅
- [ ] **Task 1.1**: Analyze current route discovery system and identify permission integration points
  - [ ] Examine `PyramidIntrospector._get_view_introspectables()` method
  - [ ] Identify where view permissions are stored in introspectables
  - [ ] Map Pyramid permission model to MCP scopes/authorization model
- [ ] **Task 1.2**: Design permission integration architecture
  - [ ] Design how Pyramid permissions translate to MCP tool permissions
  - [ ] Design authentication/authorization flow for MCP tool calls
  - [ ] Design security policy integration points
  - [ ] Create permission mapping strategy (permission names → MCP scopes)
- [ ] **Task 1.3**: Create comprehensive test plan
  - [ ] Design test scenarios for different permission levels
  - [ ] Plan authentication/authorization test cases
  - [ ] Design integration test scenarios
  - [ ] Plan security edge cases and failure modes

**Phase 2: Test Infrastructure Setup (1-2 hours)** - TDD APPROACH
- [ ] **Task 2.1**: Write authentication tests FIRST (True TDD)
  - [ ] Write failing tests for JWT authentication scenarios
  - [ ] THEN implement fixtures to make tests pass
  - [ ] Use real Pyramid security policies (NO MOCKING)
- [ ] **Task 2.2**: Create permission-aware test data
  - [ ] Create test routes with various permission levels
  - [ ] Create test resources with ACLs
  - [ ] Create test principal and group combinations
- [ ] **Task 2.3**: Design test file structure for permission tests
  - [ ] Create `test_unit_permissions.py` for permission logic tests
  - [ ] Create `test_integration_auth.py` for full auth flow tests
  - [ ] Extend existing integration tests with permission scenarios

**Phase 3: Core Permission Integration Implementation (3-4 hours)**
- [ ] **Task 3.1**: Extend route discovery to capture permissions
  - [ ] Modify `PyramidIntrospector` to extract view permissions
  - [ ] Add permission metadata to discovered route information
  - [ ] Handle routes with no permissions (public access)
  - [ ] Handle permission inheritance and defaults
- [ ] **Task 3.2**: Implement permission validation in tool execution
  - [ ] Create permission checking middleware for MCP tool calls
  - [ ] Integrate with Pyramid's security policy for authorization
  - [ ] Implement permission-based tool filtering
  - [ ] Add proper error handling for insufficient permissions
- [ ] **Task 3.3**: Add JWT/Bearer token support to MCP server
  - [ ] Implement Bearer token authentication in HTTP endpoints
  - [ ] Add JWT token validation using Pyramid's security system
  - [ ] Create token-to-principal mapping
  - [ ] Handle token expiration and refresh scenarios

**Phase 4: Security Policy Integration (2-3 hours)**
- [ ] **Task 4.1**: Create MCP-aware security policy
  - [ ] Extend existing security policy to handle MCP requests
  - [ ] Implement `identity()` method for JWT token parsing
  - [ ] Implement `permits()` method for MCP tool authorization
  - [ ] Add support for MCP-specific principals and scopes
- [ ] **Task 4.2**: Implement permission mapping
  - [ ] Create configurable permission-to-scope mapping
  - [ ] Add support for granular permissions (read, write, admin)
  - [ ] Implement default permission handling
  - [ ] Add permission inheritance for resource hierarchies
- [ ] **Task 4.3**: Add authorization metadata to tool descriptions
  - [ ] Include required permissions in MCP tool schemas
  - [ ] Add permission documentation to tool descriptions
  - [ ] Implement dynamic tool availability based on user permissions

**Phase 5: Integration Testing and Security Validation (1-2 hours)**
- [ ] **Task 5.1**: Comprehensive integration testing
  - [ ] Test full authentication flow (OAuth → JWT → Pyramid security)
  - [ ] Test permission enforcement across different routes
  - [ ] Test edge cases (expired tokens, invalid permissions, etc.)
  - [ ] Test performance impact of permission checking
- [ ] **Task 5.2**: Security validation and testing
  - [ ] Test authorization bypass attempts
  - [ ] Test token manipulation and validation
  - [ ] Test permission escalation scenarios
  - [ ] Verify secure defaults (deny by default)
- [ ] **Task 5.3**: Documentation and examples
  - [ ] Update configuration documentation
  - [ ] Create security configuration examples
  - [ ] Document permission mapping strategies
  - [ ] Create troubleshooting guide for permission issues

#### Technical Design Decisions

**Permission Mapping Strategy:**
- **Option A**: Direct mapping (Pyramid permission = MCP scope)
- **Option B**: Configurable mapping (permission → multiple scopes)
- **Option C**: Hierarchical mapping (permission levels: read < write < admin)
- **Decision**: Use Option C with configurable overrides

**Authentication Integration:**
- **JWT Validation**: Use Pyramid's security policy for consistent auth
- **Token Storage**: Stateless JWT validation (no server-side sessions)
- **Permission Lookup**: Real-time permission checking via security policy

**Security Approach:**
- **Deny by Default**: Routes without explicit permissions deny MCP access
- **Scope Validation**: Each tool call validates required permissions
- **Principal Extraction**: Extract principals from JWT claims for Pyramid ACL

#### Expected Outcomes

**Security Benefits:**
- ✅ MCP tools respect Pyramid view permissions
- ✅ Consistent authorization across HTTP and MCP interfaces
- ✅ JWT-based authentication for MCP endpoints
- ✅ Fine-grained permission control per tool/route

**Developer Experience:**
- ✅ Automatic permission discovery and enforcement
- ✅ Clear security configuration options
- ✅ Comprehensive testing and validation tools
- ✅ Detailed documentation and examples

**Integration Quality:**
- ✅ Seamless integration with existing Pyramid security
- ✅ Configurable permission mapping
- ✅ Performance-conscious implementation
- ✅ Secure by default configuration

## 🔄 POTENTIAL FUTURE TASKS

### Enhanced Permission Integration
- **Priority**: Medium
- **Estimated Time**: 4-6 hours
- **Description**: Add more sophisticated permission features

**Potential Features:**
- Support for ACL-based permissions beyond simple string matching
- Permission inheritance from Pyramid view configurations
- Context-aware permissions (permissions that depend on resource context)
- Permission caching for improved performance
- Role-based permission mapping

### Authentication Method Expansion
- **Priority**: Low-Medium
- **Estimated Time**: 3-4 hours  
- **Description**: Support additional authentication methods

**Potential Features:**
- API key authentication
- OAuth 2.0 integration beyond JWT
- Basic authentication support
- Custom authentication policy integration
- Session-based authentication

### Documentation and Examples Enhancement
- **Priority**: Medium
- **Estimated Time**: 2-3 hours
- **Description**: Comprehensive documentation for permission system

**Potential Content:**
- Permission system architecture documentation
- Step-by-step authentication setup guide
- Security best practices guide
- More complex permission examples
- Authentication troubleshooting guide

### Performance Optimization
- **Priority**: Low
- **Estimated Time**: 3-5 hours
- **Description**: Optimize permission checking performance

**Potential Optimizations:**
- Permission result caching
- Batch permission checking
- Async permission validation
- Connection pooling for auth services
- Benchmark permission system performance

## 📊 Current Status

**All major infrastructure tasks completed!** ✅

- ✅ **Testing**: Modern pytest-based test suite with 94+ tests, 75%+ coverage
- ✅ **Plugin Architecture**: Full Pyramid plugin with includeme function
- ✅ **Tool Registration**: Easy @tool decorator for automatic registration
- ✅ **Settings Integration**: Comprehensive mcp.* settings support
- ✅ **Examples**: Working example application demonstrating usage
- ✅ **Backward Compatibility**: Existing API still works unchanged
- ✅ **Security**: JWT authentication and context factory integration
- ✅ **Docker**: Development environment with Docker-in-Docker support

The project now follows Pyramid best practices and provides an excellent developer experience for integrating MCP with Pyramid applications.

## Next Steps

The core infrastructure is solid. Future development can focus on:

1. **Feature Development**: Add new MCP capabilities or Pyramid integrations
2. **Documentation**: Create comprehensive user documentation
3. **Performance**: Optimize for production use cases
4. **Additional Examples**: More complex usage scenarios

The project is ready for real-world usage and follows all Pyramid conventions!

---

## Template for Future Tasks

### [YYYY-MM-DD] Task Description

**Status**: TODO | IN PROGRESS | DONE | BLOCKED
**Assigned**: Name
**Estimated Time**: X hours
**Related Issue**: #XXX

#### Plan
- [ ] Task 1: Description
- [ ] Task 2: Description
- [ ] Task 3: Description

#### Progress
- [ ] Current status of tasks

#### Decisions Made
- Decision: Reasoning

#### Blockers/Issues
- Issue: Description and resolution plan 
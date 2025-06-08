# Project Backlog

This file contains all planned TODO tasks for the pyramid-mcp project that are not currently in active development.

## 📋 FUTURE TASKS (Prioritized)

### [HIGH PRIORITY] Route Discovery Feature - Remaining Phases

**Status**: TODO (Planned)
**Assigned**: TBD  
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

### [HIGH PRIORITY] Open Source & PyPI Publishing

**Status**: TODO (Planned)
**Assigned**: TBD  
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

### [MEDIUM PRIORITY] Enhanced Route Discovery Feature

**Status**: TODO (Planned)
**Assigned**: TBD  
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

### [MEDIUM PRIORITY] Core MCP Protocol Implementation

**Status**: TODO (Planned)
**Assigned**: TBD
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

### [MEDIUM PRIORITY] Pyramid Integration Layer

**Status**: TODO (Planned)  
**Assigned**: TBD
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

### [MEDIUM PRIORITY] Schema Generation and Documentation

**Status**: TODO (Planned)
**Assigned**: TBD  
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

### [MEDIUM PRIORITY] Authentication and Security Integration

**Status**: TODO (Planned)
**Assigned**: TBD
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

### [LOW PRIORITY] Advanced Pyramid Permission Integration

**Status**: TODO (Planned)
**Assigned**: TBD  
**Estimated Time**: 8-12 hours
**Related Issue**: N/A (Advanced security feature)

#### Plan

**Understanding the Integration Challenge:**
This task involves creating a sophisticated integration between Pyramid's mature ACL-based permission system and MCP's OAuth 2.1-based authorization system. The goal is to allow the MCP server to respect and enforce Pyramid view permissions when auto-discovering and calling routes.

**Technical Design Decisions:**
- **Permission Mapping Strategy**: Hierarchical mapping (permission levels: read < write < admin) with configurable overrides
- **Authentication Integration**: Use Pyramid's security policy for consistent auth, stateless JWT validation
- **Security Approach**: Deny by default, scope validation for each tool call

**Phase Implementation:**
- [ ] Analyze current route discovery system and identify permission integration points
- [ ] Design permission integration architecture
- [ ] Write comprehensive tests using TDD approach
- [ ] Implement permission validation in tool execution
- [ ] Add JWT/Bearer token support to MCP server
- [ ] Create MCP-aware security policy
- [ ] Implement permission mapping and authorization metadata
- [ ] Comprehensive integration testing and security validation

## 🔄 POTENTIAL FUTURE TASKS

### Enhanced Permission Integration
- **Priority**: Low
- **Estimated Time**: 4-6 hours
- **Description**: Add more sophisticated permission features (ACL-based permissions, permission inheritance, context-aware permissions, permission caching, role-based permission mapping)

### Authentication Method Expansion
- **Priority**: Low-Medium
- **Estimated Time**: 3-4 hours  
- **Description**: Support additional authentication methods (API key auth, OAuth 2.0 integration, basic auth, custom authentication policies, session-based auth)

### Documentation and Examples Enhancement
- **Priority**: Medium
- **Estimated Time**: 2-3 hours
- **Description**: Comprehensive documentation for permission system (architecture docs, setup guides, security best practices, examples, troubleshooting)

### Performance Optimization
- **Priority**: Low
- **Estimated Time**: 3-5 hours
- **Description**: Optimize permission checking performance (result caching, batch checking, async validation, connection pooling, benchmarking)

---

## 📋 Backlog Management

**Priority Levels:**
- **HIGH**: Core features needed for basic functionality
- **MEDIUM**: Important features for full functionality  
- **LOW**: Nice-to-have features and optimizations

**Task Selection Criteria:**
1. Move tasks to `general.md` when ready to start active development
2. Prioritize based on user needs and project goals
3. Consider dependencies between tasks
4. Balance feature development with maintenance

**Estimated Total Backlog**: ~80-100 hours of development work

**Next Recommended Tasks:**
1. Route Discovery Feature completion (HIGH priority)
2. Open Source & PyPI Publishing (HIGH priority)
3. Enhanced Route Discovery implementation (MEDIUM priority) 
# Route Discovery Feature Plan

## Overview

**Feature**: Automatic Pyramid Route Discovery and MCP Tool Generation
**Goal**: Automatically discover Pyramid routes and convert them into MCP tools with proper schemas
**Priority**: HIGH (Core feature)
**Status**: PLANNING
**Estimated Time**: 2-3 days

## Background

The route discovery feature is the **core value proposition** of pyramid-mcp. Instead of manually registering each function as an MCP tool, developers should be able to:

1. Configure pyramid-mcp with route patterns
2. Have the system automatically discover matching Pyramid routes  
3. Generate MCP tools with proper schemas from view signatures
4. Handle authentication, validation, and error responses automatically

This feature will make pyramid-mcp significantly more valuable than manual tool registration.

## Current State

Currently in `pyramid_mcp/introspection.py`:
```python
def discover_tools_from_pyramid(self, introspector: Any, config: Any) -> List[MCPTool]:
    # TODO: Implement actual route discovery logic
    # - Get routes from introspector
    # - Extract view callables and metadata  
    # - Generate schemas from view signatures
    # - Create MCPTool instances
    tools: List[MCPTool] = []
    return tools
```

## Requirements

### Functional Requirements

#### Route Discovery
- [ ] Discover all routes from Pyramid's introspector
- [ ] Filter routes based on include/exclude patterns
- [ ] Extract route information (path, methods, view callable)
- [ ] Handle route parameters and path variables
- [ ] Support both function-based and class-based views

#### Schema Generation  
- [ ] Generate JSON schemas from view function signatures
- [ ] Handle optional parameters with defaults
- [ ] Support Marshmallow schema decorators on views
- [ ] Handle request body vs query parameters
- [ ] Support path parameters from route patterns

#### MCP Tool Creation
- [ ] Create MCPTool instances for each discovered route
- [ ] Generate descriptive tool names from routes
- [ ] Create helpful descriptions from docstrings
- [ ] Handle HTTP method-specific tools
- [ ] Support route-specific configuration

#### Request Handling
- [ ] Convert MCP tool calls to HTTP requests
- [ ] Handle authentication headers
- [ ] Support different content types (JSON, form data)
- [ ] Pass through path parameters correctly
- [ ] Handle query string parameters
- [ ] Proper error handling and response conversion

### Non-Functional Requirements
- [ ] Performance: Fast discovery on startup
- [ ] Memory: Efficient storage of discovered tools
- [ ] Security: Respect route permissions
- [ ] Flexibility: Configurable discovery patterns
- [ ] Maintainability: Clean, testable code

## Technical Design

### 1. Route Discovery Architecture

```python
class PyramidIntrospector:
    """Enhanced route discovery with full implementation."""
    
    def discover_routes(self) -> List[RouteInfo]:
        """Discover and parse all Pyramid routes."""
        
    def filter_routes(self, routes: List[RouteInfo]) -> List[RouteInfo]:
        """Filter routes based on include/exclude patterns."""
        
    def extract_route_metadata(self, route) -> RouteInfo:
        """Extract comprehensive route information."""
        
    def discover_tools_from_pyramid(self, introspector: Any, config: Any) -> List[MCPTool]:
        """Main discovery method - now fully implemented."""
```

### 2. Data Structures

```python
@dataclass
class RouteInfo:
    """Complete route information for tool generation."""
    name: str
    pattern: str
    path: str
    methods: List[str]
    view_callable: Callable
    predicates: Dict[str, Any]
    factory: Optional[Any]
    traverse: Optional[str]
    # Path parameters extracted from pattern
    path_params: List[str]
    # View metadata
    has_request_param: bool
    return_type: Optional[Type]
    docstring: Optional[str]

@dataclass  
class ViewSignature:
    """Parsed view function signature."""
    parameters: Dict[str, ParameterInfo]
    return_type: Optional[Type]
    has_request: bool
    docstring: Optional[str]

@dataclass
class ParameterInfo:
    """Individual parameter information."""
    name: str
    type_hint: Optional[Type]
    default: Any
    required: bool
    source: str  # 'path', 'query', 'body', 'header'
```

### 3. Schema Generation Strategy

```python
class SchemaGenerator:
    """Generate JSON schemas from Python signatures."""
    
    def generate_tool_schema(self, route_info: RouteInfo) -> Dict[str, Any]:
        """Generate complete MCP tool input schema."""
        
    def parse_view_signature(self, view_callable: Callable) -> ViewSignature:
        """Parse function signature with type hints."""
        
    def type_to_json_schema(self, python_type: Type) -> Dict[str, Any]:
        """Convert Python types to JSON schema."""
        
    def extract_marshmallow_schema(self, view_callable: Callable) -> Optional[Schema]:
        """Check if view has Marshmallow schema decorator."""
```

### 4. Tool Name Generation

```python
class ToolNameGenerator:
    """Generate meaningful MCP tool names from routes."""
    
    def generate_tool_name(self, route_info: RouteInfo) -> str:
        """Create descriptive tool name from route."""
        # Examples:
        # GET /users -> "list_users"  
        # GET /users/{id} -> "get_user"
        # POST /users -> "create_user"
        # PUT /users/{id} -> "update_user"
        # DELETE /users/{id} -> "delete_user"
        
    def generate_description(self, route_info: RouteInfo) -> str:
        """Generate tool description from route and docstring."""
```

### 5. Request Execution Engine

```python
class RouteExecutor:
    """Execute discovered routes as MCP tools."""
    
    def execute_route_tool(
        self, 
        route_info: RouteInfo, 
        arguments: Dict[str, Any],
        context: MCPContext
    ) -> Any:
        """Execute a discovered route with MCP arguments."""
        
    def prepare_request(self, route_info: RouteInfo, arguments: Dict[str, Any]) -> Request:
        """Convert MCP arguments to Pyramid request."""
        
    def handle_response(self, response: Any) -> Dict[str, Any]:
        """Convert Pyramid response to MCP format."""
```

## Implementation Plan

### Phase 1: Basic Route Discovery (Day 1)
**Estimated Time**: 6-8 hours

#### Task 1: Route Information Extraction
- [ ] Implement `discover_routes()` method
- [ ] Extract basic route information from Pyramid introspector
- [ ] Create `RouteInfo` dataclass
- [ ] Handle route patterns and path parameters
- [ ] Write unit tests for route discovery

#### Task 2: Route Filtering  
- [ ] Implement include/exclude pattern matching
- [ ] Support glob patterns (`api/*`, `users/*`)
- [ ] Support exact matches and regex patterns
- [ ] Test with various route configurations

### Phase 2: View Analysis (Day 1-2)
**Estimated Time**: 4-6 hours

#### Task 3: Signature Parsing
- [ ] Implement `parse_view_signature()` method
- [ ] Extract function parameters and type hints
- [ ] Identify request parameter vs business parameters
- [ ] Handle class-based views
- [ ] Support async views

#### Task 4: Marshmallow Integration
- [ ] Detect existing Marshmallow schemas on views
- [ ] Extract schema information for tool generation
- [ ] Handle validation and error responses
- [ ] Test with existing Pyramid apps using schemas

### Phase 3: Schema Generation (Day 2)
**Estimated Time**: 6-8 hours

#### Task 5: JSON Schema Generation
- [ ] Implement `type_to_json_schema()` conversion
- [ ] Support basic types: str, int, float, bool
- [ ] Support complex types: List, Dict, Optional
- [ ] Handle Union types and custom classes
- [ ] Generate proper validation rules

#### Task 6: Tool Schema Assembly
- [ ] Combine path parameters, query parameters, and body
- [ ] Generate complete MCP tool input schemas
- [ ] Handle different HTTP methods appropriately
- [ ] Create meaningful parameter descriptions

### Phase 4: Tool Generation (Day 2-3)
**Estimated Time**: 4-6 hours

#### Task 7: MCP Tool Creation
- [ ] Implement complete `discover_tools_from_pyramid()` method
- [ ] Generate meaningful tool names and descriptions
- [ ] Create executable tool handlers
- [ ] Handle authentication and permissions
- [ ] Test with real Pyramid applications

#### Task 8: Request Execution
- [ ] Implement route execution engine
- [ ] Convert MCP arguments to Pyramid requests
- [ ] Handle path parameter substitution
- [ ] Support different content types
- [ ] Proper error handling and response conversion

### Phase 5: Testing & Integration (Day 3)
**Estimated Time**: 4-6 hours

#### Task 9: Comprehensive Testing
- [ ] Test with simple CRUD routes
- [ ] Test with complex nested routes
- [ ] Test authentication integration
- [ ] Test error handling scenarios
- [ ] Performance testing with many routes

#### Task 10: Documentation & Examples
- [ ] Update README with route discovery examples
- [ ] Create comprehensive example application
- [ ] Document configuration options
- [ ] Add troubleshooting guide

## Configuration Design

### Settings-Based Configuration
```python
settings = {
    # Route Discovery Settings
    'mcp.enable_route_discovery': 'true',
    'mcp.include_patterns': 'api/*, users/*, admin/*',
    'mcp.exclude_patterns': 'internal/*, debug/*, health',
    'mcp.discovery_methods': 'GET,POST,PUT,DELETE',
    
    # Tool Generation Settings  
    'mcp.tool_name_prefix': '',  # Optional prefix for all tools
    'mcp.generate_descriptions': 'true',
    'mcp.include_docstrings': 'true',
    
    # Request Handling Settings
    'mcp.default_auth_header': 'Authorization',
    'mcp.preserve_request_context': 'true',
    'mcp.timeout_seconds': '30',
}
```

### Programmatic Configuration
```python
# Fine-grained control for advanced users
mcp_config = MCPConfiguration(
    route_discovery=RouteDiscoveryConfig(
        enabled=True,
        include_patterns=['api/*', 'users/*'],
        exclude_patterns=['internal/*'],
        methods=['GET', 'POST', 'PUT', 'DELETE'],
        tool_name_generator=CustomToolNameGenerator(),
        schema_generator=CustomSchemaGenerator(),
    )
)
```

## Usage Examples

### Basic Auto-Discovery
```python
# Minimal setup - discovers all routes
config = Configurator(settings={
    'mcp.server_name': 'my-api',
    'mcp.enable_route_discovery': 'true',
})
config.include('pyramid_mcp')

# Your existing routes automatically become MCP tools
config.add_route('users', '/users')
config.add_route('user', '/users/{id}')
config.add_route('user_posts', '/users/{id}/posts')
```

### Selective Discovery
```python  
# Only expose API routes as MCP tools
config = Configurator(settings={
    'mcp.server_name': 'my-api', 
    'mcp.include_patterns': 'api/*',
    'mcp.exclude_patterns': 'api/internal/*',
})
config.include('pyramid_mcp')

config.add_route('api_users', '/api/users')      # ✅ Discovered
config.add_route('api_posts', '/api/posts')      # ✅ Discovered  
config.add_route('admin_panel', '/admin')        # ❌ Not discovered
config.add_route('api_internal', '/api/internal/stats')  # ❌ Excluded
```

### Enhanced Views with Type Hints
```python
# Views with type hints generate better schemas
@view_config(route_name='create_user', request_method='POST', renderer='json')
def create_user(request) -> Dict[str, Any]:
    """Create a new user account.
    
    Creates a new user with the provided information and returns
    the created user data with assigned ID.
    """
    # This docstring becomes the MCP tool description
    # Type hints generate proper JSON schema
    name: str = request.json_body['name']
    email: str = request.json_body['email'] 
    age: int = request.json_body.get('age', 18)
    
    # Implementation...
    return {"user": {"id": 123, "name": name, "email": email, "age": age}}

# Generates MCP tool:
# Name: "create_user"
# Description: "Create a new user account. Creates a new user..."
# Schema: {"properties": {"name": {"type": "string"}, "email": {"type": "string"}, "age": {"type": "integer"}}}
```

## Benefits of This Implementation

### For Developers
- **Zero Configuration**: Works out of the box with existing Pyramid apps
- **Type Safety**: Leverages Python type hints for schema generation  
- **Flexible**: Granular control over what gets exposed
- **Familiar**: Uses existing Pyramid patterns and decorators

### For MCP Clients
- **Rich Schemas**: Automatic validation and documentation
- **Consistent Interface**: Standardized tool naming and responses
- **Error Handling**: Proper MCP error responses
- **Performance**: Direct route execution without HTTP overhead

### For the Ecosystem
- **Interoperability**: Standard MCP protocol compliance
- **Discoverability**: Automatic tool catalog generation
- **Documentation**: Self-documenting APIs through schemas
- **Testing**: Easy to test MCP integrations

## Risk Assessment

### High Risk
- **Performance Impact**: Route discovery on startup could be slow
- **Memory Usage**: Storing tool metadata for many routes
- **Breaking Changes**: Changes to Pyramid's introspection API

### Medium Risk
- **Complex Routes**: Nested routes, traversal, complex predicates
- **Authentication**: Handling various auth patterns correctly
- **Type Complexity**: Advanced type hints and generics

### Low Risk  
- **Basic CRUD**: Simple routes with standard patterns
- **Documentation**: Clear examples and usage patterns
- **Testing**: Comprehensive test coverage

## Success Metrics

### Functional Metrics
- [ ] Successfully discovers 90%+ of standard Pyramid routes
- [ ] Generates valid JSON schemas for 95%+ of typed views
- [ ] Executes route tools with <100ms overhead
- [ ] Handles authentication correctly

### Developer Experience Metrics  
- [ ] Zero-config setup works for basic apps
- [ ] Configuration is intuitive and well-documented
- [ ] Error messages are clear and actionable
- [ ] Performance is acceptable (<5s startup for 100+ routes)

## Next Steps

1. **Immediate**: Create RouteInfo and related dataclasses
2. **Day 1**: Implement basic route discovery and filtering  
3. **Day 2**: Add schema generation and tool creation
4. **Day 3**: Complete request execution and testing
5. **Future**: Advanced features like caching, async support

---

**This feature will transform pyramid-mcp from a simple tool registration library into a powerful automatic API-to-MCP bridge, making it the most valuable MCP integration for Pyramid developers.** 
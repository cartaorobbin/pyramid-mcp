# Route Discovery Feature Implementation

## Overview
Implement automatic route discovery for Pyramid applications, converting routes to MCP tools with proper schema generation and filtering capabilities.

## Implementation Plan

### Phase 1: Core Route Discovery ✅ COMPLETED
**Status**: DONE  
**Estimated Time**: 1 day  
**Actual Time**: 1 day  
**Completed**: 2024-12-19

#### Tasks Completed:
- [x] Research Pyramid introspection system
- [x] Implement `PyramidIntrospector.discover_routes()` method
- [x] Handle route metadata extraction (name, pattern, methods)
- [x] Extract view information and associate with routes
- [x] Create comprehensive test suite (13 tests, all passing)
- [x] Fix introspection data access (use `get_category()` instead of `categorized()`)
- [x] Implement pattern matching for include/exclude functionality

#### Key Discoveries:
- **Pyramid Introspection System**: Uses `registry.introspector.get_category('routes')` to access route data
- **Data Structure**: Returns list of dictionaries with `introspectable` key containing actual route objects
- **Configuration Commitment**: Must call `config.commit()` before introspection works
- **View Association**: Views are in separate 'views' category, linked by `route_name`

#### Implementation Details:
- **Route Discovery**: Extracts name, pattern, methods, predicates from route introspectables
- **View Integration**: Associates views with routes using route_name matching
- **Pattern Matching**: Supports wildcards (`api/*`) and exact matches (`api`)
- **Comprehensive Testing**: 13 tests covering all functionality

### Phase 2: Schema Generation ⏳ IN PROGRESS
**Status**: TODO  
**Estimated Time**: 1 day

#### Tasks:
- [ ] Implement JSON schema generation from type hints
- [ ] Handle path parameters (e.g., `{id}`, `{user_id}`)
- [ ] Support query parameters and request body schemas
- [ ] Add validation for generated schemas
- [ ] Test schema generation with various parameter types

### Phase 3: MCP Tool Conversion
**Status**: TODO  
**Estimated Time**: 1 day

#### Tasks:
- [ ] Convert discovered routes to MCPTool objects
- [ ] Generate appropriate tool names from routes
- [ ] Create tool descriptions from docstrings
- [ ] Handle HTTP method mapping
- [ ] Test tool generation and execution

### Phase 4: Configuration Integration
**Status**: TODO  
**Estimated Time**: 0.5 day

#### Tasks:
- [ ] Add configuration options for route discovery
- [ ] Implement include/exclude pattern filtering
- [ ] Add auto-discovery toggle
- [ ] Update plugin integration
- [ ] Test configuration options

### Phase 5: Documentation & Examples
**Status**: TODO  
**Estimated Time**: 0.5 day

#### Tasks:
- [ ] Update README with route discovery examples
- [ ] Add configuration documentation
- [ ] Create example applications
- [ ] Update API documentation

## Technical Implementation

### Core Classes

#### PyramidIntrospector ✅ IMPLEMENTED
```python
class PyramidIntrospector:
    def __init__(self, configurator: Optional[Any] = None)
    def discover_routes(self) -> List[Dict[str, Any]]
    def discover_tools(self, config: Any) -> List[MCPTool]
    def _pattern_matches(self, pattern: str, route_pattern: str, route_name: str) -> bool
    def _convert_route_to_tools(self, route_info: Dict[str, Any], config: Any) -> List[MCPTool]
```

**Key Methods Implemented:**
- `discover_routes()`: Main route discovery using Pyramid introspection
- `_pattern_matches()`: Pattern matching for include/exclude filtering
- Proper handling of route and view introspectables

### Route Information Structure ✅ IMPLEMENTED
```python
{
    'name': 'api_users',
    'pattern': '/api/users',
    'methods': ['GET', 'POST'],
    'predicates': {...},
    'views': [
        {
            'callable': <function>,
            'request_method': 'GET',
            'renderer': 'json'
        }
    ]
}
```

### Configuration Options (Planned)
```python
# In Pyramid settings
mcp.route_discovery.enabled = true
mcp.route_discovery.include_patterns = api/*, users/*
mcp.route_discovery.exclude_patterns = admin/*, internal/*
mcp.route_discovery.auto_schema = true
```

## Testing Status ✅ COMPREHENSIVE

### Test Coverage: 13/13 tests passing
- **Basic Discovery**: Route discovery from Pyramid configuration
- **Route Information**: Proper structure and metadata extraction  
- **Tool Generation**: Converting routes to MCP tools
- **Schema Generation**: JSON schema from type hints and parameters
- **Pattern Matching**: Include/exclude functionality with wildcards
- **Integration**: Complex route configurations with multiple views
- **Error Handling**: Graceful handling of edge cases

### Test Results:
```
tests/test_route_discovery.py::test_discover_routes_basic PASSED
tests/test_route_discovery.py::test_route_info_structure PASSED  
tests/test_route_discovery.py::test_discover_tools_from_pyramid PASSED
tests/test_route_discovery.py::test_tool_name_generation PASSED
tests/test_route_discovery.py::test_input_schema_generation PASSED
tests/test_route_discovery.py::test_input_schema_with_annotations PASSED
tests/test_route_discovery.py::test_pattern_matching PASSED
tests/test_route_discovery.py::test_route_exclusion PASSED
tests/test_route_discovery.py::test_include_patterns PASSED
tests/test_route_discovery.py::test_exclude_patterns PASSED
tests/test_route_discovery.py::test_tool_handler_creation PASSED
tests/test_route_discovery.py::test_integration_with_complex_routes PASSED
tests/test_route_discovery.py::test_description_generation PASSED
```

**Overall Project Test Status**: 69/69 tests passing, 79% coverage

## Example Usage (Planned)

### Basic Route Discovery
```python
from pyramid.config import Configurator
from pyramid_mcp import includeme

config = Configurator()
config.add_route('api_users', '/api/users', request_method='GET')
config.add_route('api_user', '/api/users/{id}', request_method=['GET', 'PUT'])

# Enable MCP with route discovery
config.include(includeme)

# Routes automatically become MCP tools:
# - list_api_users: GET /api/users
# - get_api_user: GET /api/users/{id} 
# - update_api_user: PUT /api/users/{id}
```

### With Filtering
```python
# Only include API routes
config.registry.settings['mcp.route_discovery.include_patterns'] = 'api/*'

# Exclude admin routes  
config.registry.settings['mcp.route_discovery.exclude_patterns'] = 'admin/*'
```

## Next Steps

1. **Continue with Phase 2**: Implement comprehensive schema generation
2. **Focus on Type Hints**: Extract parameter types from function signatures
3. **Path Parameter Handling**: Convert `{id}` to proper JSON schema properties
4. **Request Body Schemas**: Handle POST/PUT request body validation

## Research Notes

### Pyramid Introspection System
- **Access Pattern**: `config.registry.introspector.get_category('routes')`
- **Data Format**: List of dicts with 'introspectable' key
- **Categories**: 'routes', 'views', 'templates', 'static_views'
- **Commitment Required**: Must call `config.commit()` before introspection

### Route Object Properties
- `name`: Route name (string)
- `pattern`: URL pattern with placeholders
- `factory`: Route factory (usually None)
- `predicates`: Dict of route predicates (request_method, etc.)

### View Object Properties  
- `callable`: The view function/class
- `route_name`: Associated route name
- `request_method`: HTTP method(s)
- `renderer`: Response renderer ('json', template, etc.)

This comprehensive implementation provides a solid foundation for automatic route discovery in Pyramid applications, with robust testing and proper integration with the MCP protocol. 
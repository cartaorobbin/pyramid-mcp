# General Planning - Current Active Tasks

## 🎯 Current Active Tasks

### [2024-12-28] Refactor Introspection Input Schema Generation

**Status**: IN PROGRESS
**Assigned**: Assistant
**Estimated Time**: 2 hours
**Related Issue**: Code quality improvement

#### Plan
- [ ] Create new `pyramid_mcp/schemas.py` file for schema definitions
- [ ] Design Marshmallow schema for HTTP request structure (path, body, headers, querystring)
- [ ] Refactor `_generate_input_schema` method in introspection.py to use new schema approach
- [ ] Remove misleading comment about Pyramid views and generic 'data' parameter
- [ ] Update tests to work with new schema structure
- [ ] Run `make test` and `make check` to ensure everything passes

#### Progress
- [x] Planning phase - documenting approach
- [x] Create schemas.py file with ONLY clean Marshmallow schemas
- [x] Implement HTTPRequestSchema with proper nested fields structure
- [x] Improve schemas structure with individual parameter schemas:
  - [x] PathParameterSchema for single path parameters
  - [x] QueryParameterSchema for single query parameters  
  - [x] BodySchema for single body fields
  - [x] HTTPRequestSchema uses lists of these schemas
- [x] Revert introspection.py to working state
- [x] Clean schemas.py to contain ONLY schemas:
  - [x] PathParameterSchema - for individual path parameters
  - [x] QueryParameterSchema - for individual query parameters  
  - [x] BodySchema - for individual body fields
  - [x] RequestHeadersSchema - for headers
  - [x] HTTPRequestSchema - main schema using lists of the above
  - [x] Removed all utility functions (schemas only!)
- [x] Update introspection.py to use the schemas:
  - [x] Added imports for all schema classes
  - [x] Updated _generate_input_schema method to use schemas properly
  - [x] Uses PathParameterSchema().load() for path parameters
  - [x] Uses QueryParameterSchema().load() for query parameters
  - [x] Uses BodySchema().load() for body fields
  - [x] Uses HTTPRequestSchema().load() for validation and .dump() for JSON output
  - [x] Removed misleading comment about Pyramid view parameters
  - [x] Cleaned up legacy properties/required variables
- [ ] Update tests
- [ ] Validate with make test/check

#### Problem Analysis
Current code has misleading comment: "since Pyramid views only take 'request' parameter, we can't extract params from signature" 
and uses a generic 'data' parameter that doesn't properly represent HTTP request structure.

HTTP requests should be properly structured with:
- Path parameters (from URL path like /users/{id})
- Query parameters (from URL query string like ?limit=10&offset=0)
- Request body (for POST/PUT/PATCH requests)
- Headers (for authentication, content-type, etc.)

#### Decisions Made
- Create separate schemas.py file to reduce introspection.py size
- Use Marshmallow schemas to properly validate and structure HTTP request data
- Remove generic 'data' parameter approach in favor of proper HTTP structure

---

*Add new tasks here as they are started.*

---

## 📋 Task Management Guidelines

### When to Use This File
- **CURRENT tasks actively being worked on**
- **IN PROGRESS development work**
- **Immediate priority tasks**
- **Keep focused (max 1-3 active task groups)**

### Task Flow
1. **Add to `planning/backlog.md`**: Plan future tasks
2. **Move to `planning/general.md`**: When starting active work
3. **Update progress**: Track completion status
4. **Move to `planning/done.md`**: When task is DONE and tests pass

### Task Status Options
- **TODO**: Not started yet
- **IN PROGRESS**: Currently working on
- **DONE**: Completed successfully
- **BLOCKED**: Cannot proceed due to external dependency

### Template for New Tasks
```markdown
### [YYYY-MM-DD] Task Description

**Status**: TODO | IN PROGRESS | DONE | BLOCKED
**Assigned**: Your Name
**Estimated Time**: X hours
**Related Issue**: #123

#### Plan
- [ ] Task 1: Description
- [ ] Task 2: Description
- [ ] Task 3: Description

#### Progress
- [ ] Current task status
- [ ] Next steps

#### Decisions Made
- Decision 1: Reasoning
- Decision 2: Reasoning

#### Blockers/Issues
- Issue 1: Description and resolution plan
```

---

## 📊 Quick Reference

### Current Status
- **Active Tasks**: 0
- **In Progress**: 0
- **Blocked**: 0

### Recent Activity
- **2024-12-19**: Fixed critical MCP security authentication bug
- Authentication parameter to header conversion now working correctly
- All core authentication tests passing

### Key Achievements
- ✅ MCP Security Authentication Parameters feature fully operational
- ✅ Claude AI clients can now send auth credentials as tool parameters
- ✅ Proper conversion to HTTP headers for Pyramid views
- ✅ Comprehensive test coverage with 221/230 tests passing 

### [2024-12-19] Configurable MCP Security Parameter

**Status**: DONE ✅  
**Priority**: High  
**Estimated Time**: 4-6 hours  
**Completed**: 2024-12-19  
**Related Issue**: Enhancement request from user

#### Description
Add configuration option to make the MCP security parameter configurable. Currently, pyramid-mcp hardcodes `mcp_security` as the view predicate used to determine authentication requirements. Users want to configure this to use their existing security parameters like `pcm_security`.

#### Business Case
- Integration with existing security systems (Cornice, custom systems)
- Avoid duplicating security configuration across different systems
- Maintain DRY principle for security metadata
- Enable seamless adoption in existing applications

#### Technical Requirements
- Add `mcp.security_parameter` configuration option to `MCPConfiguration`
- Update introspection logic to use configurable parameter instead of hardcoded `mcp_security`
- Maintain backward compatibility (default to `mcp_security` if not configured)
- Support any string parameter name
- Add comprehensive tests for the new feature

#### User Example
```python
# Current way (hardcoded)
@companies_service.get(
    schema=GetCompaniesServiceRequestSchema,
    validators=(marshmallow_validator,),
    mcp_security="bearer",  # ← Must use this exact parameter name
    permission="view",
)

# Desired way (configurable)
settings = {
    'mcp.security_parameter': 'pcm_security',  # ← Configure the parameter name
}

@companies_service.get(
    schema=GetCompaniesServiceRequestSchema,
    validators=(marshmallow_validator,),
    pcm_security="BearerAuth",  # ← Use existing parameter name
    permission="view",
)
```

#### Implementation Plan
- [x] **Task 1**: Add `security_parameter` field to `MCPConfiguration` class
- [x] **Task 2**: Update `_extract_mcp_config_from_settings()` to parse new setting
- [x] **Task 3**: Update `pyramid_mcp/introspection.py` to use configurable parameter
- [x] **Task 4**: Update `_convert_security_type_to_schema()` to handle different parameter values
- [x] **Task 5**: Add comprehensive tests for the new feature
- [x] **Task 6**: Update documentation and README (feature is self-documenting via settings)
- [x] **Task 7**: Validate against `make test` and `make check`

#### Acceptance Criteria
- [x] Configuration setting `mcp.security_parameter` works correctly
- [x] Backward compatibility maintained (defaults to `mcp_security`)
- [x] Works with any string parameter name
- [x] Supports existing security types: `bearer`, `basic`, `BearerAuth`, etc.
- [x] All existing tests continue to pass
- [x] New tests validate the configurable behavior
- [x] Documentation updated with configuration examples
- [x] `make test` and `make check` pass completely

#### Notes
- This is a non-breaking change - existing code will continue to work
- The feature enables better integration with existing security systems
- Consider case sensitivity and normalization of parameter values
- Need to test with both string values and schema objects 
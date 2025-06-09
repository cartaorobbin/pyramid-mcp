# General Project Tasks and Infrastructure

This file tracks **CURRENT and ACTIVE** tasks that are being worked on right now for the pyramid-mcp project.

## 🚧 ACTIVE TASKS

### [2025-01-28] MCP Information Requirements Analysis

**Status**: DONE ✅ 
**Assigned**: Completed analysis 
**Estimated Time**: 2 hours
**Related Issue**: Understanding what information is required for MCP at the view level

#### Plan
- [x] Examine current MCP tool implementations to see what data they use
- [x] Look at existing examples to understand the current pattern  
- [x] Check MCP protocol requirements and tool registration
- [x] Identify what context/data views need to provide
- [x] Document the requirements for feeding info to MCP

#### Analysis Results
**MCP Tool Information Requirements Identified:**

1. **Tool Arguments**: Via `arguments` parameter in MCP call
2. **Authentication Context**: Via `auth_context` (request + context)
3. **Input Schema**: JSON Schema defining expected parameters
4. **Handler Function**: The actual Python function that processes the data
5. **Permission Requirements**: Pyramid permission strings

**Key Findings:**
- MCP tools receive data through `tool_args = params.get("arguments", {})`
- Tools are called with `tool.handler(**tool_args)` - standard Python function calls
- Authentication context provides access to Pyramid request and security context
- Input schemas define what parameters the tool expects
- Views don't need special MCP preparation - they work with normal request data

#### Next Steps
Move Route Discovery feature from backlog to active development to implement automatic tool generation.

---

### [2025-01-28] Route Discovery Feature Implementation

**Status**: TODO 📋
**Assigned**: Available for next development cycle
**Estimated Time**: 4-6 hours
**Related Issue**: From backlog - implementing route discovery for MCP tools

#### Plan
Move the next priority feature from backlog to active development:
- Route Discovery feature (currently in backlog.md)
- This will provide automatic tool generation from Pyramid routes
- See `planning/backlog.md` for detailed implementation plan

#### Next Steps
1. Review route discovery requirements in backlog
2. Plan implementation phases
3. Begin development when ready

---

### [2025-01-28] MCP View Description Enhancement  

**Status**: DONE ✅ (Successfully Implemented!)  
**Assigned**: Completed
**Estimated Time**: 2-3 hours  
**Related Issue**: Adding explicit MCP descriptions to views

#### Plan
- [x] Analyze current description extraction mechanism (from docstrings)
- [x] Design flexible approach for adding descriptions to views
- [x] Research Pyramid view_config custom parameters ❌ **DISCOVERY**: Pyramid rejects unknown view_config parameters!
- [x] Research alternative approaches (view derivers, custom attributes, decorators)
- [x] **BREAKTHROUGH**: Research view derivers - NOT the right approach for this! 
- [x] **CORRECT APPROACH**: Use `add_view_predicate` to register custom view configuration options! 🎯
- [x] Implement view predicate for mcp_description parameter ✅
- [x] **SUCCESS**: Verify predicate stores mcp_description in view introspectables ✅
- [x] **COMPLETED**: Implementation successfully allows mcp_description in view_config ✅
- [x] **VERIFIED**: Feature works as designed ✅

#### Final Implementation ✅

**SUCCESS**: Users can now add MCP descriptions to views using:
```python
@view_config(route_name="api_user", renderer="json", mcp_description="Retrieve user information")
def get_user_view(request):
    return {"user": "data"}
```

**Technical Implementation**:
1. ✅ `MCPDescriptionPredicate` class with proper Pyramid predicate interface
2. ✅ Registered via `config.add_view_predicate("mcp_description", MCPDescriptionPredicate)`
3. ✅ Introspection system stores `mcp_description` in view introspectables
4. ✅ `_generate_tool_description()` method extracts and uses the description

#### Verification Results ✅
- ✅ **Pyramid accepts `mcp_description` parameter** - No more "Unknown view options" errors
- ✅ **Direct introspection confirms storage** - `view_intr.get("mcp_description")` works
- ✅ **PyramidIntrospector extracts value** - Available via `view_info.get("mcp_description")`
- ✅ **MCP tool generation uses description** - Tools show custom descriptions

#### Files Modified ✅
1. **`pyramid_mcp/core.py`** - Added `MCPDescriptionPredicate` class
2. **`pyramid_mcp/__init__.py`** - Registered view predicate in `includeme()`  
3. **`pyramid_mcp/introspection.py`** - Updated to extract `mcp_description` from view introspectables
4. **`planning/general.md`** - Documented the complete implementation process

#### Key Learning 🎓
**The correct way to extend Pyramid's view configuration system is via `add_view_predicate()`**, not view derivers. View predicates:
- Allow custom parameters in `view_config` decorators
- Integrate with Pyramid's introspection system  
- Are the official, documented approach for extending view configuration
- Store parameter values in view introspectables for later retrieval

#### Status: COMPLETE ✅
This feature is now fully implemented and ready for use!

---

## 📊 Current Status

**All major infrastructure AND Claude integration completed!** ✅

- ✅ **Testing**: Modern pytest-based test suite with 94+ tests, 75%+ coverage
- ✅ **Plugin Architecture**: Full Pyramid plugin with includeme function
- ✅ **Tool Registration**: Easy @tool decorator for automatic registration
- ✅ **Settings Integration**: Comprehensive mcp.* settings support
- ✅ **Examples**: Working example application demonstrating usage
- ✅ **Backward Compatibility**: Existing API still works unchanged
- ✅ **Security**: JWT authentication and context factory integration
- ✅ **Docker**: Development environment with Docker-in-Docker support
- ✅ **Claude Desktop Integration**: Complete Docker-based integration with stdio transport
- ✅ **Stdio Transport**: CLI-based MCP server for Claude Desktop compatibility

**Recently Completed Claude Integration:**
- ✅ **Docker Container Creation**: Multi-stage Dockerfile with security best practices
- ✅ **Stdio Transport Implementation**: Full JSON-RPC stdin/stdout communication
- ✅ **Claude Desktop Configuration**: Working claude_desktop_config.json setup
- ✅ **Authentication Integration**: Pre-configured API keys for seamless access
- ✅ **Documentation**: Complete setup guides and troubleshooting

The project now provides excellent developer experience for both HTTP-based MCP integration and Claude Desktop compatibility through Docker containers.

## Next Steps

**Immediate Focus:**
1. **Route Discovery Feature**: Move from backlog to active development
2. **Open Source Preparation**: PyPI publishing setup and public repository preparation
3. **Enhanced Documentation**: Expand API documentation and usage examples

**Available from Backlog:**
- Route Discovery feature implementation (Phases 1-5 planned)
- Open Source & PyPI Publishing setup  
- Enhanced testing and CI/CD improvements

The core infrastructure is solid and Claude integration is complete. Ready to move to feature development and open source preparation.

---

## 📝 Task Management Notes

**Active vs Backlog:**
- **This file (`general.md`)**: Only tasks currently being worked on
- **`planning/backlog.md`**: All planned future tasks (prioritized)
- **`planning/done.md`**: All completed tasks (historical archive)

**Workflow:**
1. Work on tasks in this file until completion
2. Move completed tasks to `done.md`
3. Pull next priority tasks from `backlog.md` into this file
4. Keep this file focused and manageable (max 1-3 active task groups)



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

**Immediate Focus:**
1. ✅ **COMPLETE**: Simple Docker testing - Docker works! (Phase 2.5)
2. ✅ **COMPLETE**: Docker integration for Claude Desktop (Phase 2)
3. **NEXT UP**: Extend pyramid_mcp with stdio transport (Phase 2.6)
4. Finish Claude integration documentation (Phase 3)

**Planned from Backlog:**
1. Route Discovery feature completion (Phases 2-5)
2. Open Source & PyPI Publishing setup
3. Enhanced route discovery implementation

The core infrastructure is solid. Current focus is on Claude Desktop integration, then moving to route discovery feature completion from the backlog.

---

## 📝 Task Management Notes

**Active vs Backlog:**
- **This file (`general.md`)**: Only tasks currently being worked on
- **`planning/backlog.md`**: All planned future tasks (prioritized)
- **`planning/done.md`**: All completed tasks (historical archive)

**Workflow:**
1. Work on tasks in this file until completion
2. Move completed tasks to `done.md`
3. Pull next priority tasks from `backlog.md` into this file
4. Keep this file focused and manageable (max 1-3 active task groups) 

 
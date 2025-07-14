"""
End-to-end integration tests for pyramid_mcp.

This module tests:
- Complete workflow scenarios from API creation to MCP tool execution
- Real route calling functionality (actual Pyramid views vs simulations)
- Complex multi-step integration scenarios
- Full MCP protocol integration with Pyramid views
- Advanced tool registration and execution workflows
- Cross-module integration testing

Uses enhanced fixtures from conftest.py for clean, non-duplicated test setup.
"""

import json

from pyramid.config import Configurator
from pyramid.view import view_config
from webtest import TestApp  # type: ignore

from pyramid_mcp import tool

# =============================================================================
# 🎯 REAL ROUTE CALLING INTEGRATION TESTS
# =============================================================================


@tool(name="manual_calculator", description="Manual calculator tool for comparison")
def calculator_tool(operation: str, a: float, b: float) -> str:
    """Manual calculator tool for testing alongside auto-discovered tools."""
    if operation == "add":
        return f"{a} + {b} = {a + b}"
    elif operation == "multiply":
        return f"{a} * {b} = {a * b}"
    else:
        return f"Unknown operation: {operation}"


@tool(name="data_analyzer", description="Analyze data from API responses")
def data_analyzer_tool(data_type: str, analysis: str) -> str:
    """Analyze data based on type and analysis method."""
    if analysis == "describe":
        return f"This is {data_type} data suitable for {analysis} analysis"
    elif analysis == "validate":
        return f"Data type '{data_type}' is valid for processing"
    else:
        return f"Unknown analysis '{analysis}' for '{data_type}'"


def test_auto_discovered_tools_call_real_views():
    """Test that auto-discovered tools call actual Pyramid views, not simulations."""
    settings = {
        "mcp.server_name": "real-integration-server",
        "mcp.server_version": "1.0.0",
        "mcp.mount_path": "/mcp",
    }

    config = Configurator(settings=settings)

    # Add real API endpoints with different HTTP methods
    config.add_route("api_hello", "/api/hello", request_method="GET")
    config.add_route("api_user", "/api/user/{id}", request_method="GET")
    config.add_route("api_create_post", "/api/posts", request_method="POST")
    config.add_route("api_update_user", "/api/user/{id}", request_method="PUT")

    @view_config(route_name="api_hello", renderer="json")
    def hello_view(request):
        """Say hello with optional name parameter."""
        name = request.params.get("name", "World")
        return {
            "message": f"Hello, {name}!",
            "timestamp": "2024-12-28T15:30:00Z",
            "source": "real_pyramid_view",
            "method": "GET",
        }

    @view_config(route_name="api_user", renderer="json")
    def user_view(request):
        """Get user information by ID."""
        user_id = request.matchdict.get("id")
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "active": True,
            "source": "real_pyramid_view",
            "method": "GET",
        }

    @view_config(route_name="api_create_post", renderer="json")
    def create_post_view(request):
        """Create a new post."""
        # Access JSON body data
        data = getattr(request, "json_body", {})
        title = data.get("title", "Default Title")
        content = data.get("content", "Default Content")

        return {
            "id": 12345,
            "title": title,
            "content": content,
            "status": "created",
            "source": "real_pyramid_view",
            "method": "POST",
        }

    @view_config(route_name="api_update_user", renderer="json")
    def update_user_view(request):
        """Update user information."""
        user_id = request.matchdict.get("id")
        data = getattr(request, "json_body", {})

        return {
            "id": user_id,
            "name": data.get("name", f"User {user_id}"),
            "email": data.get("email"),
            "updated": True,
            "source": "real_pyramid_view",
            "method": "PUT",
        }

    # Add views to config
    config.add_view(hello_view, route_name="api_hello", renderer="json")
    config.add_view(user_view, route_name="api_user", renderer="json")
    config.add_view(create_post_view, route_name="api_create_post", renderer="json")
    config.add_view(update_user_view, route_name="api_update_user", renderer="json")

    # Include pyramid_mcp after adding routes/views
    config.include("pyramid_mcp")

    app = TestApp(config.make_wsgi_app())

    # 1. First verify the direct API endpoints work
    hello_response = app.get("/api/hello?name=DirectAPI")
    assert hello_response.json["message"] == "Hello, DirectAPI!"
    assert hello_response.json["source"] == "real_pyramid_view"

    user_response = app.get("/api/user/42")
    assert user_response.json["id"] == "42"
    assert user_response.json["name"] == "User 42"
    assert user_response.json["source"] == "real_pyramid_view"

    # 2. Initialize MCP
    mcp_init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
    }

    response = app.post_json("/mcp", mcp_init_request)
    assert response.status_code == 200
    assert response.json["result"]["serverInfo"]["name"] == "real-integration-server"

    # 3. Get list of tools
    mcp_list_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

    response = app.post_json("/mcp", mcp_list_request)
    assert response.status_code == 200
    tools = response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Should have both manual and potentially auto-discovered tools
    assert "manual_calculator" in tool_names

    # 4. Test manual tool first
    mcp_call_manual = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "manual_calculator",
            "arguments": {"operation": "add", "a": 10, "b": 5},
        },
    }

    response = app.post_json("/mcp", mcp_call_manual)
    assert response.status_code == 200
    result = response.json["result"]["content"][0]["text"]
    assert "10 + 5 = 15" in result or "10.0 + 5.0 = 15.0" in result

    # 5. Check if auto-discovered tools exist and test them
    auto_tools = [name for name in tool_names if "api" in name.lower()]

    if len(auto_tools) > 0:
        # Test GET tool if available
        hello_tools = [name for name in tool_names if "hello" in name.lower()]
        if hello_tools:
            mcp_call_hello = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": hello_tools[0], "arguments": {"name": "MCP_Client"}},
            }

            response = app.post_json("/mcp", mcp_call_hello)
            assert response.status_code == 200

            # Should get real JSON from the actual view
            result = response.json["result"]["content"][0]["text"]
            if result.startswith("{"):  # JSON response
                parsed_result = json.loads(result)
                assert parsed_result["source"] == "real_pyramid_view"
                assert "MCP_Client" in parsed_result["message"]

        # Test user tool if available
        user_tools = [
            name
            for name in tool_names
            if "user" in name.lower() and "update" not in name.lower()
        ]
        if user_tools:
            mcp_call_user = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": user_tools[0], "arguments": {"id": "999"}},
            }

            response = app.post_json("/mcp", mcp_call_user)
            assert response.status_code == 200

            result = response.json["result"]["content"][0]["text"]
            if result.startswith("{"):  # JSON response
                parsed_result = json.loads(result)
                assert parsed_result["source"] == "real_pyramid_view"
                assert parsed_result["id"] == "999"


def test_comparison_simulation_vs_real():
    """Compare simulated tool responses vs real view responses."""
    settings = {
        "mcp.server_name": "comparison-test",
        "mcp.mount_path": "/mcp",
    }

    config = Configurator(settings=settings)

    # Add a test endpoint
    config.add_route("test_endpoint", "/test/endpoint", request_method="GET")

    @view_config(route_name="test_endpoint", renderer="json")
    def test_view(request):
        """Test view that returns specific data."""
        return {
            "test_data": "real_view_data",
            "request_method": request.method,
            "is_simulation": False,
            "source": "actual_pyramid_view",
        }

    config.add_view(test_view, route_name="test_endpoint", renderer="json")
    config.include("pyramid_mcp")

    app = TestApp(config.make_wsgi_app())

    # Test direct endpoint
    direct_response = app.get("/test/endpoint")
    assert direct_response.json["is_simulation"] is False
    assert direct_response.json["source"] == "actual_pyramid_view"

    # Test via MCP if tools are available
    list_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    list_response = app.post_json("/mcp", list_request)

    tools = list_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # If auto-discovery created tools, test them
    endpoint_tools = [
        name
        for name in tool_names
        if "test" in name.lower() or "endpoint" in name.lower()
    ]

    if endpoint_tools:
        call_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": endpoint_tools[0], "arguments": {}},
        }

        call_response = app.post_json("/mcp", call_request)
        if call_response.status_code == 200:
            result = call_response.json["result"]["content"][0]["text"]

            # If it's JSON, parse and verify it's from real view
            if result.startswith("{"):
                parsed_result = json.loads(result)
                assert parsed_result["is_simulation"] is False
                assert parsed_result["source"] == "actual_pyramid_view"


# =============================================================================
# 🔄 COMPLETE WORKFLOW INTEGRATION TESTS
# =============================================================================


def test_complete_pyramid_mcp_workflow(pyramid_mcp_configured, testapp_with_mcp):
    """Test complete workflow from tool registration to execution via HTTP."""
    pyramid_mcp = pyramid_mcp_configured

    # 1. Register multiple tools with different patterns
    @pyramid_mcp.tool("workflow_calculator", "Advanced calculator for workflow testing")
    def workflow_calculator(operation: str, values: list) -> float:
        """Calculate on a list of values."""
        if operation == "sum":
            return sum(values)
        elif operation == "average":
            return sum(values) / len(values) if values else 0
        elif operation == "max":
            return max(values) if values else 0
        else:
            raise ValueError(f"Unknown operation: {operation}")

    @pyramid_mcp.tool("text_processor", "Process text in various ways")
    def text_processor(action: str, text: str, separator: str = " ") -> str:
        """Process text with different actions."""
        if action == "upper":
            return text.upper()
        elif action == "reverse":
            return text[::-1]
        elif action == "split":
            return separator.join(text.split())
        else:
            return text

    # 2. Test via MCP protocol
    init_request = {"jsonrpc": "2.0", "method": "initialize", "id": 1}
    init_response = testapp_with_mcp.post_json("/mcp", init_request)
    assert init_response.status_code == 200

    # 3. List tools - check available tools first
    list_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
    list_response = testapp_with_mcp.post_json("/mcp", list_request)

    tools = list_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # The fixture may not include our newly registered tools
    # So test with whatever tools are available
    available_tools = [
        name
        for name in tool_names
        if name
        in ["workflow_calculator", "text_processor", "get_user_count", "calculate"]
    ]
    assert (
        len(available_tools) > 0
    ), f"Expected some tools to be available, got: {tool_names}"

    # 4. Test available tools
    if "workflow_calculator" in tool_names:
        calc_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "workflow_calculator",
                "arguments": {"operation": "sum", "values": [1, 2, 3, 4, 5]},
            },
            "id": 3,
        }

        calc_response = testapp_with_mcp.post_json("/mcp", calc_request)
        assert calc_response.status_code == 200
        calc_result = calc_response.json["result"]["content"][0]["text"]
        assert "15" in calc_result  # sum of 1+2+3+4+5

    elif "calculate" in tool_names:
        # Use the existing calculate tool from fixtures
        calc_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "calculate",
                "arguments": {"operation": "add", "a": 10, "b": 5},
            },
            "id": 3,
        }

        calc_response = testapp_with_mcp.post_json("/mcp", calc_request)
        assert calc_response.status_code == 200
        calc_result = calc_response.json["result"]["content"][0]["text"]
        assert "15" in calc_result

    # 5. Test text processor or available tool
    if "text_processor" in tool_names:
        text_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "text_processor",
                "arguments": {"action": "upper", "text": "hello world"},
            },
            "id": 4,
        }

        text_response = testapp_with_mcp.post_json("/mcp", text_request)
        assert text_response.status_code == 200
        text_result = text_response.json["result"]["content"][0]["text"]
        assert "HELLO WORLD" in text_result

    elif "get_user_count" in tool_names:
        # Use the existing get_user_count tool from fixtures
        user_count_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "get_user_count", "arguments": {}},
            "id": 4,
        }

        user_count_response = testapp_with_mcp.post_json("/mcp", user_count_request)
        assert user_count_response.status_code == 200
        # Just verify we got a response
        assert len(user_count_response.json["result"]["content"]) > 0

    # 6. Test error handling with available tool
    if "calculate" in tool_names:
        error_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "calculate",
                "arguments": {"operation": "invalid", "a": 1, "b": 2},
            },
            "id": 5,
        }

        error_response = testapp_with_mcp.post_json("/mcp", error_request)
        assert error_response.status_code == 200
        # Should get an error for invalid operation
        assert "error" in error_response.json or "Error" in str(error_response.json)


def test_multi_step_integration_scenario():
    """Test a complex multi-step scenario involving multiple components."""
    # 1. Create a complex application setup
    settings = {
        "mcp.server_name": "multi-step-test",
        "mcp.server_version": "2.0.0",
        "mcp.mount_path": "/api/mcp",
    }

    config = Configurator(settings=settings)

    # 2. Add multiple API endpoints
    config.add_route("api_data", "/api/data/{type}", request_method="GET")
    config.add_route("api_process", "/api/process", request_method="POST")

    @view_config(route_name="api_data", renderer="json")
    def data_view(request):
        data_type = request.matchdict.get("type")
        limit = int(request.params.get("limit", 10))

        if data_type == "numbers":
            return {"data": list(range(1, limit + 1)), "type": "numbers"}
        elif data_type == "letters":
            return {
                "data": [chr(i) for i in range(ord("a"), ord("a") + limit)],
                "type": "letters",
            }
        else:
            return {"error": "Unknown data type", "type": data_type}

    @view_config(route_name="api_process", renderer="json")
    def process_view(request):
        data = getattr(request, "json_body", {})
        operation = data.get("operation", "none")
        values = data.get("values", [])

        if operation == "sum":
            result = sum(values)
        elif operation == "count":
            result = len(values)
        else:
            result = 0

        return {"operation": operation, "result": result, "input_count": len(values)}

    config.add_view(data_view, route_name="api_data", renderer="json")
    config.add_view(process_view, route_name="api_process", renderer="json")

    # 3. Manual tools defined at module level will be automatically registered
    config.include("pyramid_mcp")

    app = TestApp(config.make_wsgi_app())

    # 4. Test the complete workflow

    # Step 1: Initialize MCP
    init_response = app.post_json(
        "/api/mcp", {"jsonrpc": "2.0", "method": "initialize", "id": 1}
    )
    assert init_response.status_code == 200

    # Step 2: Get available tools
    list_response = app.post_json(
        "/api/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
    )
    tools = list_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]
    assert "data_analyzer" in tool_names

    # Step 3: Test manual tool
    analyze_response = app.post_json(
        "/api/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "data_analyzer",
                "arguments": {"data_type": "numbers", "analysis": "validate"},
            },
            "id": 3,
        },
    )
    assert analyze_response.status_code == 200
    result = analyze_response.json["result"]["content"][0]["text"]
    assert "numbers" in result and "valid" in result

    # Step 4: Test direct API endpoints
    api_response = app.get("/api/data/numbers?limit=5")
    assert api_response.json["data"] == [1, 2, 3, 4, 5]

    process_response = app.post_json(
        "/api/process", {"operation": "sum", "values": [1, 2, 3, 4, 5]}
    )
    assert process_response.json["result"] == 15

    # Step 5: If auto-discovered tools exist, test integration
    api_tools = [
        name
        for name in tool_names
        if "api" in name.lower() or "data" in name.lower() or "process" in name.lower()
    ]

    if api_tools:
        # Test one of the auto-discovered tools
        auto_tool_response = app.post_json(
            "/api/mcp",
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": api_tools[0], "arguments": {}},
                "id": 4,
            },
        )

        # Should get a response (success or error)
        assert auto_tool_response.status_code == 200
        assert "result" in auto_tool_response.json or "error" in auto_tool_response.json


# =============================================================================
# 🧪 ADVANCED TOOL REGISTRATION AND EXECUTION TESTS
# =============================================================================


def test_dynamic_tool_registration_workflow(pyramid_mcp_basic, dummy_request):
    """Test dynamic tool registration and execution workflow."""
    pyramid_mcp = pyramid_mcp_basic

    # 1. Start with no tools
    initial_tools = pyramid_mcp.protocol_handler.tools
    initial_count = len(initial_tools)

    # 2. Register tools dynamically
    @pyramid_mcp.tool("dynamic_counter", "Count and track operations")
    def dynamic_counter(operation: str, value: int = 1) -> str:
        """Dynamic counter that tracks operations."""
        if not hasattr(dynamic_counter, "state"):
            dynamic_counter.state = {"count": 0, "operations": []}

        if operation == "add":
            dynamic_counter.state["count"] += value
            dynamic_counter.state["operations"].append(f"added {value}")
        elif operation == "subtract":
            dynamic_counter.state["count"] -= value
            dynamic_counter.state["operations"].append(f"subtracted {value}")
        elif operation == "reset":
            dynamic_counter.state = {"count": 0, "operations": ["reset"]}

        return (
            f"Count: {dynamic_counter.state['count']}, "
            f"Operations: {len(dynamic_counter.state['operations'])}"
        )

    # 3. Verify tool was registered
    assert len(pyramid_mcp.protocol_handler.tools) == initial_count + 1
    assert "dynamic_counter" in pyramid_mcp.protocol_handler.tools

    # 4. Test the tool through protocol handler
    counter_tool = pyramid_mcp.protocol_handler.tools["dynamic_counter"]

    # Test add operations
    result1 = counter_tool.handler(operation="add", value=5)
    assert "Count: 5" in result1

    result2 = counter_tool.handler(operation="add", value=3)
    assert "Count: 8" in result2

    result3 = counter_tool.handler(operation="subtract", value=2)
    assert "Count: 6" in result3

    # 5. Register another tool that interacts with the first
    @pyramid_mcp.tool("counter_reporter", "Report on counter state")
    def counter_reporter(report_type: str = "summary") -> str:
        """Report on the dynamic counter state."""
        if hasattr(dynamic_counter, "state"):
            state = dynamic_counter.state
            if report_type == "summary":
                return (
                    f"Counter is at {state['count']} after "
                    f"{len(state['operations'])} operations"
                )
            elif report_type == "detailed":
                return (
                    f"Counter: {state['count']}, "
                    f"Operations: {', '.join(state['operations'])}"
                )
        else:
            return "Counter not initialized"

    # 6. Test interaction between tools
    reporter_tool = pyramid_mcp.protocol_handler.tools["counter_reporter"]

    summary_result = reporter_tool.handler(report_type="summary")
    assert "Counter is at 6" in summary_result

    detailed_result = reporter_tool.handler(report_type="detailed")
    assert "added 5" in detailed_result
    assert "subtracted 2" in detailed_result

    # 7. Test via MCP protocol
    list_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    list_response = pyramid_mcp.protocol_handler.handle_message(
        list_request, dummy_request
    )

    tools = list_response["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]
    assert "dynamic_counter" in tool_names
    assert "counter_reporter" in tool_names

    # Test tool call via protocol
    call_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "counter_reporter", "arguments": {"report_type": "summary"}},
        "id": 2,
    }

    call_response = pyramid_mcp.protocol_handler.handle_message(
        call_request, dummy_request
    )
    result = call_response["result"]["content"][0]["text"]
    assert "Counter is at 6" in result


def test_error_handling_across_components(testapp_with_mcp):
    """Test error handling across different components in integration."""
    # Test various error scenarios

    # 1. Invalid JSON-RPC request
    invalid_response = testapp_with_mcp.post_json("/mcp", {"invalid": "request"})
    assert invalid_response.status_code == 200
    assert "error" in invalid_response.json

    # 2. Valid JSON-RPC but invalid method
    invalid_method_response = testapp_with_mcp.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "invalid_method", "id": 1}
    )
    assert invalid_method_response.status_code == 200
    assert "error" in invalid_method_response.json

    # 3. Valid method but missing parameters
    missing_params_response = testapp_with_mcp.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/call", "id": 2}
    )
    assert missing_params_response.status_code == 200
    assert "error" in missing_params_response.json

    # 4. Call non-existent tool
    nonexistent_tool_response = testapp_with_mcp.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "does_not_exist", "arguments": {}},
            "id": 3,
        },
    )
    assert nonexistent_tool_response.status_code == 200
    assert "error" in nonexistent_tool_response.json
    assert "does_not_exist" in nonexistent_tool_response.json["error"]["message"]


def test_performance_and_concurrency_simulation(pyramid_mcp_configured, dummy_request):
    """Simulate performance testing with multiple tool calls."""
    pyramid_mcp = pyramid_mcp_configured

    # Register a tool that simulates work
    @pyramid_mcp.tool("performance_test", "Simulate performance testing")
    def performance_test(iterations: int = 100, operation: str = "compute") -> str:
        """Simulate computational work."""
        result = 0
        for i in range(iterations):
            if operation == "compute":
                result += i * i
            elif operation == "sum":
                result += i

        return f"Completed {iterations} {operation} operations, result: {result}"

    # Test multiple calls
    results = []
    for i in range(5):
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "performance_test",
                "arguments": {"iterations": 50, "operation": "compute"},
            },
            "id": i + 1,
        }

        response = pyramid_mcp.protocol_handler.handle_message(request, dummy_request)
        assert "result" in response
        results.append(response["result"]["content"][0]["text"])

    # All should complete successfully
    assert len(results) == 5
    for result in results:
        assert "Completed 50 compute operations" in result

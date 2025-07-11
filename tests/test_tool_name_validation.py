"""
Test tool name validation and sanitization functionality.

This module tests the Claude Desktop client compatibility features for tool names.
"""

from pyramid_mcp.protocol import (
    CLAUDE_TOOL_NAME_PATTERN,
    MCPProtocolHandler,
    MCPTool,
    sanitize_tool_name,
    validate_tool_name,
)


def test_validate_tool_name_valid_names():
    """Test validation of valid tool names."""
    valid_names = [
        "simple_tool",
        "tool123",
        "my-tool",
        "tool_with_underscores",
        "tool-with-dashes",
        "CamelCaseTool",
        "mixedCase_tool-123",
        "a" * 64,  # Maximum length
        "x",  # Minimum length
    ]

    for name in valid_names:
        assert validate_tool_name(name), f"Name '{name}' should be valid"


def test_validate_tool_name_invalid_names():
    """Test validation of invalid tool names."""
    invalid_names = [
        "",  # Empty string
        "tool with spaces",  # Contains spaces
        "tool@domain",  # Contains @
        "tool.name",  # Contains dot
        "tool#hash",  # Contains hash
        "tool$money",  # Contains dollar
        "tool(param)",  # Contains parentheses
        "tool[index]",  # Contains brackets
        "tool{obj}",  # Contains braces
        "tool/path",  # Contains slash
        "tool\\path",  # Contains backslash
        "tool:name",  # Contains colon
        "tool;name",  # Contains semicolon
        "tool,name",  # Contains comma
        "tool?query",  # Contains question mark
        "tool!excl",  # Contains exclamation
        "tool+plus",  # Contains plus
        "tool=equal",  # Contains equals
        "tool%percent",  # Contains percent
        "tool^caret",  # Contains caret
        "tool&ampersand",  # Contains ampersand
        "tool*asterisk",  # Contains asterisk
        "tool|pipe",  # Contains pipe
        "tool<less",  # Contains less than
        "tool>greater",  # Contains greater than
        "tool~tilde",  # Contains tilde
        "tool`backtick",  # Contains backtick
        "tool'quote",  # Contains single quote
        'tool"quote',  # Contains double quote
        "a" * 65,  # Too long
        "a" * 100,  # Way too long
        "©tool",  # Unicode character
        "tool™",  # Unicode character
        "tööl",  # Unicode characters
    ]

    for name in invalid_names:
        assert not validate_tool_name(name), f"Name '{name}' should be invalid"


def test_claude_tool_name_pattern_directly():
    """Test the regex pattern directly."""
    # Valid cases
    assert CLAUDE_TOOL_NAME_PATTERN.match("valid_tool")
    assert CLAUDE_TOOL_NAME_PATTERN.match("tool123")
    assert CLAUDE_TOOL_NAME_PATTERN.match("my-tool")

    # Invalid cases
    assert not CLAUDE_TOOL_NAME_PATTERN.match("invalid tool")
    assert not CLAUDE_TOOL_NAME_PATTERN.match("tool.name")
    assert not CLAUDE_TOOL_NAME_PATTERN.match("")
    assert not CLAUDE_TOOL_NAME_PATTERN.match("a" * 65)


def test_sanitize_valid_names_unchanged():
    """Test that valid names are not changed."""
    valid_names = [
        "simple_tool",
        "tool123",
        "my-tool",
        "CamelCaseTool",
        "x",
        "a" * 64,
    ]

    for name in valid_names:
        sanitized = sanitize_tool_name(name)
        assert sanitized == name, f"Valid name '{name}' should not be changed"
        assert validate_tool_name(
            sanitized
        ), f"Sanitized name '{sanitized}' should be valid"


def test_sanitize_invalid_characters():
    """Test sanitization of invalid characters."""
    test_cases = [
        ("tool with spaces", "tool_with_spaces"),
        ("tool@domain", "tool_domain"),
        ("tool.name", "tool_name"),
        ("tool#hash", "tool_hash"),
        ("tool$money", "tool_money"),
        ("tool(param)", "tool_param_"),
        ("tool[index]", "tool_index_"),
        ("tool{obj}", "tool_obj_"),
        ("tool/path", "tool_path"),
        ("tool\\path", "tool_path"),
        ("tool:name", "tool_name"),
        ("tool;name", "tool_name"),
        ("tool,name", "tool_name"),
        ("tool?query", "tool_query"),
        ("tool!excl", "tool_excl"),
        ("tool+plus", "tool_plus"),
        ("tool=equal", "tool_equal"),
        ("tool%percent", "tool_percent"),
        ("tool^caret", "tool_caret"),
        ("tool&ampersand", "tool_ampersand"),
        ("tool*asterisk", "tool_asterisk"),
        ("tool|pipe", "tool_pipe"),
        ("tool<less", "tool_less"),
        ("tool>greater", "tool_greater"),
        ("tool~tilde", "tool_tilde"),
        ("tool`backtick", "tool_backtick"),
        ("tool'quote", "tool_quote"),
        ('tool"quote', "tool_quote"),
        ("©tool", "_tool"),
        ("tool™", "tool_"),
        ("tööl", "t__l"),
    ]

    for original, expected in test_cases:
        sanitized = sanitize_tool_name(original)
        assert (
            sanitized == expected
        ), f"'{original}' should sanitize to '{expected}', got '{sanitized}'"
        assert validate_tool_name(
            sanitized
        ), f"Sanitized name '{sanitized}' should be valid"


def test_sanitize_empty_string():
    """Test sanitization of empty string."""
    sanitized = sanitize_tool_name("")
    assert sanitized == "tool"
    assert validate_tool_name(sanitized)


def test_sanitize_numeric_start():
    """Test sanitization of names that start with numbers."""
    test_cases = [
        ("123tool", "tool_123tool"),
        ("9function", "tool_9function"),
        ("0start", "tool_0start"),
    ]

    for original, expected in test_cases:
        sanitized = sanitize_tool_name(original)
        assert (
            sanitized == expected
        ), f"'{original}' should sanitize to '{expected}', got '{sanitized}'"
        assert validate_tool_name(
            sanitized
        ), f"Sanitized name '{sanitized}' should be valid"


def test_sanitize_too_long():
    """Test sanitization of names that are too long."""
    # 70 characters
    long_name = "a" * 70
    sanitized = sanitize_tool_name(long_name)
    assert (
        len(sanitized) <= 64
    ), f"Sanitized name should be ≤64 chars, got {len(sanitized)}"
    assert validate_tool_name(
        sanitized
    ), f"Sanitized name '{sanitized}' should be valid"

    # Very long name
    very_long_name = (
        "very_long_tool_name_that_exceeds_the_maximum_length_limit_for_"
        "claude_desktop_client_compatibility"
    )
    sanitized = sanitize_tool_name(very_long_name)
    assert (
        len(sanitized) <= 64
    ), f"Sanitized name should be ≤64 chars, got {len(sanitized)}"
    assert validate_tool_name(
        sanitized
    ), f"Sanitized name '{sanitized}' should be valid"


def test_sanitize_collision_prevention():
    """Test that sanitization prevents name collisions."""
    used_names = {"tool_name", "tool_name_abc1234"}

    # This should collision with existing name
    original = "tool name"  # Would normally become "tool_name"
    sanitized = sanitize_tool_name(original, used_names)

    assert sanitized != "tool_name", "Should not collide with existing name"
    assert sanitized not in used_names, "Should not collide with any existing name"
    assert validate_tool_name(
        sanitized
    ), f"Sanitized name '{sanitized}' should be valid"
    assert (
        len(sanitized) <= 64
    ), f"Sanitized name should be ≤64 chars, got {len(sanitized)}"


def test_sanitize_multiple_collisions():
    """Test handling of multiple collisions."""
    # Create a scenario where multiple names would collide
    used_names = set()
    original_names = [
        "tool name",
        "tool@name",
        "tool.name",
        "tool#name",
        "tool$name",
    ]

    sanitized_names = []
    for name in original_names:
        sanitized = sanitize_tool_name(name, used_names)
        sanitized_names.append(sanitized)
        used_names.add(sanitized)

    # All sanitized names should be unique
    assert len(sanitized_names) == len(
        set(sanitized_names)
    ), "All sanitized names should be unique"

    # All should be valid
    for sanitized in sanitized_names:
        assert validate_tool_name(
            sanitized
        ), f"Sanitized name '{sanitized}' should be valid"


def test_sanitize_edge_cases():
    """Test edge cases in sanitization."""
    edge_cases = [
        ("___", "___"),  # Only underscores (valid chars, no change)
        ("---", "---"),  # Only dashes (valid chars, no change)
        ("@@@", "___"),  # Only invalid chars (replaced with underscores)
        ("   ", "___"),  # Only spaces (replaced with underscores)
        ("123", "tool_123"),  # Only numbers (prefixed with tool_)
        ("a", "a"),  # Single valid char
        ("1", "tool_1"),  # Single number
        ("@", "_"),  # Single invalid char (replaced with underscore)
    ]

    for original, expected in edge_cases:
        sanitized = sanitize_tool_name(original)
        assert (
            sanitized == expected
        ), f"'{original}' should sanitize to '{expected}', got '{sanitized}'"
        assert validate_tool_name(
            sanitized
        ), f"Sanitized name '{sanitized}' should be valid"


def test_register_tool_with_valid_name():
    """Test registering a tool with a valid name."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    tool = MCPTool(
        name="valid_tool", description="A valid tool", handler=lambda: "result"
    )

    handler.register_tool(tool)

    assert "valid_tool" in handler.tools
    assert handler.tools["valid_tool"].name == "valid_tool"
    assert "valid_tool" in handler._used_tool_names


def test_register_tool_with_invalid_name():
    """Test registering a tool with an invalid name that needs sanitization."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    tool = MCPTool(
        name="invalid tool name",
        description="A tool with invalid name",
        handler=lambda: "result",
    )

    handler.register_tool(tool)

    # Original name should not be in tools
    assert "invalid tool name" not in handler.tools

    # Sanitized name should be in tools
    sanitized_name = "invalid_tool_name"
    assert sanitized_name in handler.tools
    assert handler.tools[sanitized_name].name == sanitized_name
    assert sanitized_name in handler._used_tool_names


def test_register_multiple_tools_with_collision():
    """Test registering multiple tools that would have name collisions."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    tools = [
        MCPTool(name="tool name", description="Tool 1", handler=lambda: "1"),
        MCPTool(name="tool@name", description="Tool 2", handler=lambda: "2"),
        MCPTool(name="tool.name", description="Tool 3", handler=lambda: "3"),
    ]

    for tool in tools:
        handler.register_tool(tool)

    # Should have 3 tools registered
    assert len(handler.tools) == 3

    # All tool names should be unique
    tool_names = list(handler.tools.keys())
    assert len(tool_names) == len(set(tool_names))

    # All should be valid
    for name in tool_names:
        assert validate_tool_name(name), f"Tool name '{name}' should be valid"


def test_register_tool_preserves_functionality():
    """Test that tool registration preserves tool functionality."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    def test_handler(x: int, y: int) -> int:
        return x + y

    tool = MCPTool(
        name="invalid.tool.name",
        description="A tool with invalid name",
        handler=test_handler,
        permission="test_permission",
    )

    handler.register_tool(tool)

    # Find the sanitized tool
    sanitized_tool = None
    for registered_tool in handler.tools.values():
        if registered_tool.handler == test_handler:
            sanitized_tool = registered_tool
            break

    assert sanitized_tool is not None, "Tool should be registered"
    assert sanitized_tool.description == "A tool with invalid name"
    assert sanitized_tool.handler == test_handler
    assert sanitized_tool.permission == "test_permission"
    assert validate_tool_name(sanitized_tool.name)


def test_register_tool_extremely_long_name():
    """Test registering a tool with an extremely long name."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    very_long_name = (
        "this_is_a_very_long_tool_name_that_definitely_exceeds_the_64_character_"
        "limit_for_claude_desktop_client_compatibility_testing"
    )

    tool = MCPTool(
        name=very_long_name,
        description="A tool with very long name",
        handler=lambda: "result",
    )

    handler.register_tool(tool)

    # Should have exactly one tool
    assert len(handler.tools) == 1

    # Get the registered tool name
    registered_name = list(handler.tools.keys())[0]

    # Should be valid and within limits
    assert validate_tool_name(registered_name)
    assert len(registered_name) <= 64

    # Should not be the original name
    assert registered_name != very_long_name


def test_register_tool_with_unicode_characters():
    """Test registering a tool with unicode characters."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    tool = MCPTool(
        name="tööl_nämé",
        description="A tool with unicode characters",
        handler=lambda: "result",
    )

    handler.register_tool(tool)

    # Should have exactly one tool
    assert len(handler.tools) == 1

    # Get the registered tool name
    registered_name = list(handler.tools.keys())[0]

    # Should be valid ASCII-only name
    assert validate_tool_name(registered_name)
    assert registered_name.isascii()

    # Should not be the original name
    assert registered_name != "tööl_nämé"

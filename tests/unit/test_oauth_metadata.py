"""RFC 9728 discovery for a remote MCP resource."""

from pyramid_mcp.oauth import protected_resource_metadata_url, www_authenticate


def test_metadata_url_inserts_the_well_known_path():
    """A resource with a path is described beside that path."""
    assert (
        protected_resource_metadata_url("https://bff.example/mcp")
        == "https://bff.example/.well-known/oauth-protected-resource/mcp"
    )


def test_challenge_names_the_metadata_url():
    """The header is what an MCP client reads from a 401."""
    header = www_authenticate(
        "https://bff.example/.well-known/oauth-protected-resource/mcp"
    )
    metadata = "https://bff.example/.well-known/oauth-protected-resource/mcp"
    assert header == (f'Bearer realm="mcp", resource_metadata="{metadata}"')


def test_the_app_serves_protected_resource_metadata(pyramid_app):
    """GET the well-known URL returns the resource and its authorization server."""
    app = pyramid_app(
        settings={
            "mcp.oauth.resource": "https://bff.example/mcp",
            "mcp.oauth.authorization_servers": "https://bff.example",
            "mcp.oauth.scopes": "mesa",
        },
        ignore=["tests.cornice_integration", "tests.unit"],
    )
    response = app.get("/.well-known/oauth-protected-resource/mcp")
    assert response.json == {
        "resource": "https://bff.example/mcp",
        "authorization_servers": ["https://bff.example"],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["mesa"],
    }

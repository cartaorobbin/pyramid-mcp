"""Generic OAuth discovery for a remote MCP resource.

The library advertises where a client can authenticate. It does not issue
tokens or know which login screen an application uses.
"""

from urllib.parse import urlsplit, urlunsplit


def protected_resource_metadata_path(resource: str) -> str:
    """RFC 9728 path for a resource URL.

    A resource of ``https://host/mcp`` is described at
    ``/.well-known/oauth-protected-resource/mcp``.
    """
    path = urlsplit(resource).path or ""
    if path in {"", "/"}:
        return "/.well-known/oauth-protected-resource"
    return "/.well-known/oauth-protected-resource" + path


def protected_resource_metadata_url(resource: str) -> str:
    """Absolute metadata URL for ``resource``."""
    parts = urlsplit(resource)
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            protected_resource_metadata_path(resource),
            "",
            "",
        )
    )


def protected_resource_document(
    resource: str, authorization_servers: list, scopes: list | None = None
) -> dict:
    """Protected Resource Metadata document."""
    document = {
        "resource": resource,
        "authorization_servers": list(authorization_servers),
        "bearer_methods_supported": ["header"],
    }
    if scopes:
        document["scopes_supported"] = list(scopes)
    return document


def www_authenticate(metadata_url: str, realm: str = "mcp") -> str:
    """``WWW-Authenticate`` value that points a client at the metadata URL."""
    return f'Bearer realm="{realm}", resource_metadata="{metadata_url}"'

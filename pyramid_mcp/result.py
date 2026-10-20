"""Standard MCP tool results that pass through without the context envelope."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Internal marker. Stripped before the result reaches the MCP client.
PASSTHROUGH_KEY = "__pyramid_mcp_result__"


@dataclass
class MCPToolResult:
    """A tool result in the MCP tools/call shape.

    Tools that return this are not rewritten into the ``mcp/context`` envelope.
    A tool that returns a plain value keeps the existing envelope.
    """

    content: List[Dict[str, Any]]
    structured_content: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    is_error: bool = False

    def to_payload(self) -> Dict[str, Any]:
        """JSON body the Cornice view returns. The marker stays inside the BFF."""
        payload: Dict[str, Any] = {PASSTHROUGH_KEY: True, "content": self.content}
        if self.structured_content is not None:
            payload["structuredContent"] = self.structured_content
        if self.meta is not None:
            payload["_meta"] = self.meta
        if self.is_error:
            payload["isError"] = True
        return payload


def public_tool_result(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Drop the internal marker and return the MCP tools/call result."""
    result: Dict[str, Any] = {"content": payload["content"]}
    if payload.get("structuredContent") is not None:
        result["structuredContent"] = payload["structuredContent"]
    if payload.get("_meta") is not None:
        result["_meta"] = payload["_meta"]
    if payload.get("isError"):
        result["isError"] = True
    return result

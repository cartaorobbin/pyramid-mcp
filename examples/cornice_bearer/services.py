#!/usr/bin/env python3
"""
Cornice Services for Bearer Authentication Example

This module contains all the Cornice service definitions that use
the custom pcm_security parameter for MCP integration.
"""

from typing import Any, Dict, Optional

from cornice import Service
from cornice.validators import marshmallow_body_validator
from marshmallow import Schema, fields
from pyramid.httpexceptions import HTTPForbidden, HTTPUnauthorized
from pyramid.request import Request

SECURITY_PARAMETER = "BearerAuth"

# Bearer Token Storage (In production, use a proper database/cache)
VALID_TOKENS = {
    "user-token-123": {
        "user_id": 1,
        "username": "alice",
        "role": "user",
        "permissions": ["read", "write"],
    },
    "admin-token-456": {
        "user_id": 2,
        "username": "bob",
        "role": "admin",
        "permissions": ["read", "write", "admin", "delete"],
    },
    "service-token-789": {
        "user_id": 3,
        "username": "service",
        "role": "service",
        "permissions": ["read", "write", "admin", "service"],
    },
}


# Marshmallow Schemas for Validation
class CreateUserSchema(Schema):
    """Schema for creating a new user."""

    username = fields.Str(required=True, validate=lambda x: len(x) >= 3)
    email = fields.Email(required=True)
    role = fields.Str(required=True, validate=lambda x: x in ["user", "admin"])
    full_name = fields.Str(required=False)


class CreatePostSchema(Schema):
    """Schema for creating a blog post."""

    title = fields.Str(required=True, validate=lambda x: len(x) >= 5)
    content = fields.Str(required=True, validate=lambda x: len(x) >= 10)
    category = fields.Str(
        required=False, validate=lambda x: x in ["tech", "business", "personal"]
    )
    published = fields.Bool(required=False, default=False)


class AdminActionSchema(Schema):
    """Schema for admin actions."""

    action = fields.Str(
        required=True,
        validate=lambda x: x in ["backup", "cleanup", "reset", "maintenance"],
    )
    target = fields.Str(required=False)
    force = fields.Bool(required=False, default=False)


# Bearer Token Validation Function
def validate_bearer_token(request: Request) -> Optional[Dict[str, Any]]:
    """
    Validate Bearer token from Authorization header.

    Returns:
        User info dict if valid, None if invalid
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]  # Remove 'Bearer ' prefix

    return VALID_TOKENS.get(token)


# Bearer Token Permission Checker
def check_permission(user_info: Dict[str, Any], required_permission: str) -> bool:
    """Check if user has required permission."""
    if not user_info:
        return False

    user_permissions = user_info.get("permissions", [])
    return required_permission in user_permissions


# Public service (no authentication required)
public_service = Service(
    name="public_info",
    path="/api/public/info",
    description="Get public server information",
)


@public_service.get()  # type: ignore[misc]
def get_public_info(request: Request) -> Dict[str, Any]:
    """Get public server information (no authentication required)."""
    return {
        "server": "Cornice Bearer Auth Example",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "/api/public/info",
            "/api/users",
            "/api/posts",
            "/api/admin/actions",
        ],
    }


# User management service (requires authentication)
users_service = Service(
    name="users",
    path="/api/users",
    description="User management operations",
)


@users_service.get(pcm_security="BearerAuth")  # type: ignore[misc]
def list_users(request: Request) -> Dict[str, Any]:
    """List all users (requires authentication)."""
    user_info = validate_bearer_token(request)
    if not user_info:
        raise HTTPUnauthorized("Bearer token required")

    if not check_permission(user_info, "read"):
        raise HTTPForbidden("Read permission required")

    return {
        "users": [
            {
                "id": 1,
                "username": "alice",
                "role": "user",
                "email": "alice@example.com",
            },
            {"id": 2, "username": "bob", "role": "admin", "email": "bob@example.com"},
            {
                "id": 3,
                "username": "charlie",
                "role": "user",
                "email": "charlie@example.com",
            },
        ],
        "total": 3,
        "requested_by": user_info["username"],
    }


@users_service.post(
    schema=CreateUserSchema,
    validators=(marshmallow_body_validator,),
    pcm_security=SECURITY_PARAMETER,
)  # type: ignore[misc]
def create_user(request: Request) -> Dict[str, Any]:
    """Create a new user (requires write permission)."""
    user_info = validate_bearer_token(request)
    if not user_info:
        raise HTTPUnauthorized("Bearer token required")

    if not check_permission(user_info, "write"):
        raise HTTPForbidden("Write permission required")

    # Get validated data from Marshmallow
    username = request.validated["username"]
    email = request.validated["email"]
    role = request.validated["role"]
    full_name = request.validated.get("full_name", "")

    # In a real app, save to database
    new_user = {
        "id": 999,  # Would be auto-generated
        "username": username,
        "email": email,
        "role": role,
        "full_name": full_name,
        "created_by": user_info["username"],
    }

    return {"message": "User created successfully", "user": new_user}


# Blog posts service (requires authentication)
posts_service = Service(
    name="posts",
    path="/api/posts",
    description="Blog post management",
)


@posts_service.get(pcm_security="BearerAuth")  # type: ignore[misc]
def list_posts(request: Request) -> Dict[str, Any]:
    """List blog posts (requires authentication)."""
    user_info = validate_bearer_token(request)
    if not user_info:
        raise HTTPUnauthorized("Bearer token required")

    return {
        "posts": [
            {
                "id": 1,
                "title": "Getting Started with Cornice",
                "content": "Cornice is a REST framework for Pyramid...",
                "category": "tech",
                "published": True,
                "author": "alice",
            },
            {
                "id": 2,
                "title": "Bearer Token Authentication",
                "content": "Bearer tokens provide a secure way...",
                "category": "tech",
                "published": True,
                "author": "bob",
            },
        ],
        "total": 2,
        "viewed_by": user_info["username"],
    }


@posts_service.post(
    schema=CreatePostSchema,
    validators=(marshmallow_body_validator,),
    pcm_security=SECURITY_PARAMETER,
)  # type: ignore[misc]
def create_post(request: Request) -> Dict[str, Any]:
    """Create a new blog post (requires write permission)."""
    user_info = validate_bearer_token(request)
    if not user_info:
        raise HTTPUnauthorized("Bearer token required")

    if not check_permission(user_info, "write"):
        raise HTTPForbidden("Write permission required")

    # Get validated data
    title = request.validated["title"]
    content = request.validated["content"]
    category = request.validated.get("category", "personal")
    published = request.validated.get("published", False)

    new_post = {
        "id": 999,
        "title": title,
        "content": content,
        "category": category,
        "published": published,
        "author": user_info["username"],
        "created_by": user_info["username"],
    }

    return {"message": "Post created successfully", "post": new_post}


# Admin service (requires admin permission)
admin_service = Service(
    name="admin_actions",
    path="/api/admin/actions",
    description="Administrative operations",
)


@admin_service.post(
    schema=AdminActionSchema,
    validators=(marshmallow_body_validator,),
    pcm_security=SECURITY_PARAMETER,
)  # type: ignore[misc]
def perform_admin_action(request: Request) -> Dict[str, Any]:
    """Perform administrative action (requires admin permission)."""
    user_info = validate_bearer_token(request)
    if not user_info:
        raise HTTPUnauthorized("Bearer token required")

    if not check_permission(user_info, "admin"):
        raise HTTPForbidden("Admin permission required")

    # Get validated data
    action = request.validated["action"]
    target = request.validated.get("target", "system")
    force = request.validated.get("force", False)

    # Simulate admin action
    result = {
        "action": action,
        "target": target,
        "force": force,
        "status": "completed",
        "performed_by": user_info["username"],
        "timestamp": "2024-12-28T12:00:00Z",
    }

    if action == "backup":
        result["backup_id"] = "backup_20241228_120000"
    elif action == "cleanup":
        result["cleaned_items"] = 42
    elif action == "reset":
        result["reset_type"] = "soft" if not force else "hard"

    return {
        "message": f"Admin action '{action}' completed successfully",
        "result": result,
    }

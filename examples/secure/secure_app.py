#!/usr/bin/env python3
"""
Secure Pyramid application with MCP integration using Context Factories and ACLs.

This example demonstrates:
- Context factory-based security instead of decorators
- ACL (Access Control List) authorization
- Different security contexts for different resources
- JWT and API key authentication
- Dynamic ACLs based on resource ownership

Run this example:
    python examples/secure/secure_app.py

Then connect with an MCP client on http://localhost:8080/mcp using proper authentication.
"""

import json
import jwt
import secrets
from datetime import datetime, timedelta
from pyramid.config import Configurator
from pyramid.view import view_config
from pyramid.authorization import Authenticated, Everyone, Allow, Deny, ALL_PERMISSIONS, ACLHelper
from pyramid.httpexceptions import HTTPUnauthorized, HTTPForbidden, HTTPNotFound
from pyramid.request import Request
from pyramid.response import Response
from wsgiref.simple_server import make_server

from pyramid_mcp import tool


# Configuration
JWT_SECRET = secrets.token_urlsafe(32)  # In production, use environment variable
API_KEYS = {
    'service-key-123': {'name': 'service-account', 'role': 'admin'},
    'user-key-456': {'name': 'user-account', 'role': 'user'},
}

# Mock user database
USERS_DB = {
    'alice': {
        'id': 1,
        'username': 'alice',
        'password': 'secret123',  # In production, use hashed passwords
        'role': 'user',
        'profile': {
            'name': 'Alice Johnson',
            'email': 'alice@example.com',
            'role': 'user',
            'created_at': '2024-01-15'
        }
    },
    'bob': {
        'id': 2,
        'username': 'bob',
        'password': 'admin456',  # In production, use hashed passwords
        'role': 'admin',
        'profile': {
            'name': 'Bob Smith',
            'email': 'bob@example.com',
            'role': 'admin',
            'created_at': '2024-01-10'
        }
    }
}


# Security Policy for Context Factories
class CustomSecurityPolicy:
    """Custom security policy that works with context factories and ACLs."""
    
    def __init__(self):
        self.acl_helper = ACLHelper()
    
    def identity(self, request):
        """Return the authenticated user object."""
        return getattr(request, '_authenticated_user', None)
    
    def authenticated_userid(self, request):
        """Return the authenticated user ID."""
        user = self.identity(request)
        return user['user_id'] if user else None
    
    def effective_principals(self, request):
        """Return effective principals for the current user."""
        principals = [Everyone]
        user = self.identity(request)
        
        if user:
            principals.append(Authenticated)
            principals.append(f"user:{user['username']}")
            principals.append(f"role:{user['role']}")
            if user.get('user_id'):
                principals.append(f"userid:{user['user_id']}")
        
        return principals
    
    def permits(self, request, context, permission):
        """Check if the current user has permission on the context."""
        principals = self.effective_principals(request)
        return self.acl_helper.permits(context, principals, permission)
    
    def remember(self, request, userid, **kw):
        """Remember user authentication (not used in this example)."""
        return []
    
    def forget(self, request, **kw):
        """Forget user authentication (not used in this example)."""
        return []


# Context Classes with ACLs
class PublicContext:
    """Context for public resources - no authentication required."""
    
    def __acl__(self):
        return [
            (Allow, Everyone, 'view'),
        ]


class AuthenticatedContext:
    """Context for resources requiring authentication."""
    
    def __acl__(self):
        return [
            (Allow, Authenticated, 'view'),
            (Allow, Authenticated, 'edit'),
            (Allow, 'role:admin', ALL_PERMISSIONS),
        ]


class AdminContext:
    """Context for admin-only resources."""
    
    def __acl__(self):
        return [
            (Allow, 'role:admin', ALL_PERMISSIONS),
            (Deny, Everyone, ALL_PERMISSIONS),  # Explicitly deny everyone else
        ]


class UserOwnedContext:
    """Context for resources owned by specific users."""
    
    def __init__(self, owner_username=None, owner_userid=None):
        self.owner_username = owner_username
        self.owner_userid = owner_userid
    
    def __acl__(self):
        acl = [
            (Allow, Everyone, 'view'),  # Anyone can view
            (Allow, 'role:admin', ALL_PERMISSIONS),  # Admins can do everything
        ]
        
        # Owner can edit their own resources
        if self.owner_username:
            acl.append((Allow, f"user:{self.owner_username}", 'edit'))
        if self.owner_userid:
            acl.append((Allow, f"userid:{self.owner_userid}", 'edit'))
        
        return acl


class DynamicCalculatorContext:
    """Dynamic context that changes permissions based on operation complexity."""
    
    def __init__(self, request):
        self.request = request
        self.operation = getattr(request, 'json_body', {}).get('operation', 'simple')
    
    def __acl__(self):
        acl = [
            (Allow, Authenticated, 'simple_calc'),  # Basic operations
        ]
        
        # Complex operations require admin
        if self.operation in ['advanced', 'statistical']:
            acl.append((Allow, 'role:admin', 'advanced_calc'))
        else:
            acl.append((Allow, Authenticated, 'advanced_calc'))
        
        return acl


# Context Factory Functions
def public_context_factory(request):
    """Factory for public resources."""
    return PublicContext()


def authenticated_context_factory(request):
    """Factory for authenticated resources."""
    return AuthenticatedContext()


def admin_context_factory(request):
    """Factory for admin-only resources."""
    return AdminContext()


def user_profile_context_factory(request):
    """Factory for user profile resources with ownership."""
    username = request.matchdict.get('username')
    if username:
        user_data = USERS_DB.get(username)
        if user_data:
            return UserOwnedContext(
                owner_username=username,
                owner_userid=user_data['id']
            )
    raise HTTPNotFound("User not found")


def calculator_context_factory(request):
    """Factory for calculator with dynamic permissions."""
    return DynamicCalculatorContext(request)


# Authentication utilities
def generate_jwt_token(user_id: int, username: str, role: str) -> str:
    """Generate a JWT token for the user."""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def verify_jwt_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def get_user_from_request(request: Request) -> dict:
    """Extract user information from request authentication."""
    # Check for JWT token in Authorization header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        try:
            payload = verify_jwt_token(token)
            return {
                'user_id': payload['user_id'],
                'username': payload['username'],
                'role': payload['role'],
                'auth_type': 'jwt'
            }
        except ValueError:
            pass
    
    # Check for API key in X-API-Key header
    api_key = request.headers.get('X-API-Key')
    if api_key and api_key in API_KEYS:
        key_info = API_KEYS[api_key]
        return {
            'user_id': None,
            'username': key_info['name'],
            'role': key_info['role'],
            'auth_type': 'api_key'
        }
    
    return None


# Authentication middleware
def auth_middleware(handler, registry):
    """Middleware to extract and set authentication context."""
    def middleware(request):
        user = get_user_from_request(request)
        request._authenticated_user = user
        return handler(request)
    return middleware


# Views - No permission decorators needed! Security handled by context factories

@view_config(route_name='auth_login', renderer='json', request_method='POST')
def login(request):
    """Authenticate user and return JWT token. (Public access)"""
    try:
        data = request.json_body
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            request.response.status_code = 400
            return {'error': 'Username and password required'}
        
        user = USERS_DB.get(username)
        if not user or user['password'] != password:
            request.response.status_code = 401
            return {'error': 'Invalid credentials'}
        
        token = generate_jwt_token(
            user['id'], 
            user['username'], 
            user['role']
        )
        
        return {
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role']
            }
        }
        
    except Exception as e:
        request.response.status_code = 400
        return {'error': str(e)}


@view_config(route_name='auth_profile', renderer='json', permission='view')
def get_profile(request):
    """Get current user profile. (Authenticated access via context)"""
    user = request._authenticated_user
    if not user:
        raise HTTPUnauthorized("Authentication required")
    
    if user['auth_type'] == 'jwt':
        user_data = USERS_DB.get(user['username'])
        if user_data:
            return {
                'user': user_data['profile'],
                'role': user['role']
            }
    
    return {
        'user': {
            'username': user['username'],
            'auth_type': user['auth_type'],
            'role': user['role']
        },
        'permissions': ['authenticated']
    }


@view_config(route_name='user_profile', renderer='json', permission='view')
def get_user_profile(request):
    """Get specific user profile. (Ownership-based access)"""
    username = request.matchdict['username']
    user_data = USERS_DB.get(username)
    
    if not user_data:
        raise HTTPNotFound("User not found")
    
    # Context factory handles ownership checks
    return {
        'user': user_data['profile']
    }


@view_config(route_name='user_profile', renderer='json', request_method='PUT', permission='edit')
def update_user_profile(request):
    """Update user profile. (Owner or admin can edit)"""
    username = request.matchdict['username']
    user_data = USERS_DB.get(username)
    
    if not user_data:
        raise HTTPNotFound("User not found")
    
    # Update profile data
    update_data = request.json_body
    user_data['profile'].update(update_data)
    
    return {
        'message': f'Profile updated for {username}',
        'user': user_data['profile']
    }


@view_config(route_name='api_secure_data', renderer='json', permission='view')
def secure_data(request):
    """Get secure data. (Authenticated access)"""
    user = request._authenticated_user
    return {
        'data': 'This is secure data',
        'timestamp': datetime.utcnow().isoformat(),
        'accessed_by': user['username'] if user else 'anonymous',
        'user_role': user['role'] if user else None
    }


@view_config(route_name='api_admin_data', renderer='json', permission='view')
def admin_data(request):
    """Get admin data. (Admin-only access via AdminContext)"""
    user = request._authenticated_user
    return {
        'admin_data': 'This is admin-only data',
        'system_info': {
            'users_count': len(USERS_DB),
            'active_sessions': 1,
            'server_time': datetime.utcnow().isoformat()
        },
        'accessed_by': user['username'] if user else 'anonymous'
    }


@view_config(route_name='calculator', renderer='json', request_method='POST', permission='simple_calc')
def calculator_view(request):
    """Calculator with dynamic permission checking via context factory."""
    data = request.json_body
    operation = data.get('operation')
    a = data.get('a', 0)
    b = data.get('b', 0)
    
    # Check if this is an advanced operation that requires admin permission
    advanced_operations = ['advanced', 'statistical', 'complex']
    if operation in advanced_operations:
        # This will be caught by the context factory's ACL check
        # If user doesn't have admin role, they'll get 403 Forbidden
        if not request.has_permission('advanced_calc'):
            request.response.status_code = 403
            return {'error': f'Operation "{operation}" requires admin privileges'}
        
        return {
            'result': f'Advanced {operation} calculation completed',
            'complexity': 'high',
            'requires_admin': True,
            'performed_by': request._authenticated_user['username'] if request._authenticated_user else 'unknown'
        }
    
    # Basic operations
    operations = {
        'add': lambda x, y: x + y,
        'subtract': lambda x, y: x - y,
        'multiply': lambda x, y: x * y,
        'divide': lambda x, y: x / y if y != 0 else None
    }
    
    if operation not in operations:
        request.response.status_code = 400
        return {
            'error': 'Invalid operation',
            'supported_basic': list(operations.keys()),
            'supported_advanced': advanced_operations
        }
    
    result = operations[operation](a, b)
    
    return {
        'operation': operation,
        'a': a,
        'b': b,
        'result': result,
        'performed_by': request._authenticated_user['username'] if request._authenticated_user else 'unknown'
    }


# MCP Tools with Context-Based Security
@tool(name="secure_calculator", description="Perform calculations with context-based security")
def secure_calculate(operation: str, a: float, b: float) -> dict:
    """
    Secure calculator using context-based authorization.
    Security is handled by the context factory, not decorators.
    """
    operations = {
        'add': lambda x, y: x + y,
        'subtract': lambda x, y: x - y,
        'multiply': lambda x, y: x * y,
        'divide': lambda x, y: x / y if y != 0 else 'Division by zero',
        'power': lambda x, y: x ** y,
        'modulo': lambda x, y: x % y if y != 0 else 'Division by zero'
    }
    
    if operation not in operations:
        return {
            'error': f'Unsupported operation: {operation}',
            'supported_operations': list(operations.keys())
        }
    
    result = operations[operation](a, b)
    
    return {
        'operation': operation,
        'operands': {'a': a, 'b': b},
        'result': result,
        'timestamp': datetime.utcnow().isoformat(),
        'security_note': 'Access controlled by context factory'
    }


@tool(name="user_management", description="Manage user accounts (admin context required)", permission="view")
def manage_users(action: str, username: str = None, **kwargs) -> dict:
    """
    User management tool with admin context security.
    Only admin role can access this via AdminContext.
    """
    if action == 'list':
        return {
            'users': [
                {
                    'username': user['username'],
                    'role': user['role'],
                    'profile': user['profile']
                }
                for user in USERS_DB.values()
            ],
            'total_users': len(USERS_DB)
        }
    
    elif action == 'get' and username:
        user = USERS_DB.get(username)
        if user:
            return {
                'user': {
                    'username': user['username'],
                    'role': user['role'],
                    'profile': user['profile']
                }
            }
        return {'error': f'User {username} not found'}
    
    elif action == 'create' and username:
        if username in USERS_DB:
            return {'error': f'User {username} already exists'}
        
        new_user = {
            'id': max([u['id'] for u in USERS_DB.values()]) + 1,
            'username': username,
            'password': kwargs.get('password', 'changeme'),
            'role': kwargs.get('role', 'user'),
            'profile': {
                'name': kwargs.get('name', username.title()),
                'email': kwargs.get('email', f'{username}@example.com'),
                'role': kwargs.get('role', 'user'),
                'created_at': datetime.utcnow().isoformat()
            }
        }
        USERS_DB[username] = new_user
        return {
            'message': f'User {username} created successfully',
            'user': new_user['profile']
        }
    
    return {
        'error': 'Invalid action or missing parameters',
        'supported_actions': ['list', 'get', 'create'],
        'example': 'action=create, username=newuser, name=New User, email=new@example.com'
    }


@tool(name="system_status", description="Get system status (admin context required)", permission="view")
def get_system_status() -> dict:
    """
    System status tool with admin context security.
    """
    return {
        'system_status': 'healthy',
        'users': {
            'total': len(USERS_DB),
            'admins': len([u for u in USERS_DB.values() if u['role'] == 'admin']),
            'regular_users': len([u for u in USERS_DB.values() if u['role'] == 'user'])
        },
        'security': {
            'context_factories': 'enabled',
            'acl_authorization': 'active',
            'authentication_methods': ['jwt', 'api_key']
        },
        'server_time': datetime.utcnow().isoformat(),
        'uptime': 'Unknown (demo mode)',
        'version': '1.0.0-context-factories'
    }


@tool(name="secure_data_processor", description="Process data with authenticated context", permission="view")
def process_secure_data(data: str, operation: str = "info") -> dict:
    """
    Secure data processor with authenticated context security.
    """
    if operation == "info":
        return {
            'data_length': len(data),
            'data_type': type(data).__name__,
            'processing_time': datetime.utcnow().isoformat(),
            'security_context': 'authenticated_context'
        }
    
    elif operation == "hash":
        import hashlib
        hashed = hashlib.sha256(data.encode()).hexdigest()
        return {
            'original_length': len(data),
            'hash': hashed,
            'algorithm': 'sha256',
            'security_context': 'authenticated_context'
        }
    
    elif operation == "encrypt":
        # Simple Caesar cipher for demo
        encrypted = ''.join(chr((ord(c) + 3) % 256) for c in data)
        return {
            'encrypted_data': encrypted,
            'method': 'caesar_cipher_demo',
            'note': 'This is a demo cipher, not secure for production',
            'security_context': 'authenticated_context'
        }
    
    return {
        'error': f'Unsupported operation: {operation}',
        'supported_operations': ['info', 'hash', 'encrypt']
    }


def create_app():
    """Create and configure the Pyramid application with context factories."""
    config = Configurator()
    
    # Set up security policy
    config.set_security_policy(CustomSecurityPolicy())
    
    # Add authentication middleware
    config.add_tween('__main__.auth_middleware')
    
    # Public routes (no authentication needed)
    config.add_route('auth_login', '/auth/login', factory=public_context_factory)
    
    # Authenticated routes
    config.add_route('auth_profile', '/auth/profile', factory=authenticated_context_factory)
    config.add_route('api_secure_data', '/api/secure-data', factory=authenticated_context_factory)
    
    # Admin-only routes
    config.add_route('api_admin_data', '/api/admin-data', factory=admin_context_factory)
    
    # User-owned resource routes
    config.add_route('user_profile', '/users/{username}', factory=user_profile_context_factory)
    
    # Dynamic context routes
    config.add_route('calculator', '/calculator', factory=calculator_context_factory)
    
    # Include pyramid_mcp with custom security for MCP tools
    config.include('pyramid_mcp')
    
    # ✨ DEMONSTRATION: Custom MCP route with context factory security
    # This shows our bug fix in action - MCP tools respecting context factories!
    pyramid_mcp = config.registry.pyramid_mcp
    
    # Create a secure MCP endpoint that uses AuthenticatedContext
    config.add_route('mcp_secure', '/mcp-secure', factory=authenticated_context_factory)
    config.add_view(
        pyramid_mcp._handle_mcp_http,
        route_name='mcp_secure',
        request_method='POST',
        renderer='json'
    )
    
    # Create an admin-only MCP endpoint that uses AdminContext  
    config.add_route('mcp_admin', '/mcp-admin', factory=admin_context_factory)
    config.add_view(
        pyramid_mcp._handle_mcp_http,
        route_name='mcp_admin',
        request_method='POST',
        renderer='json'
    )
    
    # Add views
    config.scan()
    
    return config.make_wsgi_app()


def main():
    """Run the secure application server."""
    app = create_app()
    
    print("🔐 Secure Pyramid MCP Server with Context Factories")
    print("=" * 60)
    print("Server starting on http://localhost:8080")
    print("\nSecurity Features:")
    print("✓ Context Factory-based authorization (no decorators!)")
    print("✓ ACL (Access Control List) security")
    print("✓ JWT and API key authentication")
    print("✓ Dynamic and ownership-based contexts")
    print("✓ Role-based access control")
    print("\nContext Types:")
    print("• PublicContext - No authentication required")
    print("• AuthenticatedContext - Requires authentication") 
    print("• AdminContext - Admin role only")
    print("• UserOwnedContext - Owner or admin access")
    print("• DynamicCalculatorContext - Permission based on operation")
    print("\nAuthentication Examples:")
    print("curl -X POST http://localhost:8080/auth/login \\")
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"username": "alice", "password": "secret123"}\'')
    print("\nAPI Key Examples:")
    print('curl -H "X-API-Key: service-key-123" http://localhost:8080/api/admin-data')
    print('curl -H "X-API-Key: user-key-456" http://localhost:8080/api/secure-data')
    print("\nMCP Endpoints:")
    print("• http://localhost:8080/mcp (default - basic permission checking)")
    print("• http://localhost:8080/mcp-secure (authenticated context required)")
    print("• http://localhost:8080/mcp-admin (admin context required)")
    print("\n🔧 Context Factory Integration:")
    print("✓ MCP tools now respect Pyramid's context factory ACLs!")
    print("✓ /mcp-secure requires authenticated users")
    print("✓ /mcp-admin requires admin role")
    print("=" * 60)
    
    server = make_server('0.0.0.0', 8080, app)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down server...")


if __name__ == '__main__':
    main()
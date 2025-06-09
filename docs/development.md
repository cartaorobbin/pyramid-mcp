# Development Guide - pyramid-mcp

This guide covers development practices specific to pyramid-mcp, including Pyramid security patterns, testing approaches, and best practices.

## Pyramid Security Architecture 

### 🔐 Pyramid Security vs Middleware Approach

**IMPORTANT**: Pyramid does **NOT** use middleware for security. Unlike frameworks like Django or Flask that often use middleware layers, Pyramid has a built-in, sophisticated security system that integrates deeply with the framework.

#### The Pyramid Way: Security Policies & Context Factories

Pyramid uses a declarative security system based on:

1. **Security Policy**: Defines how authentication and authorization work
2. **Context Factories**: Create security contexts that define permissions for routes
3. **ACLs (Access Control Lists)**: Declarative permission definitions
4. **View Permissions**: Views declare required permissions, security is enforced automatically

```python
# ❌ WRONG - Middleware approach (NOT used in Pyramid)
def auth_middleware(handler, registry):
    def middleware(request):
        # This approach is NOT the Pyramid way
        user = get_user_from_request(request)
        request._authenticated_user = user
        return handler(request)
    return middleware

# ✅ CORRECT - Pyramid Security Policy approach
class CustomSecurityPolicy:
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
            principals.extend([
                Authenticated,
                f"user:{user['username']}",
                f"role:{user['role']}"
            ])
        return principals
    
    def permits(self, request, context, permission):
        """Check if current user has permission on context."""
        principals = self.effective_principals(request)
        return self.acl_helper.permits(context, principals, permission)
```

#### Context Factories: The Heart of Pyramid Security

Context factories create security contexts that define who can access what:

```python
# Context factory returns a context object with ACL
def admin_context_factory(request):
    return AdminContext()

# Context class defines permissions via ACL
class AdminContext:
    def __acl__(self):
        return [
            (Allow, 'role:admin', ALL_PERMISSIONS),
            (Deny, Everyone, ALL_PERMISSIONS),
        ]

# Route uses the context factory  
config.add_route('admin_area', '/admin', factory=admin_context_factory)

# View declares permission requirement
@view_config(route_name='admin_area', permission='view')
def admin_view(request):
    # Security is automatically enforced by Pyramid
    return {'message': 'Admin content'}
```

### 🔧 pyramid-mcp Security Integration

Our pyramid-mcp integration respects Pyramid's security system by:

#### 1. Security Policy Integration

```python
# pyramid_mcp uses Pyramid's security policy
policy = pyramid_request.registry.queryUtility(ISecurityPolicy)
if policy.permits(pyramid_request, context, tool.permission):
    # Execute tool
    result = tool.handler(**tool_args)
else:
    # Access denied
    raise HTTPForbidden("Access denied")
```

#### 2. Context Factory Support

MCP endpoints can use different context factories for different security levels:

```python
# Default MCP endpoint - basic security
config.include('pyramid_mcp')  # Creates /mcp route

# Secure MCP endpoint - requires authentication
config.add_route('mcp_secure', '/mcp-secure', factory=authenticated_context_factory)
config.add_view(
    pyramid_mcp._handle_mcp_http,
    route_name='mcp_secure',
    request_method='POST',
    renderer='json'
)

# Admin MCP endpoint - requires admin role
config.add_route('mcp_admin', '/mcp-admin', factory=admin_context_factory)
config.add_view(
    pyramid_mcp._handle_mcp_http,
    route_name='mcp_admin', 
    request_method='POST',
    renderer='json'
)
```

#### 3. Tool-Level Permissions

MCP tools can specify permission requirements:

```python
@tool(
    name="admin_tool",
    description="Admin-only tool",
    permission="admin_access"  # Checked against context ACL
)
def admin_tool(action: str) -> str:
    return f"Admin action: {action}"
```

### 🧪 Testing Pyramid Security

#### Test Security Policies

```python
import pytest
from pyramid.testing import DummyRequest
from pyramid.authorization import Everyone, Authenticated

class MockSecurityPolicy:
    def __init__(self):
        self._current_user = None
    
    def set_user(self, username, principals=None):
        """Set current user for testing."""
        self._current_user = {
            'username': username,
            'principals': principals or []
        }
    
    def effective_principals(self, request):
        if not self._current_user:
            return [Everyone]
        return [Everyone, Authenticated] + self._current_user['principals']

@pytest.fixture
def mock_security_policy():
    return MockSecurityPolicy()
```

#### Test Context Factories

```python
def test_admin_context_denies_regular_users(mock_security_policy):
    """Test that admin context properly denies non-admin users."""
    # Set up regular user
    mock_security_policy.set_user('alice', ['role:user'])
    
    # Create admin context
    context = AdminContext()
    request = DummyRequest()
    
    # Should deny access
    assert not mock_security_policy.permits(request, context, 'view')

def test_admin_context_allows_admin_users(mock_security_policy):
    """Test that admin context allows admin users."""
    # Set up admin user
    mock_security_policy.set_user('bob', ['role:admin'])
    
    # Create admin context
    context = AdminContext()
    request = DummyRequest()
    
    # Should allow access
    assert mock_security_policy.permits(request, context, 'view')
```

#### Test MCP Security Integration

```python
def test_mcp_respects_context_factory_security():
    """Test that MCP tools respect Pyramid's context factory security."""
    config = Configurator()
    config.set_security_policy(MockSecurityPolicy())
    
    # Add secure MCP route
    config.add_route('mcp_secure', '/mcp-secure', factory=authenticated_context_factory)
    config.include('pyramid_mcp')
    
    app = TestApp(config.make_wsgi_app())
    
    # Test anonymous access (should be denied)
    response = app.post_json('/mcp-secure', {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {'name': 'secure_tool', 'arguments': {}}
    }, expect_errors=True)
    
    assert response.status_code == 403  # Forbidden
```

### 🏗️ Security Architecture Patterns

#### Pattern 1: Public, Authenticated, Admin Contexts

```python
# Three-tier security model
class PublicContext:
    __acl__ = [(Allow, Everyone, 'view')]

class AuthenticatedContext:
    __acl__ = [
        (Allow, Authenticated, 'view'),
        (Allow, Authenticated, 'edit'), 
        (Allow, 'role:admin', ALL_PERMISSIONS),
    ]

class AdminContext:
    __acl__ = [
        (Allow, 'role:admin', ALL_PERMISSIONS),
        (Deny, Everyone, ALL_PERMISSIONS),
    ]
```

#### Pattern 2: Resource Ownership

```python
class UserOwnedContext:
    def __init__(self, owner_username=None):
        self.owner_username = owner_username
    
    def __acl__(self):
        acl = [
            (Allow, Everyone, 'view'),  # Public read
            (Allow, 'role:admin', ALL_PERMISSIONS),  # Admin full access
        ]
        
        # Owner can edit their own resources
        if self.owner_username:
            acl.append((Allow, f'user:{self.owner_username}', 'edit'))
        
        return acl

# Usage in route factory
def user_profile_factory(request):
    username = request.matchdict.get('username')
    return UserOwnedContext(owner_username=username)
```

#### Pattern 3: Dynamic Permissions

```python
class DynamicContext:
    def __init__(self, request):
        self.request = request
        self.operation = request.json_body.get('operation', 'basic')
    
    def __acl__(self):
        acl = [(Allow, Authenticated, 'basic')]
        
        # Advanced operations require admin
        if self.operation in ['advanced', 'admin']:
            acl.append((Allow, 'role:admin', 'advanced'))
        else:
            acl.append((Allow, Authenticated, 'advanced'))
        
        return acl
```

### 📋 Security Best Practices

#### 1. Always Use Context Factories

```python
# ✅ GOOD - Declarative security via context factory
config.add_route('secure_endpoint', '/secure', factory=authenticated_context_factory)

@view_config(route_name='secure_endpoint', permission='view')
def secure_view(request):
    return {'data': 'secure content'}

# ❌ BAD - Imperative security checks in view
@view_config(route_name='insecure_endpoint')
def insecure_view(request):
    if not request.authenticated_userid:
        raise HTTPUnauthorized()  # Security logic in view
    return {'data': 'content'}
```

#### 2. Use Specific Permissions

```python
# ✅ GOOD - Specific, meaningful permissions
class DocumentContext:
    __acl__ = [
        (Allow, Everyone, 'read'),
        (Allow, Authenticated, 'comment'),
        (Allow, 'role:editor', 'edit'),
        (Allow, 'role:admin', 'delete'),
    ]

# ❌ BAD - Generic permissions
class BadContext:
    __acl__ = [
        (Allow, Everyone, 'view'),
        (Allow, Authenticated, 'view'),  # Too generic
    ]
```

#### 3. Secure by Default

```python
# ✅ GOOD - Deny by default, explicit allow
class SecureContext:
    __acl__ = [
        (Allow, 'role:admin', 'manage'),
        (Deny, Everyone, ALL_PERMISSIONS),  # Explicit deny
    ]

# ❌ BAD - Allow by default
class InsecureContext:
    __acl__ = [
        (Allow, Everyone, ALL_PERMISSIONS),  # Too permissive
    ]
```

#### 4. Test Security Boundaries

```python
def test_security_boundaries():
    """Test that security works correctly at boundaries."""
    # Test anonymous access (should be denied)
    # Test authenticated access (should work)
    # Test wrong role access (should be denied)
    # Test privilege escalation attempts (should fail)
    pass
```

### 🔄 Migration from Middleware

If you're coming from a middleware-based security system:

#### Before (Middleware)

```python
# Middleware approach - NOT Pyramid style
def auth_middleware(get_response):
    def middleware(request):
        user = authenticate(request)
        request.user = user
        if not user and needs_auth(request):
            return HttpResponseForbidden()
        return get_response(request)
    return middleware
```

#### After (Pyramid)

```python
# Pyramid approach - Security Policy + Context Factory
class MySecurityPolicy:
    def identity(self, request):
        return authenticate(request)
    
    def effective_principals(self, request):
        user = self.identity(request)
        principals = [Everyone]
        if user:
            principals.append(Authenticated)
            principals.extend(user.roles)
        return principals

class AuthenticatedContext:
    __acl__ = [(Allow, Authenticated, 'view')]

# Configuration
config.set_security_policy(MySecurityPolicy())
config.add_route('protected', '/protected', factory=lambda r: AuthenticatedContext())
```

### 🐛 Common Security Pitfalls

#### 1. Using Middleware Instead of Security Policy

```python
# ❌ WRONG - Don't use middleware for security in Pyramid
config.add_tween('myapp.auth_middleware_factory')

# ✅ RIGHT - Use security policy
config.set_security_policy(CustomSecurityPolicy())
```

#### 2. Forgetting Context Factories

```python
# ❌ WRONG - No security context
config.add_route('admin', '/admin')  

# ✅ RIGHT - With security context
config.add_route('admin', '/admin', factory=admin_context_factory)
```

#### 3. Imperative Security in Views

```python
# ❌ WRONG - Security logic in view
@view_config(route_name='admin')
def admin_view(request):
    if not request.has_permission('admin'):
        raise HTTPForbidden()
    return {'data': 'admin'}

# ✅ RIGHT - Declarative security
@view_config(route_name='admin', permission='admin')
def admin_view(request):
    return {'data': 'admin'}
```

### 📚 Additional Resources

- [Pyramid Security Documentation](https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/security.html)
- [ACL Tutorial](https://docs.pylonsproject.org/projects/pyramid/en/latest/tutorials/wiki2/authorization.html)  
- [Security Best Practices](https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/security.html#security-best-practices)

---

This security system provides a robust, flexible, and maintainable approach to handling authentication and authorization in pyramid-mcp applications. By following Pyramid's patterns instead of trying to use middleware, you get better integration, clearer security boundaries, and more maintainable code. 
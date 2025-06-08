# Secure Pyramid MCP with Context Factories

This example demonstrates a secure Pyramid application using **Context Factories** and **ACLs (Access Control Lists)** instead of permission decorators. This approach provides more flexible, reusable, and maintainable security.

## Key Features

- **Context Factory-based Security**: No permission decorators needed
- **ACL Authorization**: Declarative access control lists
- **Multiple Security Contexts**: Different contexts for different resource types
- **Dynamic Security**: ACLs that change based on request context
- **Resource Ownership**: User-owned resources with ownership-based permissions
- **JWT + API Key Authentication**: Multiple authentication methods
- **Role-based Access Control**: Admin and user roles

## Security Architecture

### Context Factory Approach

Instead of using `@require_permission('admin')` decorators, security is handled by:

1. **Context Factories**: Functions that create security contexts for routes
2. **ACL Classes**: Context classes with `__acl__()` methods defining permissions
3. **Security Policy**: Custom policy that integrates with Pyramid's security system
4. **Permission Declarations**: Views use `permission='view'` parameter

```python
# Traditional decorator approach (NOT used):
@view_config(route_name='admin')
@require_permission('admin')  # ❌ Couples security to view
def admin_view(request):
    pass

# Context factory approach (USED):
@view_config(route_name='admin', permission='view')  # ✅ Declarative
def admin_view(request):
    pass  # Security handled by AdminContext via factory

config.add_route('admin', '/admin', factory=admin_context_factory)
```

### Security Contexts

#### 1. PublicContext
- **Purpose**: Public resources requiring no authentication
- **Permissions**: Everyone can view
- **Usage**: Login endpoint, public documentation

```python
class PublicContext:
    def __acl__(self):
        return [
            (Allow, Everyone, 'view'),
        ]
```

#### 2. AuthenticatedContext  
- **Purpose**: Resources requiring authentication
- **Permissions**: Authenticated users can view/edit, admins have all permissions
- **Usage**: User profiles, secure data

```python
class AuthenticatedContext:
    def __acl__(self):
        return [
            (Allow, Authenticated, 'view'),
            (Allow, Authenticated, 'edit'),
            (Allow, 'role:admin', ALL_PERMISSIONS),
        ]
```

#### 3. AdminContext
- **Purpose**: Admin-only resources
- **Permissions**: Only admin role has access
- **Usage**: System administration, user management

```python
class AdminContext:
    def __acl__(self):
        return [
            (Allow, 'role:admin', ALL_PERMISSIONS),
            (Deny, Everyone, ALL_PERMISSIONS),
        ]
```

#### 4. UserOwnedContext
- **Purpose**: Resources owned by specific users
- **Permissions**: Owner can edit, everyone can view, admins have all permissions
- **Usage**: User profiles, personal data

```python
class UserOwnedContext:
    def __init__(self, owner_username=None, owner_userid=None):
        self.owner_username = owner_username
        self.owner_userid = owner_userid
    
    def __acl__(self):
        acl = [
            (Allow, Everyone, 'view'),
            (Allow, 'role:admin', ALL_PERMISSIONS),
        ]
        
        if self.owner_username:
            acl.append((Allow, f"user:{self.owner_username}", 'edit'))
        
        return acl
```

#### 5. DynamicCalculatorContext
- **Purpose**: Dynamic permissions based on operation complexity
- **Permissions**: Basic operations for authenticated, complex for admin
- **Usage**: Calculator with different permission levels

```python
class DynamicCalculatorContext:
    def __init__(self, request):
        self.operation = request.json_body.get('operation', 'simple')
    
    def __acl__(self):
        acl = [(Allow, Authenticated, 'simple_calc')]
        
        if self.operation in ['advanced', 'statistical']:
            acl.append((Allow, 'role:admin', 'advanced_calc'))
        else:
            acl.append((Allow, Authenticated, 'advanced_calc'))
        
        return acl
```

## Security Endpoints

### Authentication Routes

#### Login (Public)
```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}'
```

**Response:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "alice",
    "role": "user"
  }
}
```

#### Profile (Authenticated Context)
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8080/auth/profile
```

### Resource Routes

#### User Profile (Ownership Context)
- **GET /users/{username}**: Anyone can view (Everyone permission)
- **PUT /users/{username}**: Owner or admin can edit

```bash
# View any user profile (public)
curl http://localhost:8080/users/alice

# Edit own profile (requires ownership or admin)
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Updated"}' \
  http://localhost:8080/users/alice
```

#### Admin Data (Admin Context)
```bash
curl -H "X-API-Key: service-key-123" \
  http://localhost:8080/api/admin-data
```

#### Secure Data (Authenticated Context)
```bash
curl -H "X-API-Key: user-key-456" \
  http://localhost:8080/api/secure-data
```

## MCP Context Factory Integration

### 🔧 NEW: Context Factory Security for MCP Tools

This example demonstrates the **Context Factory Integration Fix** that allows MCP tools to respect Pyramid's context factory security system. Previously, MCP tools could only use basic permission parameters and couldn't integrate with Pyramid's ACL system.

#### MCP Endpoints with Context Factories

The application provides three MCP endpoints demonstrating different security levels:

1. **`/mcp`** - Default MCP endpoint (basic permission checking)
2. **`/mcp-secure`** - Uses `AuthenticatedContext` (requires authentication)  
3. **`/mcp-admin`** - Uses `AdminContext` (requires admin role)

#### Testing Context Factory Security

**Anonymous Access (Denied):**
```bash
curl -X POST http://localhost:8080/mcp-secure \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
    "params": {"name": "secure_data_processor", "arguments": {"data": "test"}}
  }'
# Response: {"error": {"message": "Authentication required"}}
```

**Authenticated Access (Allowed):**
```bash
TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}' \
  | jq -r '.token')

curl -X POST http://localhost:8080/mcp-secure \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
    "params": {"name": "secure_data_processor", "arguments": {"data": "test"}}
  }'
# Response: {"result": {"content": [{"text": "..."}]}}
```

**Admin Access (Full Permissions):**
```bash
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "password": "admin456"}' \
  | jq -r '.token')

curl -X POST http://localhost:8080/mcp-admin \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", "id": 1, "method": "tools/call", 
    "params": {"name": "system_status", "arguments": {}}
  }'
```

#### How It Works

The fix works by:

1. **Context Extraction**: MCP view gets the context from the route's context factory
2. **Security Integration**: Passes both `request` and `context` to the MCP protocol handler
3. **Policy Integration**: Uses `policy.permits(request, context, permission)` instead of basic permission checking
4. **ACL Evaluation**: Context factory ACLs are properly evaluated for MCP tool access

```python
# In create_app():
# Create custom MCP routes with context factories
config.add_route('mcp_secure', '/mcp-secure', factory=authenticated_context_factory)
config.add_view(
    pyramid_mcp._handle_mcp_http,
    route_name='mcp_secure',
    request_method='POST',
    renderer='json'
)
```

## MCP Tools

All MCP tools use context-based security instead of permission decorators:

### secure_calculator
- **Context**: No specific context (uses MCP's built-in security)
- **Description**: Perform calculations with context-based security
- **Security**: Handled by pyramid-mcp's security integration

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "secure_calculator",
      "arguments": {"operation": "add", "a": 5, "b": 3}
    }
  }'
```

### user_management
- **Context**: Admin-only via pyramid-mcp security
- **Description**: Manage user accounts (admin context required)
- **Actions**: list, get, create

```bash
curl -X POST http://localhost:8080/mcp \
  -H "X-API-Key: service-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "user_management",
      "arguments": {"action": "list"}
    }
  }'
```

### system_status
- **Context**: Admin-only
- **Description**: Get system status information

### secure_data_processor
- **Context**: Authenticated users
- **Description**: Process data with various operations
- **Operations**: info, hash, encrypt

## Authentication Methods

### 1. JWT Token Authentication
```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "password": "admin456"}' | \
  jq -r '.token')

# Use token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/admin-data
```

### 2. API Key Authentication
```bash
# Admin API key
curl -H "X-API-Key: service-key-123" \
  http://localhost:8080/api/admin-data

# User API key  
curl -H "X-API-Key: user-key-456" \
  http://localhost:8080/api/secure-data
```

## Test Users

| Username | Password | Role | Access Level |
|----------|----------|------|--------------|
| alice | secret123 | user | Authenticated resources, own profile |
| bob | admin456 | admin | All resources, all user profiles |

## API Keys

| Key | Name | Role | Access Level |
|-----|------|------|--------------|
| service-key-123 | service-account | admin | All resources |
| user-key-456 | user-account | user | Authenticated resources only |

## Context Factory Benefits

### 1. **Separation of Concerns**
- Security logic is separate from business logic
- Views focus on functionality, not security
- ACLs are reusable across multiple views

### 2. **Flexibility**
- Dynamic ACLs based on request context
- Resource-specific permissions
- Easy to modify security without changing views

### 3. **Maintainability**
- Centralized security definitions
- Clear security boundaries
- Easy to audit and test

### 4. **Pyramid Integration**
- Works seamlessly with Pyramid's security system
- Supports ACL inheritance
- Integrates with authentication policies

## Security Best Practices

### 1. **Use HTTPS in Production**
```python
# Configure your WSGI server with SSL
# gunicorn --certfile=cert.pem --keyfile=key.pem myapp:app
```

### 2. **Secure JWT Secret**
```python
import os
JWT_SECRET = os.environ.get('JWT_SECRET', 'fallback-secret')
```

### 3. **Hash Passwords**
```python
import bcrypt

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)
```

### 4. **Rate Limiting**
```python
from pyramid_ratelimit import RateLimitPredicate

config.add_view_predicate('ratelimit', RateLimitPredicate)

@view_config(route_name='login', ratelimit=True)
def login_view(request):
    pass
```

## Error Handling

### Common Security Errors

#### 401 Unauthorized
```json
{
  "error": "Authentication required",
  "details": "No valid authentication provided"
}
```

#### 403 Forbidden  
```json
{
  "error": "Access denied",
  "details": "Insufficient permissions for this resource"
}
```

#### 404 Not Found (Ownership)
```json
{
  "error": "User not found",
  "details": "The requested user profile does not exist"
}
```

## Running the Example

1. **Install Dependencies**:
   ```bash
   pip install pyramid pyramid-mcp PyJWT
   ```

2. **Run the Server**:
   ```bash
   python examples/secure/secure_app.py
   ```

3. **Test Context Factories**:
   ```bash
   # Test public access
   curl http://localhost:8080/auth/login

   # Test authenticated access
   curl -H "X-API-Key: user-key-456" \
     http://localhost:8080/api/secure-data

   # Test admin access
   curl -H "X-API-Key: service-key-123" \
     http://localhost:8080/api/admin-data

   # Test ownership (will fail - not owner)
   curl -X PUT -H "X-API-Key: user-key-456" \
     -H "Content-Type: application/json" \
     -d '{"name": "Hacker"}' \
     http://localhost:8080/users/bob
   ```

## Architecture Diagram

```
Request → Authentication Middleware → Context Factory → ACL Check → View
                                          ↓
                               Context with __acl__() method
                                          ↓
                               (Allow, 'role:admin', 'view')
                               (Allow, Authenticated, 'edit')
                               (Deny, Everyone, 'delete')
```

This context factory approach provides a clean, flexible, and maintainable way to handle security in Pyramid applications with pyramid-mcp integration. 
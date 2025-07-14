# Cornice + Bearer Authentication + MCP Integration Example

This example demonstrates how to build a REST API using Cornice with Bearer token authentication and integrate it with the Model Context Protocol (MCP).

## Features

- **Cornice REST Services**: RESTful endpoints with automatic validation
- **Bearer Token Authentication**: Secure API access using Bearer tokens
- **Marshmallow Schema Validation**: Request/response validation and serialization
- **MCP Integration**: Expose Cornice services as MCP tools
- **Role-Based Permissions**: Different access levels (user, admin, service)
- **Security Levels**: Public, authenticated, and admin-only endpoints

## Quick Start

### Prerequisites

- Python 3.9+
- Poetry (for dependency management)

### Installation

```bash
# Install dependencies
cd examples/cornice-bearer
poetry install

# Or run directly from project root
cd ../../
poetry install
```

### Running the Server

```bash
# From the example directory
python cornice_bearer_app.py

# Or using poetry script
poetry run cornice-bearer-app
```

The server will start at `http://localhost:8080`

## API Endpoints

### Public Endpoints

- `GET /api/public/info` - Server information (no authentication required)

### Authenticated Endpoints (Bearer token required)

- `GET /api/users` - List users
- `POST /api/users` - Create user (requires write permission)
- `GET /api/posts` - List blog posts  
- `POST /api/posts` - Create blog post (requires write permission)

### Admin Endpoints (Bearer token + admin permission required)

- `POST /api/admin/actions` - Perform administrative actions

## Bearer Tokens

The example includes predefined Bearer tokens for testing:

| Token | User | Role | Permissions |
|-------|------|------|-------------|
| `user-token-123` | alice | user | read, write |
| `admin-token-456` | bob | admin | read, write, admin, delete |
| `service-token-789` | service | service | read, write, admin, service |

## Usage Examples

### Public Access (No Authentication)

```bash
curl http://localhost:8080/api/public/info
```

### Authenticated Access

```bash
# List users
curl -H "Authorization: Bearer user-token-123" \
     http://localhost:8080/api/users

# Create a user
curl -H "Authorization: Bearer user-token-123" \
     -H "Content-Type: application/json" \
     -d '{"username": "newuser", "email": "new@example.com", "role": "user"}' \
     http://localhost:8080/api/users

# List posts
curl -H "Authorization: Bearer user-token-123" \
     http://localhost:8080/api/posts

# Create a post
curl -H "Authorization: Bearer user-token-123" \
     -H "Content-Type: application/json" \
     -d '{"title": "My New Post", "content": "This is the content", "category": "tech"}' \
     http://localhost:8080/api/posts
```

### Admin Access

```bash
# Perform admin backup
curl -H "Authorization: Bearer admin-token-456" \
     -H "Content-Type: application/json" \
     -d '{"action": "backup", "target": "database"}' \
     http://localhost:8080/api/admin/actions

# Cleanup with force
curl -H "Authorization: Bearer admin-token-456" \
     -H "Content-Type: application/json" \
     -d '{"action": "cleanup", "force": true}' \
     http://localhost:8080/api/admin/actions
```

## MCP Integration

The Cornice services are automatically exposed as MCP tools at `http://localhost:8080/mcp`.

### Available MCP Tools

- `get_api_public_info` - Get server info (no authentication)
- `list_api_users` - List users (Bearer token required)
- `create_api_users` - Create user (Bearer token + write permission)
- `list_api_posts` - List posts (Bearer token required) 
- `create_api_posts` - Create post (Bearer token + write permission)
- `perform_api_admin_actions` - Admin actions (Bearer token + admin permission)

### MCP Tools with Bearer Authentication

When calling MCP tools that require authentication, include the Bearer token in the `auth_token` parameter:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "list_api_users",
    "arguments": {
      "auth_token": "user-token-123"
    }
  }
}
```

### Claude Desktop Configuration

Add this to your Claude Desktop MCP configuration:

```json
{
  "pyramid-mcp-cornice": {
    "command": "/path/to/python",
    "args": [
      "/path/to/pyramid-mcp/examples/cornice-bearer/cornice_bearer_app.py"
    ],
    "cwd": "/path/to/pyramid-mcp"
  }
}
```

Or use the pstdio command:

```json
{
  "pyramid-mcp-cornice": {
    "command": "/path/to/pstdio",
    "args": [
      "--app", 
      "examples.cornice-bearer.cornice_bearer_app:create_app"
    ],
    "cwd": "/path/to/pyramid-mcp"
  }
}
```

## Schema Validation

This example uses Marshmallow schemas for request validation:

### CreateUserSchema

```python
{
  "username": "string (required, min 3 chars)",
  "email": "email (required)",
  "role": "string (required, 'user' or 'admin')",
  "full_name": "string (optional)"
}
```

### CreatePostSchema

```python
{
  "title": "string (required, min 5 chars)",
  "content": "string (required, min 10 chars)", 
  "category": "string (optional, 'tech'|'business'|'personal')",
  "published": "boolean (optional, default false)"
}
```

### AdminActionSchema

```python
{
  "action": "string (required, 'backup'|'cleanup'|'reset'|'maintenance')",
  "target": "string (optional)",
  "force": "boolean (optional, default false)"
}
```

## Security Implementation

### Bearer Token Validation

1. Extract `Authorization: Bearer <token>` header
2. Lookup token in token storage (database in production)
3. Return user info if valid, None if invalid

### Permission Checking

1. Check if user has required permission
2. Permissions: `read`, `write`, `admin`, `delete`, `service`
3. Role-based access control

### Error Handling

- `401 Unauthorized` - Missing or invalid Bearer token
- `403 Forbidden` - Valid token but insufficient permissions
- `400 Bad Request` - Schema validation errors

## Production Considerations

### Security

1. **Token Storage**: Use Redis/database instead of in-memory dict
2. **Token Expiration**: Implement JWT with expiration times
3. **Token Rotation**: Regular token rotation policies
4. **HTTPS Only**: Force HTTPS in production
5. **Rate Limiting**: Implement API rate limiting

### Scalability

1. **Database**: Use proper database for user/token storage
2. **Caching**: Cache user permissions and roles
3. **Load Balancing**: Multiple server instances
4. **Monitoring**: Add logging and metrics

### Configuration

1. **Environment Variables**: Use env vars for tokens/secrets
2. **Configuration Files**: Separate dev/staging/prod configs
3. **Secret Management**: Use proper secret management systems

## Testing

```bash
# Run tests (if implemented)
poetry run pytest

# Test specific endpoint
curl -v -H "Authorization: Bearer user-token-123" \
     http://localhost:8080/api/users
```

## Development

### Adding New Endpoints

1. Create Marshmallow schema for validation
2. Create Cornice service with `mcp_security="bearer"`
3. Implement Bearer token validation in handler
4. Add permission checks as needed

### Adding New Permissions

1. Update user permissions in token storage
2. Add permission checks in handlers
3. Update documentation

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check Bearer token format and validity
2. **403 Forbidden**: Check user permissions
3. **400 Bad Request**: Check request body against schema
4. **MCP Connection**: Verify pstdio command and app path

### Debug Mode

Set environment variable for debug output:

```bash
PYRAMID_DEBUG=1 python cornice_bearer_app.py
```

## Related Examples

- `examples/simple/` - Basic pyramid-mcp integration
- `examples/secure/` - Context factory-based security
- Main project documentation for advanced features 
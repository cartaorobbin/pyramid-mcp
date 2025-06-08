# Claude Desktop Integration Guide

This guide explains how to integrate the secure pyramid-mcp server with Claude Desktop, including authentication setup and configuration.

## Overview

Claude Desktop can connect to MCP servers to expand Claude's capabilities with custom tools. This guide covers:

- Setting up Claude Desktop to connect to your secure MCP server
- Configuring authentication for secure tools
- Testing the connection and troubleshooting issues
- Best practices for production use

## Prerequisites

1. **Claude Desktop installed** - Download from [Claude.ai](https://claude.ai/download)
2. **Secure MCP server running** - Either follow the [Secure Example README](README.md) or use Docker (recommended)
3. **Valid authentication** - JWT token or API key for accessing protected tools

## Setup Options

Choose one of these setup methods:

- **🐳 [Docker Setup](#docker-setup-recommended)** - Recommended for ease of use and reliability
- **🐍 [Local Python Setup](#local-python-setup)** - For development and customization

## Docker Setup (Recommended)

The Docker approach eliminates path configuration issues and provides a consistent environment across all systems.

### Step 1: Build and Run Docker Container

From the project root directory:

```bash
# Build the Docker image
docker build -f examples/secure/Dockerfile -t pyramid-mcp-secure .

# Run the container
docker run -d -p 8080:8080 --name pyramid-mcp pyramid-mcp-secure

# Verify it's running
curl http://localhost:8080/auth/login
# Should return: 404 Not Found with "predicate mismatch for view login (request_method = POST)"
# This confirms the server is running and responding
```

### Step 2: Configure Claude Desktop for HTTP Transport

Create or edit your Claude Desktop configuration file with HTTP transport:

```json
{
  "mcpServers": {
    "pyramid-secure": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8080/mcp-secure",
        "headers": {
          "X-API-Key": "service-key-123"
        }
      }
    }
  }
}
```

### Step 3: Container Management

```bash
# Stop the container
docker stop pyramid-mcp

# Start the container again
docker start pyramid-mcp

# View logs
docker logs pyramid-mcp

# Remove the container
docker rm pyramid-mcp
```

### Docker Configuration Examples

#### Basic Admin Access
```json
{
  "mcpServers": {
    "pyramid-admin": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8080/mcp-admin",
        "headers": {
          "X-API-Key": "service-key-123"
        }
      }
    }
  }
}
```

#### User-Level Access
```json
{
  "mcpServers": {
    "pyramid-user": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8080/mcp-secure",
        "headers": {
          "X-API-Key": "user-key-456"
        }
      }
    }
  }
}
```

#### JWT Token Authentication
```json
{
  "mcpServers": {
    "pyramid-jwt": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8080/mcp-secure",
        "headers": {
          "Authorization": "Bearer YOUR_JWT_TOKEN_HERE"
        }
      }
    }
  }
}
```

### Benefits of Docker Setup

- ✅ **No path configuration** - No need to specify Python executable paths
- ✅ **Consistent environment** - Same container works on Windows, macOS, and Linux
- ✅ **Isolated dependencies** - No conflicts with your system Python
- ✅ **Easy deployment** - Single Docker command to start/stop
- ✅ **Reliable** - Container restarts automatically if it crashes

## Local Python Setup

### Step 1: Install Dependencies

Follow the [Secure Example README](README.md) for detailed installation instructions.

## Configuration

### Step 1: Locate Claude Desktop Configuration

Claude Desktop stores its configuration in different locations depending on your operating system:

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### Step 2: Basic MCP Server Configuration

Add your pyramid-mcp server to the Claude Desktop configuration:

```json
{
  "mcpServers": {
    "pyramid-secure": {
      "command": "python",
      "args": ["/path/to/your/examples/secure/secure_app.py"],
      "env": {
        "PYTHONPATH": "/path/to/pyramid-mcp"
      }
    }
  }
}
```

### Step 3: Authentication Configuration

For secure servers, you need to configure authentication. There are several approaches:

#### Option A: Environment Variables (Recommended)

Set authentication credentials as environment variables:

```json
{
  "mcpServers": {
    "pyramid-secure": {
      "command": "python",
      "args": ["/path/to/your/examples/secure/secure_app.py"],
      "env": {
        "PYTHONPATH": "/path/to/pyramid-mcp",
        "MCP_AUTH_TOKEN": "your-jwt-token-here",
        "MCP_API_KEY": "service-key-123"
      }
    }
  }
}
```

#### Option B: HTTP Transport with Authentication Headers

Configure Claude to connect via HTTP with authentication:

```json
{
  "mcpServers": {
    "pyramid-secure": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8080/mcp",
        "headers": {
          "Authorization": "Bearer your-jwt-token-here"
        }
      }
    }
  }
}
```

#### Option C: API Key Authentication

For service-to-service authentication:

```json
{
  "mcpServers": {
    "pyramid-secure": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8080/mcp",
        "headers": {
          "X-API-Key": "service-key-123"
        }
      }
    }
  }
}
```

## Getting Authentication Tokens

### JWT Token Authentication

1. **Get a JWT token** by calling the login endpoint:

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "bob",
    "password": "admin456"
  }'
```

2. **Extract the token** from the response:

```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoyLCJ1c2VybmFtZSI6ImJvYiIsInBlcm1pc3Npb25zIjpbImF1dGhlbnRpY2F0ZWQiLCJhZG1pbiJdLCJpYXQiOjE3MDkxMjM0NTYsImV4cCI6MTcwOTIwOTg1Nn0.ABC123...",
  "user": {
    "id": 2,
    "username": "bob",
    "permissions": ["authenticated", "admin"]
  }
}
```

3. **Use the token** in your Claude Desktop configuration.

### API Key Authentication

For automated/service access, use the pre-configured API keys:

- `service-key-123` - Admin permissions
- `user-key-456` - User permissions

## Complete Configuration Examples

### Example 1: Local Development with JWT

```json
{
  "mcpServers": {
    "pyramid-secure-dev": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8080/mcp",
        "headers": {
          "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        }
      }
    }
  }
}
```

### Example 2: Production with API Key

```json
{
  "mcpServers": {
    "pyramid-secure-prod": {
      "transport": {
        "type": "http",
        "url": "https://your-domain.com/mcp",
        "headers": {
          "X-API-Key": "your-production-api-key",
          "Content-Type": "application/json"
        }
      }
    }
  }
}
```

### Example 3: Multiple Permission Levels

```json
{
  "mcpServers": {
    "pyramid-user": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8080/mcp",
        "headers": {
          "X-API-Key": "user-key-456"
        }
      }
    },
    "pyramid-admin": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8080/mcp",
        "headers": {
          "X-API-Key": "service-key-123"
        }
      }
    }
  }
}
```

## Testing the Connection

### Step 1: Restart Claude Desktop

After updating the configuration, restart Claude Desktop to load the new settings.

### Step 2: Verify Connection in Claude

Start a new conversation in Claude and try using the MCP tools:

```
Hello! Can you list the available tools from the pyramid-secure server?
```

Claude should respond with the available tools from your secure server.

### Step 3: Test Tool Functionality

Try calling specific tools based on your permission level:

**For authenticated users:**
```
Can you use the secure_calculator tool to multiply 6 by 7?
```

**For admin users:**
```
Can you check the system status using the system_status tool?
```

## Available Tools by Permission Level

### Public Tools (Auto-discovered)
These tools require authentication but are available to all authenticated users:

- **api_secure_data** - Get secure data from the API
- **api_admin_data** - Get admin data (admin permission required)

### Authenticated Tools
These tools require the 'authenticated' permission:

- **secure_calculator** - Perform mathematical calculations with audit logging
- **secure_data_processor** - Process sensitive data with security controls

### Admin Tools
These tools require the 'admin' permission:

- **user_management** - Manage user accounts
- **system_status** - Get detailed system status and statistics

## Troubleshooting

### Common Issues

#### 1. "Connection refused" or "Server not found"

**Problem:** Claude can't connect to your MCP server.

**Solutions:**
- Ensure your secure_app.py is running on the correct port (8080 by default)
- Check firewall settings if running on a different machine
- Verify the URL in your configuration matches your server

#### 2. "Authentication required" errors

**Problem:** Your authentication credentials are invalid or expired.

**Solutions:**
- Check that your JWT token hasn't expired (24-hour default)
- Verify API key is correct and has appropriate permissions
- Ensure the Authorization/X-API-Key header is properly formatted

#### 3. "Permission denied" errors

**Problem:** Your credentials don't have sufficient permissions for the tool.

**Solutions:**
- Use an admin API key (`service-key-123`) for admin tools
- Login as an admin user (`bob/admin456`) to get admin JWT token
- Check the tool's permission requirements in the documentation

#### 4. Tools not appearing

**Problem:** Claude doesn't see your MCP tools.

**Solutions:**
- Restart Claude Desktop after configuration changes
- Check Claude Desktop logs for connection errors
- Verify your configuration JSON syntax is valid
- Ensure the MCP server is responding to `/mcp` endpoint

### Debug Mode

Enable debug logging in your secure_app.py for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Add request logging
def debug_middleware(handler, registry):
    def middleware(request):
        print(f"Request: {request.method} {request.path}")
        print(f"Headers: {dict(request.headers)}")
        return handler(request)
    return middleware

config.add_tween('__main__.debug_middleware')
```

### Testing with curl

Test your authentication outside of Claude:

```bash
# Test JWT authentication
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'

# Test API key authentication
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: service-key-123" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "system_status",
      "arguments": {}
    }
  }'
```

## Security Considerations

### Token Management

1. **Rotate JWT tokens regularly** - Set shorter expiration times in production
2. **Store API keys securely** - Use environment variables, not configuration files
3. **Use HTTPS in production** - Never send tokens over unencrypted connections

### Network Security

1. **Firewall configuration** - Restrict access to your MCP server
2. **VPN or private networks** - Keep MCP servers on internal networks when possible
3. **Rate limiting** - Implement rate limiting to prevent abuse

### Monitoring

1. **Audit logging** - Log all tool usage and authentication attempts
2. **Monitoring alerts** - Set up alerts for authentication failures
3. **Performance monitoring** - Monitor server performance and response times

## Production Deployment

### Docker Configuration

Create a Dockerfile for your secure MCP server:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY examples/secure/ .
EXPOSE 8080

CMD ["python", "secure_app.py"]
```

### Environment Variables

Use environment variables for production configuration:

```bash
export JWT_SECRET="your-production-jwt-secret"
export API_KEY_ADMIN="your-production-admin-key"
export API_KEY_USER="your-production-user-key"
export MCP_HOST="0.0.0.0"
export MCP_PORT="8080"
```

### Load Balancer Configuration

For high availability, configure your load balancer to handle MCP traffic:

```nginx
upstream mcp_servers {
    server app1.example.com:8080;
    server app2.example.com:8080;
}

server {
    listen 443 ssl;
    server_name mcp.example.com;
    
    location /mcp {
        proxy_pass http://mcp_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Authorization $http_authorization;
        proxy_set_header X-API-Key $http_x_api_key;
    }
}
```

This guide provides everything you need to integrate your secure pyramid-mcp server with Claude Desktop. For additional help, refer to the [main documentation](../../docs/) or the [simple example](../simple/) for basic setup. 
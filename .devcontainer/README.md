# Development Container with Docker-in-Docker

This development container provides a complete Python development environment with Docker-in-Docker functionality for the Pyramid MCP project.

## 🚀 Features

- **Python 3.11.3** development environment
- **Poetry** for dependency management  
- **Docker-in-Docker** for container development and testing
- **Pre-configured VS Code extensions** for Python and Docker development
- **Port forwarding** for web application testing (8080, 8000, 3000)
- **Automatic dependency installation** and pre-commit hooks setup

## 📦 What's Included

### Development Tools
- Poetry (latest) - Python dependency management
- Docker-in-Docker (v2) - Container development inside dev container
- Pre-commit hooks - Code quality automation

### VS Code Extensions
- Python language support with IntelliSense
- Black formatter for code formatting
- Flake8 and MyPy for linting and type checking
- Docker extension for container management
- Ruff for fast Python linting
- YAML and Makefile support

### Make Commands
Run `make help` to see all available commands, including new Docker commands:

```bash
# Docker Development Commands
make docker-check           # Verify Docker is working
make docker-build-examples  # Build example containers
make docker-test-examples   # Test example containers  
make docker-run-secure      # Run secure example interactively
make docker-clean           # Clean up Docker resources
```

## 🛠 Setup Instructions

### 1. Prerequisites
- VS Code with Dev Containers extension
- Docker Desktop running on your host machine

### 2. Open in Dev Container
1. Open the project in VS Code
2. Click "Reopen in Container" when prompted, or
3. Use Command Palette: `Dev Containers: Reopen in Container`

### 3. Verify Setup
After the container builds and starts:

```bash
# Check Python environment
poetry --version
python --version

# Check Docker functionality  
make docker-check

# Run tests to verify everything works
make test
```

## 🐳 Docker-in-Docker Usage

### Building Example Containers
```bash
# Build all example Docker images
make docker-build-examples

# Or build individually
cd examples/secure
docker build -t pyramid-mcp-secure:latest .
```

### Testing Containers
```bash
# Test example containers
make docker-test-examples

# Run secure example interactively
make docker-run-secure

# Access the running container
curl http://localhost:8080/health
```

### Development Workflow
1. **Develop** your code in the dev container
2. **Build** Docker images with `make docker-build-examples`
3. **Test** containers with `make docker-test-examples`
4. **Debug** by running containers interactively
5. **Clean up** with `make docker-clean`

## 🔧 Customization

### Adding New Ports
Edit `.devcontainer/devcontainer.json`:
```json
"forwardPorts": [8080, 8000, 3000, 5000]
```

### Adding VS Code Extensions
Edit `.devcontainer/devcontainer.json`:
```json
"extensions": [
    "existing-extensions",
    "new.extension-id"
]
```

### Modifying Post-Install Script
Edit `.devcontainer/post-install.sh` to add custom setup steps.

## 📋 Troubleshooting

### Docker Not Working
If `docker --version` fails inside the container:

1. **Rebuild the container** (Dev Containers: Rebuild Container)
2. **Check host Docker** is running
3. **Verify Docker Desktop** allows container access
4. **Check logs** in VS Code Dev Containers output

### Performance Issues
Docker-in-Docker can be resource-intensive:

1. **Increase Docker Desktop resources** (CPU/Memory)
2. **Use docker-clean** regularly to free up space
3. **Close unused containers** and images

### Port Conflicts
If ports are already in use:

1. **Stop conflicting services** on host
2. **Change port mappings** in devcontainer.json
3. **Use different ports** in make commands

### Permission Issues
If Docker permission errors occur:

1. **Rebuild container** to ensure proper setup
2. **Check docker group membership** with `groups`
3. **Restart Docker daemon** if needed

## 📚 Additional Resources

- [VS Code Dev Containers](https://code.visualstudio.com/docs/remote/containers)
- [Docker-in-Docker Documentation](https://github.com/devcontainers/features/tree/main/src/docker-in-docker)
- [Poetry Documentation](https://python-poetry.org/docs/)

## 🆘 Getting Help

If you encounter issues:

1. **Check the troubleshooting section** above
2. **Review VS Code Dev Container logs**
3. **Verify host Docker configuration**
4. **Try rebuilding the container** from scratch

For project-specific help, see the main README.md and CONTRIBUTING.md files. 
#!/bin/bash

echo "🚀 Starting Pyramid MCP dev container post-install setup..."

# Load environment variables if available
if [ -f devcontainer.env ]; then
  export $(echo $(cat devcontainer.env | sed 's/#.*//g'| xargs) | envsubst)
fi

# Ensure Docker is accessible (docker-in-docker feature should handle this, but verify)
if command -v docker &> /dev/null; then
    echo "✅ Docker is available"
    # Test Docker access
    if docker --version &> /dev/null; then
        echo "✅ Docker daemon is accessible"
    else
        echo "⚠️  Docker daemon not accessible, this may resolve after container restart"
    fi
else
    echo "❌ Docker not found in PATH"
fi

# Configure Poetry (may be installed via feature, but ensure proper config)
if command -v poetry &> /dev/null; then
    echo "✅ Poetry is available"
    poetry config virtualenvs.create true
    poetry config virtualenvs.in-project true
    echo "📦 Installing project dependencies..."
    poetry install
else
    echo "❌ Poetry not found, will be installed via dev container feature"
fi

# Install pre-commit hooks
if [ -f .pre-commit-config.yaml ]; then
    echo "🔧 Installing pre-commit hooks..."
    if command -v pre-commit &> /dev/null; then
        pre-commit install
    else
        echo "⚠️  pre-commit not available yet, will need to run 'make install' later"
    fi
fi

# Remove old SSH key (seems project-specific)
ssh-keygen -R 20.201.28.151 2>/dev/null || true

echo "🎉 Post-install setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Run 'make install' to ensure all dependencies are properly installed"
echo "   2. Run 'docker --version' to verify Docker access"
echo "   3. Try 'make test' to run the test suite"
echo "   4. Test Docker functionality with 'cd examples/secure && docker build -t test-image .'"
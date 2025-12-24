#!/bin/bash
# Install git hooks for version management

HOOK_FILE=".git/hooks/pre-commit"

# Create pre-commit hook
cat > "$HOOK_FILE" << 'EOF'
#!/bin/bash
set -e

echo "Checking for file changes and updating version..."
uv run python version_manager.py check

# If version files were modified, stage them
if git diff --name-only | grep -q "pyproject.toml\|src/__init__.py"; then
    git add pyproject.toml src/__init__.py
    echo "Version auto-incremented and staged"
fi

exit 0
EOF

chmod +x "$HOOK_FILE"
echo "Pre-commit hook installed at $HOOK_FILE"

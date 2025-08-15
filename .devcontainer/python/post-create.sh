#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Install uv environment
uv venv
uv sync --group dev --locked

# Install Pre-commit hooks
echo "Installing Pre-commit hooks..."
uv tool install pre-commit
pre-commit install


echo "Post-create script completed successfully."
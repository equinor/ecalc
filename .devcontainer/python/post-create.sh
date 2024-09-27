#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Install Pre-commit hooks
echo "Installing Pre-commit hooks..."
pre-commit install

# Install poetry environment
poetry install

echo "Post-create script completed successfully."
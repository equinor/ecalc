#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Install Poetry dependencies
echo "Installing Poetry dependencies..."
poetry install

# Install Pre-commit hooks
echo "Installing Pre-commit hooks..."
pre-commit install

echo "Post-create script completed successfully."
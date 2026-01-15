#!/bin/sh

set -ex

# Function to load an environment file if it exists
load_env_file() {
    if [ -f "$1" ]; then
        echo "Loading environment variables from $1..."
        set -a  # Automatically export all variables
        . "$1"
        set +a
    else
        echo "Warning: No environment file found at $1"
    fi
}

# Load the local .env file (overrides Azure variables if defined)
load_env_file "/app/.env"

# Start the Rasa application
echo "Starting Rasa..."
rasa run --enable-api --cors "*" --port 5005
#!/bin/bash

set -e

# Define ANSI color codes
bcolors() {
    OKGREEN='\033[32m'
    WARNING='\033[33m'
    FAIL='\033[31m'
    ENDC='\033[0m'
}

# Define colors using the bcolors from the project
green() {
    echo -e "${OKGREEN}$1${ENDC}"
}

red() {
    echo -e "${FAIL}$1${ENDC}"
}

yellow() {
    echo -e "${WARNING}$1${ENDC}"
}

# Change to the frontend directory
cd twitch-spy-frontend || exit 1

# Accepts --check or --fix as the first argument
MODE=$1

if [[ "$MODE" == "--fix" ]]; then
    echo "Applying code formatting..."
    npm run format
fi

echo "Checking code formatting..."
if npm run format-check; then
    green "All files are correctly formatted."
    exit 0
else
    red "Code formatting issues detected."
    if [[ "$MODE" == "--check" ]]; then
        red "Please format the code before pushing."
    fi
    exit 1
fi

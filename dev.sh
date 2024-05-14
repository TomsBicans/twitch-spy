#!/bin/bash

# Navigate to the frontend directory
cd twitch-spy-frontend || exit

# Install dependencies if node_modules does not exist
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the React development server
echo "Starting the React development server..."
npm start

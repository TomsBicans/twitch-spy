#!/bin/bash

# Check if virtual environment exists
if [ -d "venv" ]; then
    source venv/bin/activate
else
    # Try to create virtual environment with 'python3'
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        # If 'python3' fails, try 'python'
        python -m venv venv
        if [ $? -ne 0 ]; then
            echo "Could not create virtual environment."
            exit 1
        fi
    fi
    source venv/bin/activate
fi

# Try to install requirements with 'python3'
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    # If 'python3' fails, try 'python'
    python -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Could not install requirements."
        exit 1
    fi
fi

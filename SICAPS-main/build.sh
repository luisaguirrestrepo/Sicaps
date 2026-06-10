#!/bin/bash
echo "=== Build Script ==="
echo "Python version:"
python --version
echo "Installing requirements..."
pip install -r requirements.txt
echo "=== Build Complete ==="

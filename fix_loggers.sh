#!/bin/bash

# Fix all logger imports and usages
find src -name "*.py" -type f | while read file; do
    # Skip the logger files themselves
    if [[ "$file" == *"logger.py"* ]]; then
        continue
    fi
    
    # Replace logger imports
    sed -i '' 's/from \.\.utils\.logger import get_.*_logger/from ..utils.simple_logger import get_logger/g' "$file"
    
    # Replace logger calls
    sed -i '' 's/logger = get_.*_logger("\(.*\)")/logger = get_logger("\1")/g' "$file"
done

echo "Logger fixes applied"
#!/bin/bash

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --project-path) project_path="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Check if the project path is provided
if [ -z "$project_path" ]; then
    echo "Usage: $0 --project-path <project-path>"
    exit 1
fi

# Run the RepoAudit script with the provided project path
python3 repoaudit.py \
    --language Cpp \
    --model-name claude-3.7 \
    --project-path "$project_path" \
    --temperature 0.0 \
    --scan-type samplescan \
    --call-depth 3 \
    --max-workers 1
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

# Log file
log_file="repoaudit_all.log"

# Clear the log file if it exists
> "$log_file"

# Run the RepoAudit script with the provided project path
python3 repoaudit.py \
    --language Cpp \
    --model-name claude-3.7 \
    --seed-selection-model claude-3.7 \
    --slicing-model claude-3.5 \
    --inlining-model claude-3.7 \
    --function-detection-model claude-3.7 \
    --project-path "$project_path" \
    --temperature 0.0 \
    --scan-type samplescan \
    --call-depth 2 \
    --max-workers 1 2>&1 | tee -a "$log_file"

echo "Finished RepoAudit for $project_path" | tee -a "$log_file"

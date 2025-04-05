#!/bin/bash

# Array of project cases
cases=("cpv-1" "cpv-2" "cpv-3" "cpv-4" "cpv-5" "cpv-8" "cpv-9" "cpv-10" "cpv-11" "cpv-12" "cpv-13" "cpv-14" "cpv-15" "cpv-17")

# Iterate over each case and run the script
for project_name in "${cases[@]}"; do
    echo "Running RepoAudit for $project_name"
    bash run_repoaudit.sh --project-path "../benchmark/Cpp/$project_name"
    echo "Finished RepoAudit for $project_name"
done